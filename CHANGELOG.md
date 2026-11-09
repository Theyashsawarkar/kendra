# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.3.0 -- 2026-11-09

- **No more accidental lock.** `l` no longer locks the screen (it moves
  right): lock is `Space l`, the power menu `Space p` (`p` still works).
  `Space` no longer toggles the focused tile; `Enter` does. `L` says where
  lock went, for one release.
- **Vim keys** (Vyom 0.7): always NORMAL (there's nothing to type);
  `h` / `j` / `k` / `l` move through the tile grid by where things are on
  screen (`l` never jumps rows) and down into the sliders, `gg` / `G` to the
  first tile / the last slider. On a slider `h` / `l` change it by 5 (a count
  first: `3l` is +15) and `0` / `$` go to its ends; `Enter` there mutes.
- **`o` opens a tile's details** (Wi-Fi in tarang, Bluetooth in setu);
  `Right` no longer does, so it moves right like everywhere else.
  `Shift+Enter` still opens them.
- **New keys**: `Space g w` / `g b` / `g h` / `g p` / `g a` open Wi-Fi,
  Bluetooth, the hotspot, the power menu, the battery; `Space r` reloads every
  tile.
- `m` mutes (it was documented as `M`, but Shift never worked); Vyom's footer
  shows the keys.
- Keys are data (`kendra/vim.py`); `scripts/keybinds.py` writes the
  `# keybind:` lines and the README table from it (`--check` in CI).
- Needs Vyom 0.7.0.

## v0.2.0 -- 2026-11-07

- **Every tile says On or Off**, and an "on" tile fills its icon in the tile's colour (no more guessing from a faint tint).
- **Wi‑Fi and Bluetooth name what they're on**, with the headphones' battery ("WH-1000XM5 · 78%"). `Right` opens their details: tarang and setu when they're installed, even without an `open` command.
- **Sliders show their value** ("80%", "Muted" in red), with a thicker track, a bigger thumb and an icon button; volume names the output device. On a slider, Up / Down move on instead of changing it.
- New keys: `M` mutes, `L` locks, `P` opens the power menu (vishram inside Vyom when you haven't set `power`).
- The header shows the battery and uptime as chips (uptime in days once it's long); lock and power are set apart, power in red.
- A clear accent frame on the tile or slider you're on.
- The dark theme tile names the GTK theme; a few subtitles start with a capital now.
- Needs Vyom 0.6.0.
- Every corner is rounded: the website's callouts.
- A logo and a shloka at the top of the README and the website: every Vayu tool has them now.

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
