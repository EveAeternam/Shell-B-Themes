#!/usr/bin/env python3
"""Check every theme in themes/<id>/theme.json, build index.json and a preview.svg per theme.

Mirrors the rules Shell:B applies on install (server/themes.py `clean`): colours must be hex, choices come from fixed
lists, body text must reach WCAG AAA (7:1) on the page and panels, secondary text AA (4.5:1), the accent must carry a
readable label. A theme that needs nudging still installs (Shell:B adjusts it), but this script reports the nudge so you
can fix the design yourself. Standard library only; run from the repository root:

    python3 -I scripts/validate.py          # check + rebuild index.json and previews
    python3 -I scripts/validate.py --check  # check only (CI); exits 1 on any error
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

FONTS = ("inter", "barlow", "barlow-condensed", "shippori-mincho", "josefin-sans", "jetbrains-mono", "georgia",
         "cormorant-garamond", "sora", "syncopate", "outfit", "zen-maru-gothic")
BODY_FONTS = ("inter", "barlow", "shippori-mincho", "georgia", "sora", "outfit", "zen-maru-gothic")
SHAPES = ("soft", "hard", "round")
HORIZONS = ("none", "forest", "mountains", "floating", "waves", "city", "seafloor", "dunes", "snowpines", "hills")
PARTICLES = ("none", "fireflies", "petals", "leaves", "woodsprites", "snow", "embers", "bubbles", "bokeh", "sand", "rain", "abyss", "aurora")
PALETTE = ("bg", "panel", "raised", "hover", "code", "text", "text2", "muted", "accent", "brand", "line")
REQUIRED_PALETTE = ("bg", "panel", "text", "text2", "muted", "accent", "brand")
META = ("author", "license", "version", "tags", "homepage")
FONT_FAMILY = {
    "inter": "Inter, system-ui, sans-serif", "barlow": "Barlow, sans-serif", "barlow-condensed": "'Barlow Condensed', sans-serif",
    "shippori-mincho": "'Shippori Mincho', serif", "josefin-sans": "'Josefin Sans', sans-serif", "jetbrains-mono": "'JetBrains Mono', monospace",
    "georgia": "Georgia, serif", "cormorant-garamond": "'Cormorant Garamond', serif", "sora": "Sora, sans-serif",
    "syncopate": "Syncopate, sans-serif", "outfit": "Outfit, sans-serif", "zen-maru-gothic": "'Zen Maru Gothic', sans-serif",
}


def norm(h: str) -> str:
    h = h.lstrip("#").lower()
    return "#" + ("".join(c * 2 for c in h) if len(h) == 3 else h)


def lum(h: str) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check(path: Path) -> tuple[dict | None, list[str], list[str]]:
    """(theme, errors, warnings). Errors block a merge; warnings are nudges Shell:B would make on install."""
    errors, warnings = [], []
    try:
        spec = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return None, [f"not valid JSON: {e}"], []
    if not isinstance(spec, dict):
        return None, ["the file must hold one object"], []
    folder = path.parent.name
    if not ID_RE.match(folder):
        errors.append(f"folder name {folder!r}: lowercase letters, digits and dashes only")
    if spec.get("id") not in (None, folder):
        errors.append(f"id {spec.get('id')!r} doesn't match the folder name {folder!r}")
    name = str(spec.get("name") or "").strip()
    if not name or len(name) > 32:
        errors.append("name: 1-32 characters")
    if len(str(spec.get("blurb") or "")) > 160:
        errors.append("blurb: at most 160 characters")
    if not spec.get("blurb"):
        warnings.append("no blurb; the picker shows a generic line")
    if spec.get("mode") not in ("dark", "light"):
        errors.append("mode must be 'dark' or 'light'")
    for key in ("author", "license"):
        if not spec.get(key):
            errors.append(f"{key} is required (license: an SPDX id such as MIT or CC0-1.0)")

    pal = spec.get("palette")
    if not isinstance(pal, dict):
        errors.append("palette must be an object")
        pal = {}
    for k in REQUIRED_PALETTE:
        if k not in pal:
            errors.append(f"palette.{k} is required")
    for k, v in pal.items():
        if k not in PALETTE and k != "inks":
            warnings.append(f"palette.{k} is not a known key and will be ignored")
        elif k != "inks" and not (isinstance(v, str) and HEX.match(v)):
            errors.append(f"palette.{k} must be a hex colour like #1b2433")
    ok = {k: norm(pal[k]) for k in PALETTE if isinstance(pal.get(k), str) and HEX.match(pal[k])}
    if all(k in ok for k in ("bg", "panel", "text", "text2", "muted", "accent")):
        for k, ratio, label in (("text", 7.0, "AAA"), ("text2", 4.5, "AA"), ("muted", 4.5, "AA")):
            for surface in ("bg", "panel"):
                c = contrast(ok[k], ok[surface])
                if c < ratio:
                    warnings.append(f"{k} on {surface} is {c:.1f}:1, under {label} {ratio}:1 (Shell:B will lighten/darken it)")
        label = max(("#ffffff", "#111111"), key=lambda c: contrast(c, ok["accent"]))
        c = contrast(label, ok["accent"])
        if c < 4.5:
            warnings.append(f"accent {ok['accent']} can't carry a readable label ({c:.1f}:1); Shell:B will shift it")
        if contrast(ok["accent"], ok["bg"]) < 3.0:
            warnings.append("accent is faint on the page (links get a brighter variant)")
    inks = spec.get("inks") or pal.get("inks") or []
    if not isinstance(inks, list) or any(not (isinstance(c, str) and HEX.match(c)) for c in inks):
        errors.append("inks must be a list of hex colours")
    elif not 2 <= len(inks) <= 4:
        warnings.append("inks: 2-4 colours make the best picker stripe")

    fonts = spec.get("fonts") or {}
    if not isinstance(fonts, dict):
        errors.append("fonts must be an object")
        fonts = {}
    if fonts.get("display") is not None and fonts["display"] not in FONTS:
        errors.append(f"fonts.display must be one of {', '.join(FONTS)}")
    if fonts.get("body") is not None and fonts["body"] not in BODY_FONTS:
        errors.append(f"fonts.body must be one of {', '.join(BODY_FONTS)}")
    if spec.get("shape") is not None and spec["shape"] not in SHAPES:
        errors.append(f"shape must be one of {', '.join(SHAPES)}")
    tr = spec.get("tracking", 0)
    if not isinstance(tr, (int, float)) or not -0.02 <= tr <= 0.24:
        errors.append("tracking must be a number from -0.02 to 0.24")
    if spec.get("caps") and tr < 0.06:
        warnings.append("caps headings read better with tracking 0.08 or more")

    bd = spec.get("backdrop") or {}
    if not isinstance(bd, dict):
        errors.append("backdrop must be an object")
        bd = {}
    sky = bd.get("sky") or []
    if not isinstance(sky, list) or len(sky) > 3 or any(not (isinstance(c, str) and HEX.match(c)) for c in sky):
        errors.append("backdrop.sky: up to 3 hex colours, top to bottom")
    glows = bd.get("glows") or []
    if not isinstance(glows, list) or len(glows) > 4:
        errors.append("backdrop.glows: a list of at most 4")
    else:
        for i, g in enumerate(glows):
            if not isinstance(g, dict) or not (isinstance(g.get("color"), str) and HEX.match(g["color"])):
                errors.append(f"backdrop.glows[{i}] needs a hex color")
                continue
            for k, lo, hi in (("x", 0, 100), ("y", 0, 100), ("size", 10, 100), ("strength", 0.02, 0.5)):
                v = g.get(k)
                if v is not None and not (isinstance(v, (int, float)) and lo <= v <= hi):
                    errors.append(f"backdrop.glows[{i}].{k} must be {lo}-{hi}")
    st = bd.get("stars", 0)
    if not isinstance(st, (int, float)) or not 0 <= st <= 1:
        errors.append("backdrop.stars must be 0-1")
    if bd.get("horizon") is not None and bd["horizon"] not in HORIZONS:
        errors.append(f"backdrop.horizon must be one of {', '.join(HORIZONS)}")
    if bd.get("horizonColor") is not None and not (isinstance(bd["horizonColor"], str) and HEX.match(bd["horizonColor"])):
        errors.append("backdrop.horizonColor must be a hex colour")

    pt = spec.get("particles") or {}
    if not isinstance(pt, dict):
        errors.append("particles must be an object")
        pt = {}
    if pt.get("kind") is not None and pt["kind"] not in PARTICLES:
        errors.append(f"particles.kind must be one of {', '.join(PARTICLES)}")
    cols = pt.get("colors") or []
    if not isinstance(cols, list) or len(cols) > 3 or any(not (isinstance(c, str) and HEX.match(c)) for c in cols):
        errors.append("particles.colors: up to 3 hex colours")
    d = pt.get("density", 1)
    if not isinstance(d, (int, float)) or not 0.2 <= d <= 2:
        errors.append("particles.density must be 0.2-2")
    for k in spec:
        if k not in ("id", "name", "blurb", "mode", "palette", "inks", "fonts", "caps", "tracking", "shape", "backdrop", "particles", *META):
            warnings.append(f"unknown key {k!r} is ignored")
    return spec, errors, warnings


def preview_svg(spec: dict) -> str:
    """A small picture of the app in the theme's colours: rail, sidebar, a title, the ink stripe, a primary button."""
    p = {k: norm(v) for k, v in spec["palette"].items() if isinstance(v, str) and HEX.match(v)}
    inks = [norm(c) for c in (spec.get("inks") or [])] or [p["accent"], p.get("brand", p["accent"])]
    shape = spec.get("shape", "soft")
    r = 2 if shape == "hard" else 18 if shape == "round" else 8
    sky = [norm(c) for c in (spec.get("backdrop") or {}).get("sky") or []] or [p["bg"]]
    stops = "".join(f'<stop offset="{i / max(1, len(sky) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(sky))
    stripe = "".join(f'<rect x="{144 + i * (64 / len(inks)):.1f}" y="62" width="{64 / len(inks):.1f}" height="4" fill="{c}"/>' for i, c in enumerate(inks))
    font = FONT_FAMILY.get((spec.get("fonts") or {}).get("display", "inter"), FONT_FAMILY["inter"])
    caps = "text-transform:uppercase;letter-spacing:0.12em;" if spec.get("caps") else ""
    btn_r = 0 if shape == "hard" else 999
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>
<linearGradient id="btn" x1="0" y1="0" x2="1" y2="0">{"".join(f'<stop offset="{i / max(1, len(inks) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(inks))}</linearGradient></defs>
<rect width="320" height="180" rx="{r}" fill="url(#sky)"/>
<rect x="0" y="0" width="44" height="180" fill="{p['panel']}"/>
<rect x="44" y="0" width="84" height="180" fill="{p['panel']}" opacity="0.6"/>
<rect x="56" y="18" width="60" height="5" rx="2" fill="{p['text']}" opacity="0.5"/>
<rect x="56" y="34" width="52" height="5" rx="2" fill="{p['text']}" opacity="0.25"/>
<rect x="56" y="50" width="56" height="5" rx="2" fill="{p['text']}" opacity="0.25"/>
<rect x="56" y="66" width="44" height="5" rx="2" fill="{p['text']}" opacity="0.25"/>
<text x="144" y="46" font-family="{font}" font-size="18" font-weight="600" fill="{p['text']}" style="{caps}">Good evening</text>
{stripe}
<rect x="144" y="84" width="152" height="22" rx="{r}" fill="{p['panel']}" stroke="{p['text']}" stroke-opacity="0.13"/>
<rect x="144" y="114" width="118" height="22" rx="{r}" fill="{p['panel']}" stroke="{p['text']}" stroke-opacity="0.13"/>
<rect x="228" y="148" width="68" height="18" rx="{btn_r}" fill="url(#btn)"/>
</svg>
'''


def main() -> int:
    check_only = "--check" in sys.argv
    index, bad = [], 0
    for path in sorted(THEMES.glob("*/theme.json")):
        spec, errors, warnings = check(path)
        tag = path.parent.name
        for w in warnings:
            print(f"  {tag}: warning: {w}")
        for e in errors:
            print(f"  {tag}: ERROR: {e}")
        if errors or spec is None:
            bad += 1
            continue
        pal = spec["palette"]
        index.append({
            "id": tag, "name": spec["name"], "blurb": spec.get("blurb", ""), "mode": spec["mode"],
            "author": spec.get("author", ""), "license": spec.get("license", ""), "version": spec.get("version", "1.0"),
            "tags": spec.get("tags", []), "path": f"themes/{tag}/theme.json", "preview": f"themes/{tag}/preview.svg",
            "swatch": {"bg": norm(pal["bg"]), "panel": norm(pal["panel"]), "text": norm(pal["text"]),
                       "inks": [norm(c) for c in (spec.get("inks") or [pal["accent"], pal["brand"]])]},
            "fonts": spec.get("fonts", {}), "shape": spec.get("shape", "soft"),
            "particles": (spec.get("particles") or {}).get("kind", "none"), "horizon": (spec.get("backdrop") or {}).get("horizon", "none"),
        })
        if not check_only:
            (path.parent / "preview.svg").write_text(preview_svg(spec))
    for d in sorted(p for p in THEMES.iterdir() if p.is_dir()):
        if not (d / "theme.json").exists():
            print(f"  {d.name}: ERROR: no theme.json")
            bad += 1
    if not check_only:
        (ROOT / "index.json").write_text(json.dumps({"format": 1, "kind": "theme", "items": index}, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(index)} theme{'s' if len(index) != 1 else ''} ok, {bad} with errors")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
