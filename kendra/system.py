"""What kendra's tiles and sliders read and change.

Every tile has a generic built-in (NetworkManager, BlueZ, mako, gsettings,
power-profiles-daemon...) and can be pointed at your own commands in
~/.config/vyom/config.toml ([plugin.kendra], see examples/config.toml). A tile
whose tool isn't installed, or whose hardware isn't there (no Bluetooth
controller, no backlight, no battery), simply isn't shown.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import time


ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


def expand(cmd):
    return os.path.expanduser(os.path.expandvars(cmd))


def run(cmd, timeout=4):
    """Runs a command (a string goes through the shell, a list doesn't).
    Returns (exit code, stdout stripped); a missing tool or a timeout is
    (127, "")."""
    try:
        r = subprocess.run(expand(cmd) if isinstance(cmd, str) else cmd, shell=isinstance(cmd, str),
                           capture_output=True, text=True, timeout=timeout)
        # bluetoothctl colours its lines even into a pipe ("\x1b[1;30mDevice ..."),
        # which hid every connected device: no escape codes, ever
        return r.returncode, ANSI.sub("", r.stdout).strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def spawn(cmd):
    """Starts a command and returns at once (pickers, the power menu)."""
    subprocess.Popen(expand(cmd), shell=True, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def have(tool):
    return shutil.which(expand(tool).split()[0]) is not None


# ------------------------------------------------------------------ tiles
class Tile:
    """A toggle. status() returns (on, subtitle); on is True/False, or None
    for a tile that only does something (no on/off state)."""
    key = title = icon = ""
    # A line drawing instead of the glyph: SVG markup in currentColor, drawn
    # in the icon's colour like a glyph (faint when off, filled when on).
    icon_svg = None
    color = "mauve"
    shows_state = True          # writes "On" / "Off" at its right
    # Levels a tile can be on at (e.g. Jyoti: Akhaṇḍa, Nandādīpa): a list of
    # {"name", "when", "set"}; empty for a plain on/off tile. `level` is the
    # one status() last found, or None.
    levels = ()
    level = None

    def __init__(self, conf=None):
        self.conf = conf or {}
        self.open_cmd = self.conf.get("open")

    def available(self):
        return True

    def status(self):
        return None, ""

    def toggle(self, on):
        pass


class CommandTile(Tile):
    """A tile driven by your own commands (config.toml):
      status   prints the state; on when its output matches on_when (regex)
      toggle   one command for both directions, or on / off for each
      subtitle_on / subtitle_off   what the tile says under its title
      levels   while on, the levels it can be at, each a table:
               name (shown), when (regex on the status output: this level
               is current), set (the command that switches to it). The
               tile's subtitle then names the current level, and a row of
               the levels shows under the tiles to pick one.
    A tile with only `run` is an action (e.g. fetch a new wallpaper)."""

    def __init__(self, key, conf, defaults):
        super().__init__(conf)
        self.key = key
        self.title = conf.get("title", defaults.get("title", key))
        self.icon = conf.get("icon", defaults.get("icon", ""))
        svg = conf.get("icon_svg")   # a path to an SVG, in config.toml
        if svg:
            try:
                with open(os.path.expanduser(svg)) as f:
                    self.icon_svg = f.read()
            except OSError:
                self.icon_svg = None
        else:
            self.icon_svg = defaults.get("icon_svg")
        self.color = conf.get("color", defaults.get("color", "mauve"))
        # A level needs all three keys; one missing one is left out (never a crash).
        self.levels = [lv for lv in conf.get("levels", ())
                       if isinstance(lv, dict) and all(lv.get(k) for k in ("name", "when", "set"))]

    def available(self):
        cmds = [self.conf.get(k) for k in ("status", "toggle", "on", "off", "run") if self.conf.get(k)]
        cmds += [lv["set"] for lv in self.levels]
        return bool(cmds) and all(have(c) for c in cmds)

    def status(self):
        if "run" in self.conf and "status" not in self.conf:
            return None, self.conf.get("subtitle", "")
        _, out = run(self.conf["status"])
        on = re.search(self.conf.get("on_when", r"^(on|yes|true|active|enabled|1)$"), out, re.M) is not None
        self.level = None
        if on:
            self.level = next((lv["name"] for lv in self.levels if re.search(lv["when"], out, re.M)), None)
            if self.level:
                return on, self.level
        return on, self.conf.get("subtitle_on" if on else "subtitle_off", "on" if on else "off")

    def set_level(self, name):
        lv = next((lv for lv in self.levels if lv["name"] == name), None)
        if lv is not None:
            run(lv["set"], timeout=15)

    def toggle(self, on):
        if "run" in self.conf and "status" not in self.conf:
            spawn(self.conf["run"])
        elif "toggle" in self.conf:
            run(self.conf["toggle"], timeout=15)
        else:
            run(self.conf["on" if on else "off"], timeout=15)


class Wifi(Tile):
    key, title, icon, color = "wifi", "Wi‑Fi", "\U000f05a9", "sky"

    def available(self):
        return have("nmcli") and "wifi" in run("nmcli -t -f TYPE device")[1].split()

    # `--rescan no`: the cached scan; a fresh one takes seconds.
    def status(self):
        on = run("nmcli radio wifi")[1] == "enabled"
        if not on:
            return False, "Off"
        ssid = next((l.split(":", 1)[1] for l in run("nmcli -t -f ACTIVE,SSID device wifi list --rescan no")[1].splitlines()
                     if l.startswith("yes:")), "")
        if ssid:
            return True, ssid
        wired = "ethernet:connected" in run("nmcli -t -f TYPE,STATE device")[1]
        return True, "On · ethernet in use" if wired else "On · not connected"

    def toggle(self, on):
        run(["nmcli", "radio", "wifi", "on" if on else "off"])


class Bluetooth(Tile):
    key, title, icon, color = "bluetooth", "Bluetooth", "\U000f00af", "blue"

    def available(self):
        return have("bluetoothctl") and "Controller" in run("bluetoothctl show")[1]

    def status(self):
        on = "Powered: yes" in run("bluetoothctl show")[1]
        if not on:
            return False, "Off"
        devs = [l.split(" ", 2)[1:] for l in run("bluetoothctl devices Connected")[1].splitlines()
                if l.startswith("Device ") and l.count(" ") >= 2]
        if not devs:
            return True, "On · nothing connected"
        mac, name = devs[0]
        # The first device's battery, when it reports one ("Battery Percentage: 0x4e (78)").
        m = re.search(r"Battery Percentage:.*\((\d+)\)", run(["bluetoothctl", "info", mac])[1])
        sub = f"{name} · {m.group(1)}%" if m else name
        return True, sub + (f" +{len(devs) - 1}" if len(devs) > 1 else "")

    def toggle(self, on):
        run(["bluetoothctl", "power", "on" if on else "off"], timeout=8)


class Hotspot(Tile):
    """Through vayu-hotspot (Vayu's hotspot command) or a command of yours
    with the same `status --json` / `on` / `off` interface."""
    key, title, icon, color = "hotspot", "Hotspot", "\U000f0003", "teal"

    def __init__(self, conf=None):
        super().__init__(conf)
        self.cmd = expand(self.conf.get("command", "vayu-hotspot"))

    def available(self):
        return have(self.cmd) or os.access(self.cmd, os.X_OK)

    def status(self):
        rc, out = run([self.cmd, "status", "--json"])
        try:
            st = json.loads(out) if rc == 0 else None
        except ValueError:
            st = None
        if not st:
            return False, "unavailable"
        if st["on"]:
            n = st["client_count"]
            return True, f"{st['ssid']} · {n} connected"
        return False, "Off"

    def toggle(self, on):
        run([self.cmd, "on" if on else "off"], timeout=25)


class DoNotDisturb(Tile):
    key, title, icon, color = "dnd", "Do not disturb", "\U000f009b", "red"

    def available(self):
        return have("makoctl")

    def status(self):
        on = "do-not-disturb" in run("makoctl mode")[1].split()
        return on, "notifications held" if on else "off"

    def toggle(self, on):
        run(["makoctl", "mode", "-a" if on else "-r", "do-not-disturb"])


class DarkTheme(Tile):
    key, title, icon, color = "theme", "Dark theme", "\U000f0594", "mauve"
    schema = ["org.gnome.desktop.interface", "color-scheme"]

    def available(self):
        return have("gsettings")

    def status(self):
        on = "dark" in run(["gsettings", "get", *self.schema])[1]
        # "catppuccin-mocha-mauve-standard+default" -> "Catppuccin"
        theme = run(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"])[1].strip("'")
        theme = re.split(r"[-_+ ]", theme)[0].capitalize()
        return on, theme or ("Dark" if on else "Light")

    def toggle(self, on):
        run(["gsettings", "set", *self.schema, "prefer-dark" if on else "default"])


class PowerProfile(Tile):
    """Cycles power-saver -> balanced -> performance (those this machine
    offers: performance needs CPU support). Its subtitle names the profile,
    so it writes no On/Off."""
    key, title, icon, color = "power-profile", "Power", "\U000f0241", "green"
    shows_state = False

    def available(self):
        return have("powerprofilesctl") and run("powerprofilesctl get")[0] == 0

    def profiles(self):
        found = re.findall(r"^\s*\*?\s*([a-z-]+):\s*$", run("powerprofilesctl list")[1], re.M)
        order = ["power-saver", "balanced", "performance"]
        return [p for p in order if p in found] or order[:2]

    def status(self):
        p = run("powerprofilesctl get")[1]
        return p != "balanced", p.replace("-", " ").capitalize()

    def toggle(self, on):
        ps, cur = self.profiles(), run("powerprofilesctl get")[1]
        nxt = ps[(ps.index(cur) + 1) % len(ps)] if cur in ps else ps[0]
        run(["powerprofilesctl", "set", nxt])


JYOTI = {
    "title": "Jyoti", "icon": "\U000f0238", "color": "peach",
    # ekatva's flame (apps/mobile/src/ui/jyoti-art.ts), in one colour with its
    # heart cut out, painted in the tile's colour like a glyph. A vector, so
    # it's sharp at the 18 px it's shown at.
    "icon_svg": ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><title>Jyoti</title><path d="M100 190C70 190 44 172 42 142C40 120 50 106 58 92C62 86 60 80 56 72C64 80 72'
                 ' 92 72 104C72 84 80 68 86 52C92 38 92 24 86 12C108 26 122 46 122 66C122 76 120 84 116'
                 ' 90C128 84 140 76 148 60C152 80 160 96 160 120C160 160 132 190 100 190Z M100 182C84 182'
                 ' 74 170 74 154C74 138 86 126 98 112C100 124 108 128 114 134C122 142 126 150 126 158C126'
                 ' 172 114 182 100 182Z" fill="currentColor" fill-rule="evenodd"/></svg>'),
}
BUILTIN = {t.key: t for t in (Wifi, Bluetooth, Hotspot, DoNotDisturb, DarkTheme, PowerProfile)}
# Defaults for tiles that only exist through your commands.
COMMAND_DEFAULTS = {
    # Jyoti (ज्योति, the flame): the laptop stays awake. Its icon is ekatva's
    # flame. "jagaran" and "caffeine" are its
    # names in configs from before.
    "jyoti": JYOTI,
    "jagaran": JYOTI,
    "caffeine": JYOTI,
    "wallpaper": {"title": "New wallpaper", "icon": "\U000f02e9", "color": "yellow"},
}


def make_tile(key, conf):
    """A built-in tile, unless config.toml gives it commands: then those
    drive it, keeping the built-in's title, icon and color."""
    if key in BUILTIN and not any(k in conf for k in ("status", "toggle", "on", "off", "run")):
        return BUILTIN[key](conf)
    b = BUILTIN.get(key)
    defaults = {"title": b.title, "icon": b.icon, "color": b.color} if b else COMMAND_DEFAULTS.get(key, {})
    return CommandTile(key, conf, defaults)


# ---------------------------------------------------------------- sliders
class Volume:
    icon, icon_muted = "\U000f057e", "\U000f0581"

    def available(self):
        return have("wpctl") and run("wpctl get-volume @DEFAULT_AUDIO_SINK@")[0] == 0

    def get(self):
        out = run("wpctl get-volume @DEFAULT_AUDIO_SINK@")[1]
        m = re.search(r"([\d.]+)", out)
        return round(float(m.group(1)) * 100) if m else 0, "MUTED" in out

    def set(self, pct):
        run(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{pct / 100:.2f}"])

    def toggle_mute(self):
        run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])

    def device(self):
        """The output's name ("WH-1000XM5", "Built-in Audio Analog Stereo")."""
        out = run("wpctl inspect @DEFAULT_AUDIO_SINK@")[1]
        m = re.search(r'node\.description = "([^"]+)"', out) or re.search(r'node\.nick = "([^"]+)"', out)
        return m.group(1) if m else ""


class Brightness:
    icon = "\U000f00e0"

    def available(self):
        return have("brightnessctl") and bool(glob.glob("/sys/class/backlight/*"))

    def get(self):
        out = run("brightnessctl -m -c backlight")[1].split(",")
        return (int(out[3].rstrip("%")) if len(out) > 3 else 0), False

    def set(self, pct):
        run(["brightnessctl", "-q", "-c", "backlight", "set", f"{max(pct, 1)}%"])


# ----------------------------------------------------------------- header
def battery():
    """(percent, charging, time left text) of the first battery, or None.
    Handles both kinds of driver: energy_* (µWh) with power_now, or
    charge_* (µAh) with current_now."""
    def read(p, cast=str):
        try:
            return cast(open(p).read().strip())
        except (OSError, ValueError):
            return None
    for d in sorted(glob.glob("/sys/class/power_supply/*")):
        if read(f"{d}/type") != "Battery":
            continue
        pct, status = read(f"{d}/capacity", int), read(f"{d}/status") or ""
        if pct is None:
            continue
        kind = "energy" if read(f"{d}/energy_now", int) is not None else "charge"
        now, full = read(f"{d}/{kind}_now", int), read(f"{d}/{kind}_full", int)
        rate = read(f"{d}/power_now" if kind == "energy" else f"{d}/current_now", int)
        left = ""
        if rate and now is not None and full and status in ("Charging", "Discharging"):
            h = (full - now) / abs(rate) if status == "Charging" else now / abs(rate)
            if 0 < h < 48:
                left = f"{int(h)} h {int(h % 1 * 60):02d}"
        return pct, status in ("Charging", "Full"), left
    return None


def uptime():
    try:
        s = float(open("/proc/uptime").read().split()[0])
    except OSError:
        return ""
    d, h, m = int(s // 86400), int(s % 86400 // 3600), int(s % 3600 // 60)
    return f"up {d} d {h} h" if d else f"up {h} h {m} min" if h else f"up {m} min"


def user_name():
    import pwd
    p = pwd.getpwuid(os.getuid())
    full = p.pw_gecos.split(",")[0].strip()
    return (full.split()[0] if full else p.pw_name).capitalize()


def greeting():
    h = time.localtime().tm_hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


# ------------------------------------------------------ the bento's data
# (2026-11-26) The Wi-Fi square's signal and traffic, the Bluetooth square's
# devices, the power modes and the wallpaper picture.

def wifi_device():
    for line in run("nmcli -t -f DEVICE,TYPE device")[1].splitlines():
        dev, _, kind = line.partition(":")
        if kind == "wifi":
            return dev
    return None


def wifi_signal(dev):
    """(percent or None, dBm or None) of the network you're on."""
    pct = None
    for line in run("nmcli -t -f IN-USE,SIGNAL device wifi list --rescan no")[1].splitlines():
        if line.startswith("*:"):
            try:
                pct = int(line.split(":")[1])
            except ValueError:
                pass
    dbm = None
    if dev and have("iw"):
        m = re.search(r"signal:\s*(-?\d+)\s*dBm", run(["iw", "dev", dev, "link"])[1])
        dbm = int(m.group(1)) if m else None
    return pct, dbm


def signal_word(pct):
    if pct is None:
        return 0, ""
    if pct >= 75:
        return 4, "Excellent"
    if pct >= 55:
        return 3, "Strong"
    if pct >= 35:
        return 2, "Fair"
    return 1, "Weak"


class Traffic:
    """Download and upload speed, one sample every `step` seconds for the
    last minute, read from the device's byte counters (no tool, nothing on
    the network). Kept in memory by the resident daemon, so the panel opens
    on a full minute."""

    def __init__(self, step=2, keep=30):
        self.step, self.keep = step, keep
        self.down, self.up = [], []
        self.last = None
        self.dev = None

    def counters(self):
        try:
            base = f"/sys/class/net/{self.dev}/statistics/"
            with open(base + "rx_bytes") as rx, open(base + "tx_bytes") as tx:
                return int(rx.read()), int(tx.read()), time.monotonic()
        except (OSError, ValueError, TypeError):
            return None

    def sample(self):
        now = self.counters()
        if now is None:
            self.last = None
            return
        if self.last is not None:
            dt = max(0.5, now[2] - self.last[2])
            self.down.append(max(0, (now[0] - self.last[0]) / dt))
            self.up.append(max(0, (now[1] - self.last[1]) / dt))
            del self.down[:-self.keep], self.up[:-self.keep]
        self.last = now


def rate(bps):
    """Bytes a second as (number, unit): "12.4", "MB/s"."""
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.1f}", "MB/s"
    if bps >= 1000:
        return f"{bps / 1000:.0f}", "kB/s"
    return f"{bps:.0f}", "B/s"


def bt_devices():
    """Connected Bluetooth devices: [{mac, name, icon, battery}], in
    bluetoothctl's order."""
    out = []
    for line in run("bluetoothctl devices Connected")[1].splitlines():
        if not line.startswith("Device ") or line.count(" ") < 2:
            continue
        _, mac, name = line.split(" ", 2)
        info = run(["bluetoothctl", "info", mac])[1]
        m = re.search(r"Battery Percentage:.*\((\d+)\)", info)
        icon = re.search(r"Icon:\s*(\S+)", info)
        out.append({"mac": mac.upper(), "name": name, "icon": icon.group(1) if icon else "",
                    "battery": int(m.group(1)) if m else None})
    return out


KINDS = {"audio-headset": "Headset", "audio-headphones": "Headphones", "audio-card": "Speaker",
         "input-mouse": "Mouse", "input-keyboard": "Keyboard", "input-gaming": "Controller",
         "phone": "Phone", "computer": "Computer"}


def pick_device(devs, recent):
    """The one the square shows: a device at 20% or less (the lowest first),
    else the one connected most recently (`recent`: mac -> when), else the
    first. Each dev may carry "low": its lowest battery."""
    low = [d for d in devs if d.get("low") is not None and d["low"] <= 20]
    if low:
        return min(low, key=lambda d: d["low"])
    if not devs:
        return None
    return max(devs, key=lambda d: (recent.get(d["mac"], 0), -devs.index(d)))


PROFILES = [("power-saver", "Saver", "\U000f032a"), ("balanced", "Balanced", "\U000f05d1"),
            ("performance", "Performance", "\U000f0241")]


def power_profiles():
    """[(id, name, glyph)] this machine offers, and the current id."""
    if not have("powerprofilesctl"):
        return [], None
    found = re.findall(r"^\s*\*?\s*([a-z-]+):\s*$", run("powerprofilesctl list")[1], re.MULTILINE)
    cur = run("powerprofilesctl get")[1]
    return [p for p in PROFILES if p[0] in found], cur or None


def set_power_profile(pid):
    run(["powerprofilesctl", "set", pid])


def wallpaper_image(conf):
    """The picture on the desktop now: config `image`, else swaybg's -i."""
    path = conf.get("image")
    if path:
        return os.path.realpath(expand(path))
    out = run("pgrep -a swaybg")[1]
    m = re.search(r"-i\s+(\S+)", out)
    return os.path.realpath(m.group(1)) if m else None


def wallpaper_name(path):
    """ "wallpaper-20261126-RFHilo.jpg" -> "RF Hilo"; "Trail_Cedars.png" -> "Trail Cedars"."""
    if not path:
        return ""
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = re.sub(r"^wallpaper-\d{8}-", "", stem)
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", stem)
    return stem.strip()
