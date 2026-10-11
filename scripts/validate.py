#!/usr/bin/env python3
"""Check every theme in themes/<id>/theme.json, draw its preview.svg, build index.json and the gallery in README.md.

Mirrors the rules Shell:B applies on install (server/themes.py `clean`): colours must be hex, choices come from fixed
lists, body text must reach WCAG AAA (7:1) on the page and panels, secondary text AA (4.5:1), the accent must carry a
readable label. A theme that needs nudging still installs (Shell:B adjusts it), but this script reports the nudge so you
can fix the design yourself. The preview is a small drawing of the app in the theme (sky, glows, stars, the horizon
silhouette from scenery/, the chrome in the theme's colours and fonts); it is deterministic, so CI can check it is
current. Standard library only; run from the repository root:

    python3 -I scripts/validate.py          # check + rebuild previews, index.json and the README gallery
    python3 -I scripts/validate.py --check  # check only (CI); exits 1 on any error or stale generated file
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"
SCENERY = ROOT / "scenery"
README = ROOT / "README.md"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
URL_RE = re.compile(r"^https?://[^\s\"'<>]{1,200}$")
START, END = "<!-- gallery:start -->", "<!-- gallery:end -->"

FONTS = ("inter", "barlow", "barlow-condensed", "shippori-mincho", "josefin-sans", "jetbrains-mono", "georgia",
         "cormorant-garamond", "sora", "syncopate", "outfit", "zen-maru-gothic")
BODY_FONTS = ("inter", "barlow", "shippori-mincho", "georgia", "sora", "outfit", "zen-maru-gothic")
SHAPES = ("soft", "hard", "round")
HORIZONS = ("none", "forest", "mountains", "floating", "waves", "city", "seafloor", "dunes", "snowpines", "hills")
PARTICLES = ("none", "fireflies", "petals", "leaves", "woodsprites", "snow", "embers", "bubbles", "bokeh", "sand", "rain", "abyss", "aurora")
PALETTE = ("bg", "panel", "raised", "hover", "code", "text", "text2", "muted", "accent", "brand", "line")
REQUIRED_PALETTE = ("bg", "panel", "text", "text2", "muted", "accent", "brand")
META = ("author", "authorUrl", "license", "version", "tags", "homepage", "credits")
KNOWN = ("id", "name", "blurb", "mode", "palette", "inks", "fonts", "caps", "tracking", "shape", "backdrop", "particles", *META)
FONT_FAMILY = {
    "inter": "Inter, system-ui, sans-serif", "barlow": "Barlow, sans-serif", "barlow-condensed": "'Barlow Condensed', sans-serif",
    "shippori-mincho": "'Shippori Mincho', serif", "josefin-sans": "'Josefin Sans', sans-serif", "jetbrains-mono": "'JetBrains Mono', monospace",
    "georgia": "Georgia, serif", "cormorant-garamond": "'Cormorant Garamond', serif", "sora": "Sora, sans-serif",
    "syncopate": "Syncopate, sans-serif", "outfit": "Outfit, sans-serif", "zen-maru-gothic": "'Zen Maru Gothic', sans-serif",
}
# the silhouette files and, as in Shell:B, the height each one is drawn at (px in a 900 px window; 'floating' fills 70 %)
HORIZON_FILES = {"forest": ("normandy-treeline.svg", 150), "mountains": ("mountains.svg", 300), "floating": ("pandora-isles.svg", 760),
                 "waves": ("waves.svg", 200), "city": ("city.svg", 420), "seafloor": ("seafloor.svg", 260), "dunes": ("dunes.svg", 360),
                 "snowpines": ("snowpines.svg", 260), "hills": ("hills.svg", 420)}


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


def mix(a: str, b: str, t: float) -> str:
    pa, pb = ([int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


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
        if not spec.get(key) or not isinstance(spec[key], str):
            errors.append(f"{key} is required (license: an SPDX id such as MIT or CC0-1.0)")
    if isinstance(spec.get("author"), str) and len(spec["author"]) > 80:
        errors.append("author: at most 80 characters")
    for key in ("authorUrl", "homepage"):
        if spec.get(key) is not None and not (isinstance(spec[key], str) and URL_RE.match(spec[key])):
            errors.append(f"{key} must be an http(s) URL")
    credits = spec.get("credits")
    if credits is not None:
        if not isinstance(credits, list) or any(not isinstance(c, dict) or not c.get("what") or not c.get("author") or not c.get("license") for c in credits):
            errors.append("credits: a list of {what, author, license, url?} for anything you didn't make yourself")
        elif any(c.get("url") is not None and not (isinstance(c["url"], str) and URL_RE.match(c["url"])) for c in credits):
            errors.append("credits[].url must be an http(s) URL")

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
        if k not in KNOWN:
            warnings.append(f"unknown key {k!r} is ignored")
    return spec, errors, warnings


# ── preview ──────────────────────────────────────────────────────────────────

def _rng(seed: str):
    """A tiny deterministic generator so previews don't change between runs."""
    s = sum(ord(c) * (i + 1) for i, c in enumerate(seed)) & 0xffffffff or 1

    def rnd():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7fffffff
        return s / 0x7fffffff
    return rnd


def _horizon_svg(kind: str, color: str, W: int, H: int) -> str:
    """The silhouette as Shell:B draws it: a 1600 px tile repeated along the bottom at a 1440 px window's scale, or the
    floating islands centred at 70 % height."""
    if kind not in HORIZON_FILES:
        return ""
    fname, px = HORIZON_FILES[kind]
    try:
        src = (SCENERY / fname).read_text()
    except OSError:
        return ""
    m = re.search(r"viewBox=['\"]([\d. -]+)['\"]", src)
    inner = re.sub(r"^.*?<svg[^>]*>", "", src, count=1, flags=re.S).rsplit("</svg>", 1)[0]
    inner = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->", "", inner, flags=re.S).strip()
    # Shell:B uses the file as a CSS mask, so only its alpha counts: flatten every fill and stroke to the horizon colour
    inner = re.sub(r"\b(fill|stroke)=(['\"])(?!none\2)[^'\"]*\2", lambda m: f"{m.group(1)}={m.group(2)}{color}{m.group(2)}", inner)
    inner = re.sub(r"\b(fill|stroke):\s*(?!none)[^;'\"]+", lambda m: f"{m.group(1)}:{color}", inner)
    vb = m.group(1) if m else f"0 0 1600 {px}"
    _, _, vw, vh = (float(v) for v in vb.split())
    scale = W / 1440
    if kind == "floating":
        h = 0.7 * H
        w = vw / vh * h
        return (f'<svg x="{(W - w) / 2:.1f}" y="{H - h:.1f}" width="{w:.1f}" height="{h:.1f}" viewBox="{vb}" preserveAspectRatio="xMidYMax meet">'
                f'<g fill="{color}">{inner}</g></svg>')
    h = min(240, px) * scale
    w = 1600 * scale
    tiles = "".join(f'<svg x="{i * w:.1f}" y="{H - h:.1f}" width="{w:.1f}" height="{h:.1f}" viewBox="{vb}" preserveAspectRatio="none">'
                    f'<g fill="{color}">{inner}</g></svg>' for i in range(int(W / w) + 1))
    return tiles


def preview_svg(spec: dict) -> str:
    """The app in the theme: sky, glows and stars, the horizon, then the chrome in the theme's colours and fonts."""
    W, H = 480, 270
    p = {k: norm(v) for k, v in spec["palette"].items() if isinstance(v, str) and HEX.match(v)}
    dark = spec["mode"] != "light"
    panel, text, accent = p["panel"], p["text"], p["accent"]
    raised = p.get("raised") or mix(panel, text, 0.06)
    inks = [norm(c) for c in (spec.get("inks") or [])] or [accent, p.get("brand", accent)]
    shape = spec.get("shape", "soft")
    r = 2 if shape == "hard" else 14 if shape == "round" else 7
    bd = spec.get("backdrop") or {}
    sky = [norm(c) for c in (bd.get("sky") or [])] or [p["bg"]]
    stops = "".join(f'<stop offset="{i / max(1, len(sky) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(sky))
    defs = [f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>',
            '<linearGradient id="btn" x1="0" y1="0" x2="1" y2="0">'
            + "".join(f'<stop offset="{i / max(1, len(inks) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(inks)) + "</linearGradient>"]
    layers = [f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']
    for i, g in enumerate((bd.get("glows") or [])[:4]):
        c = norm(g["color"]) if isinstance(g, dict) and isinstance(g.get("color"), str) and HEX.match(g["color"]) else None
        if not c:
            continue
        s = float(g.get("size", 50)); st = float(g.get("strength", 0.14))
        defs.append(f'<radialGradient id="g{i}"><stop offset="0" stop-color="{c}" stop-opacity="{st:.2f}"/><stop offset="0.7" stop-color="{c}" stop-opacity="0"/></radialGradient>')
        layers.append(f'<ellipse cx="{float(g.get("x", 50)) / 100 * W:.1f}" cy="{float(g.get("y", 50)) / 100 * H:.1f}" rx="{s / 100 * W:.1f}" ry="{0.75 * s / 100 * H:.1f}" fill="url(#g{i})"/>')
    stars = float(bd.get("stars", 0) or 0)
    if stars > 0:
        rnd = _rng(spec["name"])
        for _ in range(int(stars * 70)):
            layers.append(f'<circle cx="{rnd() * W:.1f}" cy="{rnd() * H * 0.72:.1f}" r="{0.5 + rnd() * 0.8:.2f}" fill="#ffffff" fill-opacity="{0.3 + rnd() * 0.5:.2f}"/>')
    hz = bd.get("horizon", "none")
    hc = norm(bd["horizonColor"]) if isinstance(bd.get("horizonColor"), str) and HEX.match(bd["horizonColor"]) else mix(p["bg"], "#000000", 0.4)
    layers.append(_horizon_svg(hz, hc, W, H))
    # the chrome: rail, sidebar, a greeting, the ink stripe, two cards, the composer with its primary button
    font = FONT_FAMILY.get((spec.get("fonts") or {}).get("display", "inter"), FONT_FAMILY["inter"])
    caps = "text-transform:uppercase;" if spec.get("caps") else ""
    track = f"letter-spacing:{float(spec.get('tracking', 0)) * 17:.1f}px;" if spec.get("tracking") else ""
    line_op = 0.1 if dark else 0.12
    stripe = "".join(f'<rect x="{170 + i * (72 / len(inks)):.1f}" y="88" width="{72 / len(inks):.1f}" height="4" fill="{c}"/>' for i, c in enumerate(inks))
    btn_r = 0 if shape == "hard" else 99
    chrome = f'''<rect x="0" y="0" width="44" height="{H}" fill="{panel}" fill-opacity="0.92"/>
<rect x="12" y="12" width="20" height="20" rx="{min(r, 6)}" fill="url(#btn)"/>
<rect x="44" y="0" width="100" height="{H}" fill="{panel}" fill-opacity="0.6"/>
<rect x="44" y="0" width="1" height="{H}" fill="{text}" fill-opacity="{line_op}"/>
<rect x="56" y="20" width="76" height="6" rx="3" fill="{text}" fill-opacity="0.55"/>
<rect x="56" y="40" width="64" height="5" rx="2.5" fill="{text}" fill-opacity="0.25"/>
<rect x="56" y="56" width="70" height="5" rx="2.5" fill="{text}" fill-opacity="0.25"/>
<rect x="56" y="72" width="58" height="5" rx="2.5" fill="{text}" fill-opacity="0.25"/>
<rect x="56" y="88" width="66" height="5" rx="2.5" fill="{text}" fill-opacity="0.25"/>
<text x="170" y="70" font-family="{html.escape(font, quote=True)}" font-size="22" font-weight="600" fill="{text}" style="{caps}{track}">Good evening</text>
{stripe}
<rect x="170" y="110" width="250" height="40" rx="{r}" fill="{panel}" fill-opacity="0.86" stroke="{text}" stroke-opacity="{line_op}"/>
<rect x="184" y="122" width="150" height="5" rx="2.5" fill="{text}" fill-opacity="0.6"/>
<rect x="184" y="134" width="200" height="5" rx="2.5" fill="{p.get('text2', text)}" fill-opacity="0.6"/>
<rect x="170" y="160" width="190" height="34" rx="{r}" fill="{panel}" fill-opacity="0.86" stroke="{text}" stroke-opacity="{line_op}"/>
<rect x="184" y="172" width="120" height="5" rx="2.5" fill="{text}" fill-opacity="0.6"/>
<rect x="184" y="183" width="90" height="4" rx="2" fill="{accent}" fill-opacity="0.9"/>
<rect x="170" y="224" width="290" height="30" rx="{14 if shape == 'round' else r}" fill="{raised}" fill-opacity="0.95" stroke="{text}" stroke-opacity="{line_op}"/>
<rect x="184" y="236" width="110" height="5" rx="2.5" fill="{p.get('muted', text)}" fill-opacity="0.6"/>
<rect x="414" y="230" width="38" height="18" rx="{btn_r}" fill="url(#btn)"/>'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(spec["name"], quote=True)}">\n'
            f'<defs>{"".join(defs)}</defs>\n' + "\n".join(x for x in layers if x) + "\n" + chrome + "\n</svg>\n")


# ── README gallery ───────────────────────────────────────────────────────────

def gallery_html(index: list[dict]) -> str:
    cells = []
    for it in index:
        by = html.escape(it["author"])
        if it.get("authorUrl"):
            by = f'<a href="{html.escape(it["authorUrl"], quote=True)}">{by}</a>'
        cells.append(f'<td align="center" valign="top" width="33%"><a href="{it["path"]}"><img src="{it["preview"]}" alt="{html.escape(it["name"], quote=True)}" width="100%"></a>'
                     f'<br><b>{html.escape(it["name"])}</b> · {it["mode"]}<br><sub>by {by} · {html.escape(it["license"])}</sub></td>')
    rows = "\n".join("<tr>\n" + "\n".join(cells[i:i + 3]) + "\n</tr>" for i in range(0, len(cells), 3))
    return f"{START}\n<table>\n{rows}\n</table>\n{END}"


def readme_with_gallery(index: list[dict]) -> str | None:
    text = README.read_text()
    if START not in text or END not in text:
        return None
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + gallery_html(index) + tail


def main() -> int:
    check_only = "--check" in sys.argv
    index, bad, stale = [], 0, []
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
            "author": spec.get("author", ""), "authorUrl": spec.get("authorUrl", ""), "license": spec.get("license", ""),
            "version": spec.get("version", "1.0"), "tags": spec.get("tags", []), "credits": spec.get("credits", []),
            "path": f"themes/{tag}/theme.json", "preview": f"themes/{tag}/preview.svg",
            "swatch": {"bg": norm(pal["bg"]), "panel": norm(pal["panel"]), "text": norm(pal["text"]),
                       "inks": [norm(c) for c in (spec.get("inks") or [pal["accent"], pal["brand"]])]},
            "fonts": spec.get("fonts", {}), "shape": spec.get("shape", "soft"),
            "particles": (spec.get("particles") or {}).get("kind", "none"), "horizon": (spec.get("backdrop") or {}).get("horizon", "none"),
        })
        svg = preview_svg(spec)
        out = path.parent / "preview.svg"
        if check_only:
            if not out.exists() or out.read_text() != svg:
                stale.append(str(out.relative_to(ROOT)))
        else:
            out.write_text(svg)
    for d in sorted(p for p in THEMES.iterdir() if p.is_dir()):
        if not (d / "theme.json").exists():
            print(f"  {d.name}: ERROR: no theme.json")
            bad += 1
    idx = json.dumps({"format": 1, "kind": "theme", "items": index}, indent=1, ensure_ascii=False) + "\n"
    readme = readme_with_gallery(index)
    if check_only:
        if not (ROOT / "index.json").exists() or (ROOT / "index.json").read_text() != idx:
            stale.append("index.json")
        if readme is not None and readme != README.read_text():
            stale.append("README.md (gallery)")
        for s in stale:
            print(f"  stale: {s} (run scripts/validate.py and commit)")
    else:
        (ROOT / "index.json").write_text(idx)
        if readme is not None:
            README.write_text(readme)
    print(f"{len(index)} theme{'s' if len(index) != 1 else ''} ok, {bad} with errors" + (f", {len(stale)} generated file(s) stale" if stale else ""))
    return 1 if bad or stale else 0


if __name__ == "__main__":
    sys.exit(main())
