<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img alt="kendra" src="assets/banner-dark.svg" width="560">
  </picture>
</p>

<p align="center">
  <b>Quick settings: Wi-Fi, Bluetooth, hotspot, DND, caffeine, theme, wallpaper, power profile, volume, brightness, battery, lock, power.</b><br>
  Quick settings. A tool for <a href="https://github.com/Theyashsawarkar/vyom">Vyom</a>, keyboard-driven panels for Wayland.
</p>

<p align="center">
  <a href="https://github.com/Theyashsawarkar/kendra/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Theyashsawarkar/kendra/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/Theyashsawarkar/kendra/releases"><img alt="Release" src="https://img.shields.io/github/v/release/Theyashsawarkar/kendra?color=cba6f7&label=release"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-f5e0dc"></a>
  <a href="https://github.com/Theyashsawarkar/vyom"><img alt="Vyom 0.2.4+" src="https://img.shields.io/badge/vyom-0.2.4%2B-89b4fa"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-a6e3a1">
  <img alt="Wayland" src="https://img.shields.io/badge/wayland-layer--shell-94e2d5">
</p>

<p align="center">
  <img alt="kendra: quick settings panel" src="assets/screenshots/kendra.png" width="100%">
</p>

> *Kendra* (केन्द्र) is Sanskrit for "centre": the centre every quick setting sits in.

kendra is quick settings for [Vyom](https://github.com/Theyashsawarkar/vyom): one keyboard-driven panel that opens instantly, with live data, a preview and a key for everything. It runs on any compositor with the layer-shell protocol (sway, Hyprland, river, niri, Wayfire, labwc…). In [Vayu](https://github.com/Theyashsawarkar/vayu), the desktop it was built for, it replaces the theme / wallpaper / caffeine capsules on the bar.

## Contents

- [Features](#features)
- [Install](#install)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [The Vyom family](#the-vyom-family)
- [Contributing](#contributing)
- [License](#license)

## Features

- A panel under the bar's top-right corner: a greeting, uptime and battery, **lock and power** buttons.
- Tiles: **Wi‑Fi, Bluetooth, hotspot, do not disturb, caffeine, dark theme, new wallpaper, power profile**, each saying what it's doing; right click / `Shift+Enter` opens a tile's details.
- **Volume and brightness** sliders (click the speaker to mute).
- Opens instantly with the last state, then refreshes every tile in the background; anything the machine doesn't have isn't shown.
- Any tile can be driven by your own commands (`status` / `toggle` / `on` / `off`, matched with `on_when`).
- Keyboard first: every action has a key, shown in the footer; the mouse works too.
- Never freezes the panel: slow commands run in the background.

## Install

### Requirements

- [Vyom](https://github.com/Theyashsawarkar/vyom) 0.2.4 or newer (Python 3.11+, PyGObject, GTK 4, [gtk4-layer-shell](https://github.com/wmww/gtk4-layer-shell), a Nerd Font)
- optional: nmcli, bluetoothctl, makoctl, gsettings, powerprofilesctl, wpctl, brightnessctl (each tile uses what's there)

### Install

```sh
git clone https://github.com/Theyashsawarkar/kendra ~/.local/share/vyom/plugins/kendra
vyom reload           # pick it up (or log out and in)
vyom kendra            # open it; run it again to close
```

Give it a key in your compositor, e.g. sway:

```sh
bindsym $mod+<key> exec vyom kendra
```

### Update and uninstall

```sh
git -C ~/.local/share/vyom/plugins/kendra pull && vyom reload     # update
rm -rf ~/.local/share/vyom/plugins/kendra && vyom reload          # uninstall
```

## Usage

Open it with `vyom kendra` (or your key). Type to search; the footer always shows the keys for what's selected.

| Key | Action |
|---|---|
| `Arrows` | Move between the toggles and sliders |
| `Enter / Space` | Toggle the focused setting |
| `Shift+Enter` | Open the focused setting's details (e.g. the Wi-Fi list) |
| `Esc` | Close quick settings |
| `Esc` | Close the panel |

Every Vyom panel also has `Up`/`Down` (or `Ctrl+K`/`Ctrl+J`) to move, `Page Up`/`Page Down` to jump and `Tab` to switch to the next tool.

## Configuration

Everything is optional, in `~/.config/vyom/config.toml` under `[plugin.kendra]`:

| Setting | Default | What it does |
|---|---|---|
| `tiles` | wifi bluetooth hotspot dnd caffeine theme wallpaper power-profile | Which tiles, in order |
| `lock / power` | loginctl lock-session / (none) | The header buttons |
| `tile.<name>` | (none) | Per tile: open, status, on_when, toggle, on, off, subtitle_on/off, title, icon, color |
| `margin_top / margin_right` | 6 / 8 | Position under the bar |

Run `vyom reload` after editing.

## Troubleshooting

- **Nothing opens.** `vyom list` shows every installed tool, and why one is skipped (a missing requirement, or a Vyom that's too old).
- **It opened, then something failed.** Look for a `Traceback` in `~/.local/state/vyom/daemon.log`, and [open an issue](https://github.com/Theyashsawarkar/kendra/issues/new/choose) with it.
- **No blur or rounded corners.** That's the compositor: on SwayFX, add `layer_effects "vyom" { blur enable; corner_radius 20; shadows enable }`.

## The Vyom family

Each tool is its own repository, so you install only the ones you want:

| Tool | | What it does |
|---|---|---|
| [dvara](https://github.com/Theyashsawarkar/dvara) | द्वार, gateway | The app launcher |
| [ganit](https://github.com/Theyashsawarkar/ganit) | गणित, mathematics | The calculator and converter |
| [smriti](https://github.com/Theyashsawarkar/smriti) | स्मृति, memory | Clipboard history |
| [bhava](https://github.com/Theyashsawarkar/bhava) | भाव, feeling, emotion | The emoji picker |
| [tarang](https://github.com/Theyashsawarkar/tarang) | तरंग, wave | Wi‑Fi and the hotspot |
| [setu](https://github.com/Theyashsawarkar/setu) | सेतु, bridge | Bluetooth |
| [doot](https://github.com/Theyashsawarkar/doot) | दूत, messenger | Your phone, through KDE Connect |
| [patra](https://github.com/Theyashsawarkar/patra) | पात्र, vessel | Docker containers |
| [suchana](https://github.com/Theyashsawarkar/suchana) | सूचना, notice | Notifications |
| [raga](https://github.com/Theyashsawarkar/raga) | राग, melody | YouTube music and video |
| [mudra](https://github.com/Theyashsawarkar/mudra) | मुद्रा, gesture | Keybinding search |
| [urja](https://github.com/Theyashsawarkar/urja) | ऊर्जा, energy | The battery at a glance |
| [vishram](https://github.com/Theyashsawarkar/vishram) | विश्राम, rest | The power menu |
| [kendra](https://github.com/Theyashsawarkar/kendra) (this one) | केन्द्र, centre | Quick settings |

## Contributing

Bug reports, ideas and pull requests are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and the few rules every tool follows, and [CHANGELOG.md](CHANGELOG.md) for what changed in each release. Please report security issues privately ([SECURITY.md](SECURITY.md)).

## License

[MIT](LICENSE).
