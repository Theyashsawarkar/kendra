"""The tiles' facts from Vyom's live state (vyom.state, Vyom 0.9): what
NetworkManager, BlueZ, UPower, power-profiles-daemon, the sound server and
the backlight last said, kept current by their own signals. Reading it is
a look at memory, so the panel opens on the current state without running
a command. Each function turns a snapshot into what kendra's widgets take,
or returns None when there's nothing to go on (an older Vyom, the daemon
isn't running): then kendra asks the old way (system.py, in a thread)."""
import re

try:
    from vyom import live as state
except ImportError:      # Vyom before 0.9: no live state
    state = None

from . import system


def get(name):
    if state is None:
        return None
    try:
        return state.get(name)
    except Exception:    # noqa: BLE001  (never let a source take the panel down)
        return None


def net(dev, step, window):
    """{"rx": [...], "tx": [...], ...}: the last `window` seconds of the
    device's speeds in `step`-second bins, kept by Vyom since it started
    (Vyom 0.10's live.history), so the chart opens full. None with an older
    Vyom or without NetworkManager: then kendra samples while it shows."""
    if state is None or not hasattr(state, "history"):
        return None
    try:
        return state.history("net", dev=dev, step=step, window=window)
    except Exception:    # noqa: BLE001
        return None


def wifi(snap):
    """(on, subtitle, signal percent) like Wifi.status() and wifi_signal()."""
    if not snap or not snap.get("running") or not snap.get("device"):
        return None
    if not snap.get("enabled"):
        return False, "Off", None
    a = snap.get("active")
    if a and a.get("ssid"):
        return True, a["ssid"], a.get("strength")
    return True, "On · ethernet in use" if snap.get("wired") else "On · not connected", None


def bluetooth(snap):
    """(on, connected devices [{mac, name, icon, battery}]) like
    Bluetooth.status() and bt_devices()."""
    if not snap or not snap.get("running") or not snap.get("adapter"):
        return None
    if not snap["adapter"].get("powered"):
        return False, []
    devs = [{"mac": d["mac"], "name": d.get("alias") or d.get("name") or d["mac"], "icon": d.get("icon") or "",
             "battery": d.get("battery")} for d in snap.get("devices", []) if d.get("connected")]
    return True, devs


MAC = re.compile(r"([0-9A-Fa-f]{2}[:_]){5}[0-9A-Fa-f]{2}")


def upower_batteries(snap):
    """{MAC: [(label, percent)]} for devices UPower reports more than one
    battery for (earbuds left / right / case), like setu's
    bluez.upower_batteries() but from the live state."""
    if not snap or not snap.get("running"):
        return None
    found = {}
    for d in snap.get("devices", []):
        m = MAC.search(d.get("native_path") or "") or MAC.search(d.get("serial") or "")
        if not m or not d.get("present", True):
            continue
        mac = m.group(0).replace("_", ":").upper()
        found.setdefault(mac, []).append((d.get("type", ""), d.get("model", ""), int(d.get("percentage") or 0)))
    out = {}
    for mac, items in found.items():
        if len(items) < 2:
            continue
        kinds = [k for k, _, _ in items]
        out[mac] = [((k if kinds.count(k) == 1 else f"{k} {model}") or model or "Battery").strip().capitalize()
                    for k, model, _ in items]
        out[mac] = list(zip(out[mac], [p for _, _, p in items]))
    return out


def power(snap):
    """([(id, name, glyph)], current id) like system.power_profiles()."""
    if not snap or not snap.get("profiles"):
        return None
    return [p for p in system.PROFILES if p[0] in snap["profiles"]], snap.get("active") or None


def volume(snap):
    """((percent, muted), device name) like Volume.get() and .device()."""
    if not snap or snap.get("volume") is None:
        return None
    return (snap["volume"], bool(snap.get("muted"))), snap.get("device", "")


def brightness(snap):
    if not snap:
        return None
    return (snap["percent"], False), ""


# ------------------------------------------------------ your own tiles' state
# A tile from your commands can say where its state lives instead of a
# `status` command run on every opening ([plugin.kendra.tile.<key>] live):
#   "unit:<name>"   a systemd user unit's ActiveState ("active", "inactive"...)
#   "file:<path>"   a small file's text (a mode, a level)
#   "akashvani"     the notification mode, from akashvani in this process
#                   ("normal", "silent", "dnd")
#   "theme"         GNOME's colour scheme ("prefer-dark", "default"...)
# A list joins them, one per line, for on_when and the levels' `when`.

def track(spec):
    for item in [spec] if isinstance(spec, str) else spec or ():
        if isinstance(item, str) and item.startswith("unit:") and state is not None:
            state.track_unit(item[5:])


def akashvani_mode(vyom):
    p = getattr(vyom, "plugins", {}).get("akashvani")
    server = getattr(p, "server", None)
    if server is None or not getattr(server, "owned", True):
        return None
    modes = set(getattr(server, "modes", ()) or ())
    return "dnd" if server.dnd() else "silent" if "silent" in modes else "normal"


def text(spec, vyom, ask=False):
    """The tile's state as text, or None when part of it isn't known. ask:
    find out what isn't (systemctl, gsettings; a worker thread only), so
    on_when means the same either way."""
    out = []
    for item in [spec] if isinstance(spec, str) else spec or ():
        if not isinstance(item, str):
            return None
        if item.startswith("unit:"):
            units = get("units") or {}
            v = units.get(item[5:])
            if v is None and ask:
                v = system.run(["systemctl", "--user", "is-active", item[5:]])[1] or "inactive"
        elif item.startswith("file:"):
            try:
                with open(system.expand(item[5:])) as f:
                    v = f.read(4096).strip()
            except OSError:
                v = ""
        elif item == "akashvani":
            v = akashvani_mode(vyom)
            if v is None and ask:
                m = system.run(["akashvani", "mode"])[1].split()
                v = "dnd" if {"dnd", "do-not-disturb"} & set(m) else "silent" if "silent" in m else "normal"
        elif item == "theme":
            v = (get("theme") or {}).get("color_scheme")
            if v is None and ask:
                v = system.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])[1].strip("'")
        else:
            v = None
        if v is None:
            return None
        out.append(v)
    return "\n".join(out) if out else None


def theme():
    """(on, theme name) for the built-in dark-theme tile, or None."""
    t = get("theme")
    if not t:
        return None
    name = re.split(r"[-_+ ]", t.get("gtk_theme") or "")[0].capitalize()
    return t["dark"], name or ("Dark" if t["dark"] else "Light")


def hotspot():
    """(on, ssid) from NetworkManager, or None."""
    w = get("wifi")
    if not w or not w.get("running") or "hotspot" not in w:
        return None
    h = w["hotspot"]
    return bool(h.get("on")), h.get("ssid", "")
