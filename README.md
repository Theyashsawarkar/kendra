# kendra

**kendra** (केन्द्र, "centre") — Quick settings. A tool for [Vyom](https://github.com/Theyashsawarkar/vyom), the keyboard-driven panels of [Vayu](https://github.com/Theyashsawarkar/vayu); in Vayu it replaces the theme / wallpaper / caffeine capsules on the bar.

> Quick settings: Wi-Fi, Bluetooth, hotspot, DND, caffeine, theme, wallpaper, power profile, volume, brightness, battery, lock, power.

## Features

- A panel under the bar's top-right corner: a greeting, uptime and battery, **lock and power** buttons.
- Tiles: **Wi‑Fi, Bluetooth, hotspot, do not disturb, caffeine, dark theme, new wallpaper, power profile**, each saying what it's doing; right click / `Shift+Enter` opens a tile's details.
- **Volume and brightness** sliders (click the speaker to mute).
- Opens instantly with the last state, then refreshes every tile in the background; anything the machine doesn't have isn't shown.
- Any tile can be driven by your own commands (`status` / `toggle` / `on` / `off`, matched with `on_when`).

## Keys

| Key | Action |
|---|---|
| `Arrows` | Move between the toggles and sliders |
| `Enter / Space` | Toggle the focused setting |
| `Shift+Enter` | Open the focused setting's details (e.g. the Wi-Fi list) |
| `Esc` | Close quick settings |
| `Esc` | close |

Every Vyom panel also has: `Up`/`Down` (or `Ctrl+K`/`Ctrl+J`) to move, `Page Up`/`Page Down`, `Tab` to switch to the next tool.

## Requirements

- [Vyom](https://github.com/Theyashsawarkar/vyom) 0.2 or newer (Python 3.11+, GTK 4, gtk4-layer-shell, a layer-shell compositor)
- optional: nmcli, bluetoothctl, makoctl, gsettings, powerprofilesctl, wpctl, brightnessctl (each tile uses what's there)

## Install

```sh
git clone https://github.com/Theyashsawarkar/kendra ~/.local/share/vyom/plugins/kendra
vyom reload        # or log out and in
vyom kendra         # open it (again: close it)
```

Bind it to a key, e.g. in sway:

```
bindsym $mod+<key> exec vyom kendra
```

Update: `git -C ~/.local/share/vyom/plugins/kendra pull && vyom reload`. `vyom list` shows every installed tool and why one would be skipped.

## Configuration

In `~/.config/vyom/config.toml` (all optional):

```toml
[plugin.kendra]
# tiles: which tiles, in order (default: wifi bluetooth hotspot dnd caffeine theme wallpaper power-profile)
# lock / power: the header buttons (default: loginctl lock-session / (none))
# tile.<name>: per tile: open, status, on_when, toggle, on, off, subtitle_on/off, title, icon, color (default: )
# margin_top / margin_right: position under the bar (default: 6 / 8)
```

## License

MIT.
