"""kendra (केन्द्र, "centre"): quick settings for Vyom.

Toggles, sliders, battery and session buttons in a panel under the bar's
top-right corner. Opens with the last known state, then every tile
refreshes in a background thread, so slow tools never hold it up.
"""
from gi.repository import GLib, Gtk, Pango

from vyom import Plugin as Base
from vyom import ui

from . import system

# keybind: Vyom/quick settings | Arrows | Move between the toggles and sliders
# keybind: Vyom/quick settings | Enter / Space | Toggle the focused setting
# keybind: Vyom/quick settings | Right | Open the focused tile's details (Wi-Fi in tarang, Bluetooth in setu)
# keybind: Vyom/quick settings | Shift+Enter | Open the focused setting's details (e.g. the Wi-Fi list)
# keybind: Vyom/quick settings | M | Toggle mute on the sound output
# keybind: Vyom/quick settings | L | Lock the screen
# keybind: Vyom/quick settings | P | Open the power menu
# keybind: Vyom/quick settings | Esc | Close quick settings

DEFAULT_TILES = ["wifi", "bluetooth", "hotspot", "dnd", "caffeine", "theme", "wallpaper", "power-profile"]
# A tile's details in another Vyom tool, when it's installed and the tile has no `open` command.
DETAILS = {"wifi": ("tarang", []), "bluetooth": ("setu", []), "hotspot": ("tarang", ["hotspot"])}
CHEVRON = "\U000f0142"


def sentence(text):
    """ "screen stays on" -> "Screen stays on" (names like an SSID are left alone)."""
    return text[:1].upper() + text[1:] if text else text


class TileButton(Gtk.Button):
    """A toggle: a rounded icon square (filled in the tile's colour when on),
    its name and what it's on, and "On" / "Off" or a chevron for details."""

    def __init__(self, plugin, tile):
        super().__init__()
        self.plugin, self.tile, self.on = plugin, tile, None
        self.add_css_class("qs-tile")
        self.add_css_class(f"q-{tile.color}")
        self.internal = None if tile.open_cmd else DETAILS.get(tile.key)
        if self.internal and self.internal[0] not in getattr(plugin.vyom, "plugins", {}):
            self.internal = None
        box = Gtk.Box(spacing=11)
        icon = ui.label(tile.icon, "qs-icon", halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        box.append(icon)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        text.append(ui.label(tile.title, "qs-title", xalign=0))
        self.sub = ui.label("…", "qs-sub", xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=16)
        text.append(self.sub)
        box.append(text)
        self.state = ui.label("", "qs-state", valign=Gtk.Align.CENTER)
        self.state.set_visible(False)
        box.append(self.state)
        if self.has_details():
            box.append(ui.label(CHEVRON, "qs-more", valign=Gtk.Align.CENTER))
            click = Gtk.GestureClick(button=3)
            click.connect("pressed", lambda *_: self.open_details())
            self.add_controller(click)
            self.set_tooltip_text("Click: toggle · Right click or →: details")
        self.set_child(box)
        self.connect("clicked", lambda *_: self.activate_tile())

    def has_details(self):
        return bool(self.tile.open_cmd or self.internal)

    def show_state(self, on, sub):
        self.on = on
        self.sub.set_label(sub if self.tile.key in DETAILS else sentence(sub))
        (self.add_css_class if on else self.remove_css_class)("on")
        # On / Off in words, so the tint isn't the only sign. A tile with details
        # names what it's on instead (its subtitle says "Off" when it's off).
        word = on is not None and self.tile.shows_state and not self.has_details()
        self.state.set_visible(word)
        if word:
            self.state.set_label("On" if on else "Off")

    def activate_tile(self):
        want = not self.on if self.on is not None else True
        if self.on is not None:
            self.show_state(want, "…")
        self.plugin.background(lambda: self.tile.toggle(want), then=lambda _r: self.refresh())

    def open_details(self):
        if self.tile.open_cmd:
            self.plugin.close()
            system.spawn(self.tile.open_cmd)
            return True
        if self.internal:
            name, args = self.internal
            GLib.idle_add(lambda: (self.plugin.vyom.open(name, list(args)), False)[1])
            return True
        return False

    def refresh(self):
        self.plugin.background(self.tile.status, then=lambda r: self.show_state(*r) if isinstance(r, tuple) else None)


class SliderRow(Gtk.Box):
    """Icon button (mute), the name over a thick track, the value in words."""

    def __init__(self, plugin, source, css, name):
        super().__init__(spacing=12)
        self.plugin, self.source, self.busy, self.pending = plugin, source, False, None
        self.name = name
        self.add_css_class("qs-slider")
        self.add_css_class(css)
        self.icon = Gtk.Button(label=source.icon, valign=Gtk.Align.CENTER)
        self.icon.add_css_class("qs-slider-icon")
        if hasattr(source, "toggle_mute"):
            self.icon.connect("clicked", lambda *_: self.toggle_mute())
            self.icon.set_tooltip_text("Mute / unmute (M)")
        else:
            self.icon.set_can_focus(False)
            self.icon.set_can_target(False)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True, valign=Gtk.Align.CENTER)
        self.title = ui.label(name, "qs-slider-name", xalign=0, ellipsize=Pango.EllipsizeMode.END)
        col.append(self.title)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self.changed)
        col.append(self.scale)
        self.value = ui.label("", "qs-value", width_chars=6, xalign=1, valign=Gtk.Align.CENTER)
        for w in (self.icon, col, self.value):
            self.append(w)

    def toggle_mute(self):
        self.plugin.background(self.source.toggle_mute, then=lambda _r: self.refresh())

    def changed(self, scale):
        v = int(scale.get_value())
        self.value.set_label(f"{v}%")
        self.value.remove_css_class("muted")
        if self.busy:
            return
        if self.pending:  # coalesce a drag into one command every 80 ms
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(80, self.apply, v)

    def apply(self, v):
        self.pending = None
        self.plugin.background(lambda: self.source.set(v))
        return False

    def refresh(self):
        def get():
            v = self.source.get()
            dev = self.source.device() if hasattr(self.source, "device") else ""
            return v, dev

        def show(r):
            if not isinstance(r, tuple):
                return
            (v, muted), dev = r
            self.busy = True
            self.scale.set_value(v)
            self.busy = False
            self.title.set_label(f"{self.name} · {dev}" if dev else self.name)
            self.value.set_label("Muted" if muted else f"{v}%")
            (self.value.add_css_class if muted else self.value.remove_css_class)("muted")
            (self.add_css_class if muted else self.remove_css_class)("is-muted")
            if hasattr(self.source, "icon_muted"):
                self.icon.set_label(self.source.icon_muted if muted else self.source.icon)
        self.plugin.background(get, then=show)


class Plugin(Base):
    name, title, icon, color = "kendra", "Quick settings", "\U000f0493", "mauve"
    layout = "card"
    width = 420
    anchor = ("top", "right")

    def __init__(self, vyom, conf):
        super().__init__(vyom, conf)
        self.margins = {"top": int(self.conf.get("margin_top", 6)), "right": int(self.conf.get("margin_right", 8))}
        self.card = None
        self.tiles, self.sliders = [], []

    def build_card(self):
        if self.card is None:
            self.card = self._build()
        self.refresh_all()
        if self.tiles:   # once it's in the window (grabbing before does nothing)
            GLib.idle_add(self.first_focus)
        return self.card

    def first_focus(self):
        self.tiles[0].grab_focus()
        # Where you are, drawn by us: a layer-shell panel isn't always an
        # "active" window, so GTK's :focus can't be relied on.
        if self.panel is not None and getattr(self, "watched_panel", None) is not self.panel:
            self.watched_panel = self.panel
            self.panel.connect("notify::focus-widget", lambda *_: self.mark_focus())
        self.mark_focus()
        return False

    def mark_focus(self):
        focus = self.panel.get_focus() if self.panel is not None else None
        for w in self.tiles + [s.scale for s in self.sliders] + [s.icon for s in self.sliders] + \
                list(getattr(self, "session_buttons", [])):
            (w.add_css_class if w is focus else w.remove_css_class)("sel")

    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("qs")
        root.append(self._header())
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, column_homogeneous=True)
        grid.add_css_class("qs-tiles")
        for key in self.conf.get("tiles", DEFAULT_TILES):
            tile = system.make_tile(key, self.conf.get("tile", {}).get(key, {}))
            if not tile.available():
                continue  # tool missing or no such hardware: no tile
            b = TileButton(self, tile)
            n = len(self.tiles)
            grid.attach(b, n % 2, n // 2, 1, 1)
            self.tiles.append(b)
        root.append(grid)
        sliders = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sliders.add_css_class("qs-sliders")
        for src, css, name in ((system.Volume(), "volume", "Volume"), (system.Brightness(), "brightness", "Brightness")):
            if src.available():
                row = SliderRow(self, src, css, name)
                sliders.append(row)
                self.sliders.append(row)
        root.append(sliders)
        foot = Gtk.Box(spacing=14)
        foot.add_css_class("qs-foot")
        hints = [("Arrows", "move"), ("Enter", "toggle")]
        if any(t.has_details() for t in self.tiles):
            hints.append(("→", "open"))
        if any(hasattr(s.source, "toggle_mute") for s in self.sliders):
            hints.append(("M", "mute"))
        for keys, what in hints:
            foot.append(ui.hint_label(keys, what))
        esc = ui.hint_label("Esc", "close")
        esc.set_hexpand(True)
        esc.set_halign(Gtk.Align.END)
        foot.append(esc)
        root.append(foot)
        return root

    def _header(self):
        box = Gtk.Box(spacing=12)
        box.add_css_class("qs-header")
        box.append(ui.label(system.user_name()[:1], "qs-avatar", valign=Gtk.Align.CENTER))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER, hexpand=True)
        self.hello = ui.label("", "qs-hello", xalign=0)
        self.chip_box = Gtk.Box(spacing=6)
        text.append(self.hello)
        text.append(self.chip_box)
        box.append(text)
        # Lock and power, set apart from the tiles; power in red. L and P do the same.
        self.session, self.session_buttons = {}, []
        for icon, key, tip, css in (("\U000f033e", "lock", "Lock the screen (L)", "lock"),
                                    ("\U000f0425", "power", "Power menu (P)", "power")):
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
        child = self.chip_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.chip_box.remove(child)
            child = nxt
        bat = system.battery()
        if bat:
            pct, charging, left = bat
            color = "green" if charging or pct > 30 else "yellow" if pct > 15 else "red"
            icon = "\U000f0084" if charging else "\U000f0079" if pct > 90 else \
                chr(0xF007A + min(8, max(0, pct // 10 - 1)))   # 󰁺..󰂂 by tens
            text = f"{pct}%" + (f" · {left} {'to full' if charging else 'left'}" if left else "")
            self.chip_box.append(ui.chip(text, color, icon))
        up = system.uptime()
        if up:
            self.chip_box.append(ui.chip(up, "gray", "\U000f0150"))
        for t in self.tiles:
            t.refresh()
        for s in self.sliders:
            s.refresh()

    def focused_tile(self):
        w = self.panel.get_focus() if self.panel is not None else None
        while w is not None and not isinstance(w, TileButton):
            w = w.get_parent()
        return w

    def key(self, name, row, mods):
        if name in ("Return", "KP_Enter") and "shift" in mods:
            t = self.focused_tile()
            return bool(t and t.open_details())
        if name in ("Up", "Down") and not mods and self.panel is not None \
                and any(self.panel.get_focus() is s.scale for s in self.sliders):
            # Up / Down leave a slider (Left / Right change it), like everywhere else here.
            self.panel.child_focus(Gtk.DirectionType.UP if name == "Up" else Gtk.DirectionType.DOWN)
            return True
        if name == "Right" and not mods:
            t = self.focused_tile()
            if t is not None and t.has_details():
                return t.open_details()
            return False
        if mods:
            return False
        if name in ("m", "M"):
            for s in self.sliders:
                if hasattr(s.source, "toggle_mute"):
                    s.toggle_mute()
                    return True
            return False
        if name in ("l", "L"):
            return self.session_action("lock")
        if name in ("p", "P"):
            return self.session_action("power")
        return False
