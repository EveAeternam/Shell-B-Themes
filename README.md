# Shell:B Themes

Community themes for [Shell:B](https://github.com/EveAeternam/Shell-B), the local-first AI workspace.

A Shell:B theme is **data, not CSS**: a palette, two fonts from a fixed list, a corner shape, a backdrop (sky gradient,
soft glows, stars, a horizon silhouette) and a particle layer drifting behind the app. Shell:B turns that into a
stylesheet itself and checks everything on install: colours must be hex, choices come from fixed lists, and text is
nudged until it meets WCAG AA on its background. A theme file can change how Shell:B looks, and nothing else.

## Install one

In Shell:B open **Settings → Appearance**. Under *Community themes* you see this repository's catalogue, with a tile per
theme. **Install** adds it to your own themes (the ones Shell:B designs in chat live there too) and applies it. Shell:B
fetches this repository as a tarball at a pinned commit and reads `index.json`, so browsing works offline once fetched.

You can also paste a `theme.json` into a chat and ask Shell:B to apply it: the `design_theme` tool takes the same shape.

## Catalogue

| Theme | Mode | Look |
|---|---|---|
| Tidepool | light | Sea-glass greens on wet sand, bubbles rising, a waves horizon |
| Observatory | dark | Midnight navy, brass accent, the Milky Way over a mountain ridge |
| Paper & Ink | light | Cream stock, charcoal ink, one vermilion stamp; serif, nothing moving |
| Monsoon | dark | Slate-grey city in the rain, lamplight and teal neon |
| Lantern Festival | dark | Plum night, paper lanterns drifting over the hills |
| Glacier | light | Cold whites and glacier blue, snow pines, falling snow |
| Ember Forge | dark | Iron and charcoal lit from below, embers rising, hard panels |
| Moss | dark | Greens on green, fireflies between the trunks, rounded shapes |
| Phosphor | dark | Green phosphor on black glass, monospaced, square corners |
| Sunday Morning | light | Butter light, marmalade and sky blue over green hills |

`index.json` is the machine-readable version of this table; `themes/<id>/preview.svg` is a thumbnail of each.

## Make one

The quickest way is to let Shell:B do it: in **Settings → Appearance** describe a look and press *Design theme*, refine
it in the chat, then *Export* it from the picker. That gives you a `theme.json` ready for this repository.

By hand, copy any folder under `themes/` and edit. The format:

```jsonc
{
  "name": "Tidepool",                 // 1-32 characters
  "blurb": "One sentence for the picker (≤ 160 characters)",
  "mode": "light",                    // or "dark": a theme designs one mode
  "author": "Your name",
  "license": "MIT",                   // an SPDX id: MIT, CC0-1.0, CC-BY-4.0 …
  "version": "1.0",
  "tags": ["sea", "light"],
  "palette": {                        // all hex; see the table below
    "bg": "#eef5f1", "panel": "#f7fbf8", "raised": "#e1ece6", "hover": "#d3e3da", "code": "#f2f7f4",
    "text": "#10302a", "text2": "#3f5f58", "muted": "#5b746e",
    "accent": "#0f7f73", "brand": "#2c6fb0", "line": "#0a2a24"
  },
  "inks": ["#0f7f73", "#2c6fb0", "#e8b86a"],   // 2-4 signature colours for the picker stripe and buttons
  "fonts": { "display": "sora", "body": "sora" },
  "caps": false,                      // uppercase headings
  "tracking": 0,                      // heading letter-spacing in em, -0.02 to 0.24 (caps want 0.08+)
  "shape": "round",                   // soft | hard | round
  "backdrop": {
    "sky": ["#f4f9f6", "#e4f0ea", "#cfe4dc"],      // 1-3 colours, top to bottom
    "glows": [ { "x": 80, "y": 10, "size": 60, "strength": 0.18, "color": "#ffffff" } ],   // ≤ 4 soft lights
    "stars": 0,                       // 0-1 star density
    "horizon": "waves",               // none | forest | mountains | floating | waves | city | seafloor | dunes | snowpines | hills
    "horizonColor": "#9fcabd"
  },
  "particles": { "kind": "bubbles", "colors": ["#ffffff", "#bfe6da"], "density": 0.7 }
}
```

| Palette key | Used for | Contrast rule |
|---|---|---|
| `bg` | page background | |
| `panel` | sidebar and cards | |
| `raised` | inputs, chips, raised surfaces | derived from panel if omitted |
| `hover` | hover and selected rows | derived if omitted |
| `code` | code blocks | derived if omitted |
| `text` | body text | 7:1 on bg and panel |
| `text2` | secondary text | 4.5:1 |
| `muted` | labels, timestamps | 4.5:1 |
| `accent` | primary buttons, links, focus | its label (white or near-black) must reach 4.5:1 |
| `brand` | logo and secondary highlights | |
| `line` | borders, drawn translucent | |

Fonts for `display`: `inter`, `barlow`, `barlow-condensed`, `shippori-mincho`, `josefin-sans`, `jetbrains-mono`,
`georgia`, `cormorant-garamond`, `sora`, `syncopate`, `outfit`, `zen-maru-gothic`. For `body` only the readable ones:
`inter`, `barlow`, `shippori-mincho`, `georgia`, `sora`, `outfit`, `zen-maru-gothic`.

Particles: `none`, `fireflies`, `petals`, `leaves`, `woodsprites`, `snow`, `embers`, `bubbles`, `bokeh`, `sand`,
`rain` (wet window over city bokeh), `abyss` (jellyfish and marine snow), `aurora` (curtains plus snow).

Design it like an art director: one direction, a restrained palette (60 % surfaces, 30 % structure, 10 % accent), deep
tinted neutrals rather than pure black, warm or cool off-whites rather than pure white, one strong accent used sparingly.

Then check it:

```bash
python3 -I scripts/validate.py
```

This reports errors (the theme won't load) and warnings (Shell:B would adjust a colour for contrast), rebuilds
`index.json` and writes `preview.svg` next to your theme. See [CONTRIBUTING.md](CONTRIBUTING.md) for the pull request
checklist. The formal schema is in [theme.schema.json](theme.schema.json).

## License

The scripts and this repository are MIT. Each theme names its own license in `theme.json`; the ones here are MIT too.
