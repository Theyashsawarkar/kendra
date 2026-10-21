# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.1.3 -- 2026-10-21

- Follows the theme: its colours are named (`@accent`, `@crust`...) instead
  of fixed hex codes, so a theme that redefines them (Vyom 0.2.9's `css`,
  e.g. [varna](https://github.com/Theyashsawarkar/varna)) recolours it too.

## v0.1.2 -- 2026-10-21

- A website (GitHub Pages, https://theyashsawarkar.github.io/kendra/): the README as a home page, the
  changelog, and architecture decision records (`docs/adr/`), built from these files by
  `scripts/build-site.py`; CI checks the site is up to date.

## v0.1.1 -- 2026-10-21

- Documentation for open source: a logo and banner, a full README (features,
  install, usage, configuration, troubleshooting, the whole Vyom family),
  CONTRIBUTING, SECURITY and CODE_OF_CONDUCT, issue and pull request
  templates, and CI (compiles, checks plugin.toml and that every key is
  documented).

## v0.1.0 -- 2026-10-19

- First release, as its own repository: quick settings. Replaces the theme / wallpaper / caffeine capsules on the bar in Vayu.
- A panel under the bar's top-right corner: a greeting, uptime and battery, **lock and power** buttons.
- Tiles: **Wi‑Fi, Bluetooth, hotspot, do not disturb, caffeine, dark theme, new wallpaper, power profile**, each saying what it's doing; right click / `Shift+Enter` opens a tile's details.
- **Volume and brightness** sliders (click the speaker to mute).
- Opens instantly with the last state, then refreshes every tile in the background; anything the machine doesn't have isn't shown.
- Any tile can be driven by your own commands (`status` / `toggle` / `on` / `off`, matched with `on_when`).
