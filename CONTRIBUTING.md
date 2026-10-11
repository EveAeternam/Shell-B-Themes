# Contributing a theme

1. Fork the repository and add a folder `themes/<id>/` with a `theme.json`. The id is lowercase letters, digits and
   dashes (`tidepool`, `lantern-festival`), and it must not already exist.
2. Fill in `name`, `blurb`, `mode`, `author` and `license`. The license is an SPDX id (MIT, CC0-1.0, CC-BY-4.0). By
   opening a pull request you agree that the theme is shared under the license you named.
3. Run `python3 -I scripts/validate.py` from the repository root. Fix every error; look at every warning (a warning means
   Shell:B will move a colour for contrast, which usually means the design would rather pick a different colour).
4. Commit `theme.json`, the generated `preview.svg` and the updated `index.json`.
5. Open a pull request. The description says what the theme is for and, if it is inspired by something, what.

Themes are reviewed for taste as well as validity: one clear direction, readable text, no eye-watering accents. Themes
that imitate a company's branding or an existing product's exact look are not merged.

Updating a theme: bump `version`, keep the id. Shell:B shows a newer version as available after the next refresh.
