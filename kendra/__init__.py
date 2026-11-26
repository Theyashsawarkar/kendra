"""kendra (केन्द्र, "centre"): quick settings for Vyom.

Toggles, sliders, battery and session buttons in a panel under the bar's
top-right corner. Opens with the last known state, then every tile
refreshes in a background thread, so slow tools never hold it up.
"""
import logging
import time

from gi.repository import GLib, Gtk, Pango

from vyom import Hint, ui
from vyom import Plugin as Base

from vyom import util

from . import bento, system, vim

log = logging.getLogger("vyom.kendra")

# KEYBINDS (generated from kendra/vim.py by scripts/keybinds.py; don't edit by hand)
# keybind: Vyom/quick settings:normal | h | Move left in the tiles (on a slider: lower it by 5)
# keybind: Vyom/quick settings:normal | l | Move right in the tiles (on a slider: raise it by 5)
# keybind: Vyom/quick settings:normal | j | Move down (from the tiles into the sliders)
# keybind: Vyom/quick settings:normal | k | Move up
# keybind: Vyom/quick settings:normal | g g | Jump to the first tile
# keybind: Vyom/quick settings:normal | G | Jump to the last control (the bottom slider)
# keybind: Vyom/quick settings:normal | 0 | Set the focused slider to its minimum
# keybind: Vyom/quick settings:normal | $ | Set the focused slider to its maximum
# keybind: Vyom/quick settings:normal | Enter | Toggle the focused setting (on a slider: mute it)
# keybind: Vyom/quick settings:normal | o | Open the focused tile's details (Wi-Fi in tarang, Bluetooth in setu)
# keybind: Vyom/quick settings:normal | m | Toggle mute on the sound output
# keybind: Vyom/quick settings leader:normal | Space l | Lock the screen
# keybind: Vyom/quick settings leader:normal | Space p | Open the power menu
# keybind: Vyom/quick settings leader:normal | Space g w | Open the Wi-Fi panel (tarang)
# keybind: Vyom/quick settings leader:normal | Space g b | Open the Bluetooth panel (setu)
# keybind: Vyom/quick settings leader:normal | Space g h | Open the hotspot (tarang's Hotspot tab)
# keybind: Vyom/quick settings leader:normal | Space g p | Open the power menu (vishram)
# keybind: Vyom/quick settings leader:normal | Space g a | Open the battery panel (urja)
# keybind: Vyom/quick settings leader:normal | Space r | Reload every tile and slider
# keybind: Vyom/quick settings | Shift+Enter | Open the focused setting's details (same as o)
# END KEYBINDS

DEFAULT_TILES = ["wifi", "bluetooth", "hotspot", "notifications", "dnd", "jyoti", "theme", "wallpaper", "power-profile"]
# A tile's details in another Vyom tool, when it's installed and the tile has no `open` command.
DETAILS = {"wifi": ("tarang", []), "bluetooth": ("setu", []), "hotspot": ("tarang", ["hotspot"]),
           "power-profile": ("urja", [])}
# Where each part sits in the bento (column, row, width, height), 4 columns.
WIFI, VOLUME, BRIGHT = (0, 0, 2, 3), (2, 0, 1, 3), (3, 0, 1, 3)
BT = (2, 3, 2, 3)
BOTTOM = 6
# circles in the bottom row, before the wallpaper (dnd only when there's no
# three-way notifications tile)
CIRCLES = ("hotspot", "ekatva", "dnd", "theme")
BELL, BELL_X, BELL_OFF = "\U000f009a", "\U000f00a0", "\U000f009b"
FLAME = "\U000f0238"
OFF = "\U000f073a"


def ago(t):
    s = max(0, time.time() - t)
    if s < 90:
        return "just now"
    for size, unit in ((86400, "d"), (3600, "h"), (60, "min")):
        if s >= size:
            return f"{int(s // size)} {unit}"
    return "just now"


def setu_mods():
    """setu's Bluetooth helpers when setu is installed (Vyom puts every
    plugin on the path): the buds' own batteries. None without it."""
    try:
        from setu import bluez as sb, fastpair  # noqa: PLC0415
        return sb, fastpair
    except Exception:     # noqa: BLE001  (not installed, or an older setu)
        return None


class Plugin(Base):
    name, title, icon, color = "kendra", "Quick settings", "\U000f0493", "mauve"
    layout = "card"
    width = 228
    anchor = ("top", "right")
    modal = True                # vim keys (Vyom 0.7): always NORMAL; h / j / k / l move, Enter toggles
    start_mode = "normal"
    card_cursor = False         # kendra moves by the grid itself (h / l never jump rows)
    key_groups = vim.GROUPS
    hints = [Hint("Enter", "toggle"), Hint("o", "open")]   # the rest: ? lists every key

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.margins = {"top": int(self.conf.get("margin_top", 6)), "right": int(self.conf.get("margin_right", 8))}
        self.card = None
        self.parts, self.sliders, self.focusables = [], [], []
        self.wifi = self.bt = self.jyoti = self.power = self.wall = None
        self.traffic = system.Traffic()
        self.first_seen = {}
        self.fp = None
        self.sampling = None

    # ------------------------------------------------------------ building
    def build_card(self):
        if self.card is None:
            self.card = self._build()
        self.refresh_all()
        self.start_listening()
        if self.focusables:
            GLib.idle_add(self.first_focus)
        return self.card

    def first_focus(self):
        self.focusables[0].grab_focus()
        # Where you are, drawn by us: a layer-shell panel isn't always an
        # "active" window, so GTK's :focus can't be relied on.
        if self.panel is not None and getattr(self, "watched_panel", None) is not self.panel:
            self.watched_panel = self.panel
            self.panel.connect("notify::focus-widget", lambda *_: self.mark_focus())
        self.mark_focus()
        return False

    def mark_focus(self):
        focus = self.panel.get_focus() if self.panel is not None else None
        for w in self.focusables + list(getattr(self, "session_buttons", [])):
            # a slider's rim goes on its capsule, not on the bare scale
            target = w.get_parent() if isinstance(w.get_parent(), bento.Tall) else w
            (target.add_css_class if w is focus else target.remove_css_class)("sel")

    def tile(self, key):
        keys = self.conf.get("tiles", DEFAULT_TILES)
        if key not in keys:
            return None
        t = system.make_tile(key, self.conf.get("tile", {}).get(key, {}))
        return t if t.available() else None

    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.add_css_class("qs")
        root.append(self._header())
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True, row_homogeneous=True)
        grid.add_css_class("k-bento")
        def place(w, pos):
            grid.attach(w, *pos)
        keys = self.conf.get("tiles", DEFAULT_TILES)
        t = self.tile("wifi")
        if t:
            if self.sampling is None:
                self.traffic.dev = system.wifi_device()
                self.traffic.sample()
                self.sampling = GLib.timeout_add_seconds(self.traffic.step, self.sample)
            self.wifi = bento.WifiSquare(self, t, self.traffic)
            place(self.wifi, WIFI)
            self.parts.append(self.wifi)
            self.focusables.append(self.wifi.toggle)
        srcs = [(src, css, name) for src, css, name in ((system.Volume(), "volume", "Volume"),
                                                         (system.Brightness(), "brightness", "Brightness"))
                if src.available()]
        if self.wifi is not None and len(srcs) < 2:
            # one slider (no sound card, or no backlight): Wi-Fi takes the room
            grid.remove(self.wifi)
            place(self.wifi, (0, 0, 4 - len(srcs), 3))
        for (src, css, name), pos in zip(srcs, (VOLUME, BRIGHT)[2 - len(srcs):]):
            if True:
                tall = bento.Tall(self, src, css, name)
                place(tall, pos)
                self.sliders.append(tall)
                self.focusables.append(tall.scale)
        pills = []      # the left column's pills under Wi-Fi; they share its height
        t = self.tile("jyoti") or self.tile("jagaran") or self.tile("caffeine")
        if t:
            colors = ["sky", "peach", "yellow", "green"]
            opts = [("off", "Off", OFF, "gray")] + [(lv["name"], lv["name"], FLAME, colors[i % 4])
                                                     for i, lv in enumerate(t.levels)]
            if not t.levels:
                opts.append(("on", "On", FLAME, "peach"))
            self.jyoti = bento.Segments(self, t.title, opts, lambda k, t=t: self.pick_jyoti(t, k))
            self.jyoti.tile = t
            pills.append(self.jyoti)
            self.focusables += list(self.jyoti.buttons.values())
        t = self.tile("bluetooth")
        if t:
            self.bt = bento.BtSquare(self, t)
            place(self.bt, BT)
            self.parts.append(self.bt)
            self.focusables.append(self.bt.toggle)
        if "power-profile" in keys:
            profiles, _cur = system.power_profiles()
            if profiles:
                opts = [(pid, name, glyph, "green") for pid, name, glyph in profiles]
                self.power = bento.Segments(self, "Power mode", opts, self.pick_power,
                                            open_fn=lambda: self.open_details("power-profile", None))
                pills.append(self.power)
                self.focusables += list(self.power.buttons.values())
        # Notifications: a tile with levels (normal / silent / dnd) is a
        # three-way pill; without one, a plain dnd circle in the bottom row.
        t = self.tile("notifications")
        self.notify = None
        if t and t.levels:
            looks = {0: (BELL, "white"), 1: (BELL_X, "yellow"), 2: (BELL_OFF, "red")}
            opts = []
            for i, lv in enumerate(t.levels):
                icon, color = looks.get(i, (BELL, "gray"))
                opts.append((lv["name"], lv["name"], lv.get("icon", icon), lv.get("color", color)))
            self.notify = bento.Segments(self, t.title, opts, lambda k, t=t: self.pick_level(t, k, self.refresh_notify),
                                         words={lv["name"]: lv.get("about", "") for lv in t.levels})
            self.notify.tile = t
            pills.append(self.notify)
            self.focusables += list(self.notify.buttons.values())
        # Whatever pills there are fill the column under Wi-Fi evenly (no
        # hole for one you haven't set up); with none, Bluetooth takes the row.
        if pills:
            order = [self.jyoti, self.notify, self.power]   # the same order whichever are set up
            pills = [p for p in order if p in pills]
            # three row-high slots: one pill sits in the middle, two at the
            # top and bottom, three fill them; never a stretched pill
            slots = {1: [None, 0, None], 2: [0, None, 1], 3: [0, 1, 2]}[min(len(pills), 3)]
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, homogeneous=True)
            for k in slots:
                col.append(Gtk.Box() if k is None else pills[k])
            place(col, (0, 3, 2, 3))
        elif self.bt is not None:
            grid.remove(self.bt)
            place(self.bt, (0, 3, 4, 3))
        known = {"wifi", "bluetooth", "jyoti", "jagaran", "caffeine", "power-profile", "wallpaper",
                 "notifications", *CIRCLES}
        bottom = Gtk.Box(spacing=8)
        bottom.add_css_class("k-bottom")
        for k in [*CIRCLES, *[k for k in keys if k not in known]]:
            if k == "dnd" and self.notify is not None:
                continue
            t = self.tile(k)
            if t:
                c = bento.Circle(self, t, size=40)
                bottom.append(c)
                self.parts.append(c)
                self.focusables.append(c)
        t = self.tile("wallpaper")
        if t:
            self.wall = bento.WallpaperPill(self, t)
            bottom.append(self.wall)
            self.focusables.append(self.wall)
        if bottom.get_first_child() is not None:
            grid.attach(bottom, 0, BOTTOM, 4, 1)
        root.append(grid)
        self.said = ui.label("", "k-say", xalign=0, ellipsize=Pango.EllipsizeMode.END, use_markup=True)
        root.append(self.said)
        # The keys are in Vyom's footer (a modal card has one).
        return root

    def say(self, markup):
        if getattr(self, "said", None) is not None:
            self.said.set_markup(markup)

    def sample(self):
        self.traffic.sample()
        if self.wifi is not None and self.panel is not None and self.panel.get_visible():
            self.wifi.update_speed()
        return True

    def opened(self, args):
        """Vyom calls this before the card is built; build_card starts the
        listening once the Bluetooth square exists."""
        self.start_listening()

    def start_listening(self):
        mods = setu_mods()
        if mods and self.bt is not None:
            if self.fp is None:
                self.fp = mods[1].Scanner()
            self.background(self.fp.start)
            # The buds announce left / right / case every few seconds: look
            # again while the panel is open, so the square fills in by itself.
            if getattr(self, "bt_watch", None) is None:
                self.bt_watch = GLib.timeout_add_seconds(3, self.bt_tick)

    def bt_tick(self):
        if self.panel is None or not self.panel.get_visible():
            self.bt_watch = None
            return False
        self.refresh_bt()
        return True

    def closed(self):
        if getattr(self, "bt_watch", None) is not None:
            GLib.source_remove(self.bt_watch)
            self.bt_watch = None
        if self.fp is not None:
            self.background(self.fp.stop)

    # ------------------------------------------------------------ actions
    def open_details(self, key, open_cmd):
        if open_cmd:
            self.close()
            system.spawn(open_cmd)
            return True
        internal = DETAILS.get(key)
        if internal and internal[0] in getattr(self.vyom, "plugins", {}):
            name, args = internal
            GLib.idle_add(lambda: (self.vyom.open(name, list(args)), False)[1])
            return True
        self.set_status("no details for this one", "bad")
        return False

    def pick_jyoti(self, t, key):
        def work():
            on, _ = t.status()
            if key == "off":
                if on:
                    t.toggle(False)
            elif key == "on":
                if not on:
                    t.toggle(True)
            else:
                if not on and not t.levels:
                    t.toggle(True)
                t.set_level(key)
        self.background(work, then=lambda _r: self.refresh_jyoti())

    def pick_level(self, t, name, then):
        self.background(lambda: t.set_level(name), then=lambda _r: then())

    def refresh_notify(self):
        if self.notify is None:
            return
        t = self.notify.tile
        self.background(t.status, then=lambda r: self.notify.show(t.level) if isinstance(r, tuple) else None)

    def pick_power(self, pid):
        self.background(lambda: system.set_power_profile(pid), then=lambda _r: self.refresh_power())

    # ------------------------------------------------------------ reading
    def refresh_jyoti(self):
        if self.jyoti is None:
            return
        t = self.jyoti.tile

        def show(r):
            if not isinstance(r, tuple):
                return
            on, _sub = r
            self.jyoti.show("off" if not on else (t.level or ("on" if "on" in self.jyoti.buttons else None)))
        self.background(t.status, then=show)

    def refresh_power(self):
        if self.power is None:
            return
        self.background(system.power_profiles, then=lambda r: self.power.show(r[1]) if isinstance(r, tuple) else None)

    def refresh_wifi(self):
        w = self.wifi

        def get():
            on, sub = w.tile.status()
            pct, dbm = system.wifi_signal(self.traffic.dev) if on else (None, None)
            return on, sub, pct, dbm
        self.background(get, then=lambda r: w.show_state(*r) if isinstance(r, tuple) else None)

    def refresh_bt(self):
        b = self.bt

        def get():
            on, _sub = b.tile.status()
            if not on:
                return on, [], None
            devs = system.bt_devices()
            mods = setu_mods()
            ubats = mods[0].upower_batteries() if mods else {}
            readings = self.fp.read() if (self.fp is not None and mods) else {}
            memo = util.load_state("setu-case", {})
            recent = dict(util.load_state("setu-last-connected", {}))
            now = time.time()
            for d in devs:
                self.first_seen.setdefault(d["mac"], now)
                recent[d["mac"]] = max(recent.get(d["mac"], 0), self.first_seen[d["mac"]])
                parts = {}
                r = readings.get(d["name"])
                if r:
                    for k, p in r["parts"].items():
                        parts[k.capitalize()] = {"level": p["level"], "charging": p["charging"]}
                elif d["mac"] in ubats:
                    for lab, pct in ubats[d["mac"]]:
                        key = lab.split()[0].capitalize()
                        parts[key] = {"level": pct, "charging": False}
                case = parts.get("Case")
                m = memo.get(d["mac"])
                if (case is None or case.get("level") is None) and m and (parts.get("Left") or parts.get("Right")):
                    parts["Case"] = {"level": m["level"], "charging": False,
                                     "age": ago(m["at"])}
                d["parts"] = parts
                levels = [p["level"] for k, p in parts.items() if k != "Case" and p.get("level") is not None]
                d["low"] = min(levels) if levels else d["battery"]
            for mac in list(self.first_seen):
                if mac not in {d["mac"] for d in devs}:
                    del self.first_seen[mac]
            pick = system.pick_device(devs, recent)
            if pick is not None and pick.get("parts") != getattr(self, "last_parts", None):
                self.last_parts = pick.get("parts")
                log.debug("kendra: bluetooth %s %s", pick["name"], pick.get("parts") or f"{pick.get('battery')}%")
            return on, devs, pick
        self.background(get, then=lambda r: b.show_state(*r) if isinstance(r, tuple) else None)

    def _header(self):
        box = Gtk.Box(spacing=12)
        box.add_css_class("qs-header")
        self.ring = bento.BatteryRing(system.user_name()[:1])
        box.append(self.ring)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER, hexpand=True)
        self.hello = ui.label("", "qs-hello", xalign=0)
        self.meta = ui.label("", "k-meta", xalign=0, ellipsize=Pango.EllipsizeMode.END)
        text.append(self.hello)
        text.append(self.meta)
        box.append(text)
        # Lock and power, set apart from the tiles; power in red. Space l and Space p do the same.
        self.session, self.session_buttons = {}, []
        for icon, key, tip, css in (("\U000f033e", "lock", "Lock the screen (Space l)", "lock"),
                                    ("\U000f0425", "power", "Power menu (Space p)", "power")):
            cmd = self.conf.get(key, "loginctl lock-session" if key == "lock" else None)
            if not cmd or not system.have(cmd):
                if key == "power" and "vishram" in getattr(self.vyom, "plugins", {}):
                    cmd = None   # the power menu inside Vyom
                else:
                    continue
            b = Gtk.Button(label=icon, tooltip_text=tip, valign=Gtk.Align.CENTER)
            b.add_css_class("qs-round")
            b.add_css_class(css)
            b.connect("clicked", lambda _b, k=key: self.session_action(k))
            self.session[key] = cmd
            self.session_buttons.append(b)
            box.append(b)
        return box

    def session_action(self, key):
        if key not in self.session:
            return False
        cmd = self.session[key]
        if cmd:
            self.close()
            system.spawn(cmd)
        else:
            GLib.idle_add(lambda: (self.vyom.open("vishram", []), False)[1])
        return True

    def refresh_all(self):
        self.hello.set_label(f"{system.greeting()}, {system.user_name()}")
        bat = system.battery()
        bits = []
        if bat:
            pct, charging, left = bat
            self.ring.set(pct, charging)
            bits.append(f"{pct}%" + (" charging" if charging else "") + (f" · {left} {'to full' if charging else 'left'}" if left else ""))
        else:
            self.ring.set(None, False)
        up = system.uptime()
        if up:
            bits.append(up)
        self.meta.set_label(" · ".join(bits))
        if self.wifi is not None:
            self.refresh_wifi()
        if self.bt is not None:
            self.refresh_bt()
        self.refresh_jyoti()
        self.refresh_notify()
        self.refresh_power()
        for p in self.parts:
            if isinstance(p, bento.Circle):
                p.refresh()
        for s in self.sliders:
            s.refresh()
        if self.wall is not None:
            self.wall.refresh()
        if self.wifi is not None:
            GLib.idle_add(lambda: (self.say(self.wifi.words()), False)[1])

    def focused_tile(self):
        """What o / Shift+Enter opens: the focused circle or square."""
        w = self.panel.get_focus() if self.panel is not None else None
        while w is not None:
            if isinstance(w, bento.Circle):
                return w
            if getattr(w, "owner", None) is not None:
                return w.owner
            if isinstance(w, bento.Segments) and w is self.power:
                return w
            w = w.get_parent()
        return None

    def key(self, name, row, mods):
        if name in ("Return", "KP_Enter") and "shift" in mods:
            t = self.focused_tile()
            return bool(t and t.open_details())
        return False

    # ------------------------------------------------------------ vim keys
    def keys(self, tab):
        return vim.keys(tab)

    def focused_slider(self):
        f = self.panel.get_focus() if self.panel is not None else None
        return next((s for s in self.sliders if f is s.scale), None)


    def v_move(self, n, way):
        s = self.focused_slider()
        if s is not None and way in ("left", "right"):
            v = s.scale.get_value() + (5 if way == "right" else -5) * n
            s.scale.set_value(max(0, min(100, v)))
            return
        if self.panel is None:
            return
        if self.panel.get_focus() is None and self.focusables:
            self.focusables[0].grab_focus()
            return
        d = {"left": Gtk.DirectionType.LEFT, "right": Gtk.DirectionType.RIGHT,
             "down": Gtk.DirectionType.DOWN, "up": Gtk.DirectionType.UP}[way]
        for _ in range(n):
            self.panel.child_focus(d)

    def v_top(self, _n, _a):
        if self.focusables:
            self.focusables[0].grab_focus()

    def v_bottom(self, _n, _a):
        last = self.focusables[-1:]
        if last:
            last[0].grab_focus()

    def v_ends(self, _n, which):
        s = self.focused_slider()
        if s is None:
            self.set_status("move to a slider first (j)", "bad")
            return
        s.scale.set_value(0 if which == "min" else 100)

    def v_enter(self, _n, _a):
        s = self.focused_slider()
        if s is not None:
            if hasattr(s.source, "toggle_mute"):
                s.toggle_mute()
            return
        f = self.panel.get_focus() if self.panel is not None else None
        if f is not None:
            f.activate()

    def v_details(self, _n, _a):
        t = self.focused_tile()
        if t is self.power and t is not None:
            self.open_details("power-profile", None)
        elif t is None or not t.open_details():
            self.set_status("this setting has no details", "bad")

    def v_mute(self, _n, _a):
        for s in self.sliders:
            if hasattr(s.source, "toggle_mute"):
                s.toggle_mute()
                return
        self.set_status("no sound output to mute", "bad")

    def v_lock(self, _n, _a):
        if not self.session_action("lock"):
            self.set_status("no lock command here", "bad")

    def v_power(self, _n, _a):
        if not self.session_action("power"):
            self.set_status("no power menu here", "bad")

    def v_goto(self, _n, arg):
        name, _, sub = arg.partition(":")
        if name not in getattr(self.vyom, "plugins", {}):
            self.set_status(f"{name} isn't installed", "bad")
            return
        GLib.idle_add(lambda: (self.vyom.open(name, [sub] if sub else []), False)[1])

    def v_refresh(self, _n, _a):
        self.refresh_all()
