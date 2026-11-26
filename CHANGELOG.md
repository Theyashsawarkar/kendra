# Changelog

Newest first. Releases are tags (`vX.Y.Z`).

## v0.6.1 -- 2026-11-26

- A smaller panel: about 15% narrower and shorter, with smaller circles, numbers and gaps.

## v0.6.0 -- 2026-11-26

- **A new panel: the bento.** Wi-Fi and Bluetooth are big squares (the circle toggles, the arrow or a right click opens tarang / setu). Wi-Fi shows its signal bars, the download speed big with upload beside it, and the last minute as two lines (download and upload), each with its peak. Bluetooth shows the device that matters: one at 20% or less, else the one connected most recently; earbuds as Left and Right in big light numbers with the case under them and what's charging, the rest as "+N more". Volume and brightness stand as tall capsules. Jyoti (Off, Akhaṇḍa, Nandādīpa) and power mode (Saver, Balanced, Performance) are segments where the chosen one grows to show its name. Hotspot, phone link, quiet and theme are circles: left click toggles, right click opens their panel. The wallpaper you're on is a pill with its name; click it for a new one. Your initial sits in a ring that is the battery, and one line at the bottom says what's under the pointer.
- New screenshots in the Spatial look, taken with made-up demo data (WebP, sharp on high-density screens).
- The website, closer to Vayu's own: the tool's screenshot blurred behind the page, a centred hero with the logo and the verse, the page you're on as the white pill, glass "On this page" and footer panels, releases as cards. No glow behind the logo, no coloured line beside the verse.
- **Spatial look**: tiles are borderless glass with 20 px corners and round icons that fill with their colour when on; on tiles are brighter glass; lock, power, levels and slider icons are round; thicker pill sliders; where you are is a light rim.
- The website has Vayu's Spatial look: graphite glass, a floating navigation bar, near-white for links and the main button, and the tool's own colour only as its signature (the logo's glow, the shloka's line, the release dots). No more all-caps labels.

## v0.5.0 -- 2026-11-24

- **Tiles can have levels**: `levels = [{ name, when, set }, …]` on a command tile. While it's on, a row under the tiles shows a button per level (the current one filled in the tile's colour) to switch with a click or `j` and `Enter`, and the tile's subtitle names the level. For Jyoti in Vayu: Akhaṇḍa or Nandādīpa, where quick settings could only turn it on or off.
- **Fixed: the Jyoti tile's title sat further right than every other tile's**, and its row could grow tall: the flame's square took the tile's spare room.
- **Jyoti's icon is a flame**: ekatva's flame in one colour, its heart cut out, painted in the tile's colour. A vector, sharp at the 18 px it's shown at.

## v0.4.0 -- 2026-11-17

- **The caffeine tile is now Jyoti** (ज्योति, the flame), as across Vayu and ekatva, with its lamp, the diya, as a line drawing. Its key in `tiles` and `[plugin.kendra.tile.…]` is `jyoti`; `caffeine` still works.
- A tile can have a line drawing for its icon: `icon_svg = "path/to.svg"` (in `currentColor`), painted in the icon's colour like a glyph.

## v0.3.1 -- 2026-11-09

- **A click on a tile's `>` arrow opens its panel** (Wi-Fi in tarang, Bluetooth in setu, the hotspot); a click anywhere else on the tile still toggles it.
- **More compact**: about 450 px wide instead of 700 (Vyom 0.7.1's footer no longer widens a card), with smaller tiles, icons, sliders and gaps; the footer shows `Enter toggle` (`?` lists every key).

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
