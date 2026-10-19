"""kendra (केन्द्र, "centre"): quick settings for Vyom.

Toggles, sliders, battery and session buttons in a panel under the bar's
top-right corner. Opens with the last known state, then every tile
refreshes in a background thread, so slow tools never hold it up.
"""
from gi.repository import Gtk, Pango

from vyom import Plugin as Base
from vyom import ui

from . import system

# keybind: Vyom/quick settings | Arrows | Move between the toggles and sliders
# keybind: Vyom/quick settings | Enter / Space | Toggle the focused setting
# keybind: Vyom/quick settings | Shift+Enter | Open the focused setting's details (e.g. the Wi-Fi list)
# keybind: Vyom/quick settings | Esc | Close quick settings

DEFAULT_TILES = ["wifi", "bluetooth", "hotspot", "dnd", "caffeine", "theme", "wallpaper", "power-profile"]


class TileButton(Gtk.Button):
    def __init__(self, plugin, tile):
        super().__init__()
        self.plugin, self.tile, self.on = plugin, tile, None
        self.add_css_class("qs-tile")
        self.add_css_class(f"q-{tile.color}")
        box = Gtk.Box(spacing=12)
        box.append(ui.label(tile.icon, "qs-icon"))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        text.append(ui.label(tile.title, "qs-title", xalign=0))
        self.sub = ui.label("…", "qs-sub", xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=18)
        text.append(self.sub)
        box.append(text)
        if tile.open_cmd:
            box.append(ui.label("\U000f0142", "qs-more", hexpand=True, halign=Gtk.Align.END))
            click = Gtk.GestureClick(button=3)
            click.connect("pressed", lambda *_: self.open_details())
            self.add_controller(click)
            self.set_tooltip_text("Click: toggle · Right click or Shift+Enter: details")
        self.set_child(box)
        self.connect("clicked", lambda *_: self.activate_tile())

    def show_state(self, on, sub):
        self.on = on
        self.sub.set_label(sub)
        (self.add_css_class if on else self.remove_css_class)("on")

    def activate_tile(self):
        want = not self.on if self.on is not None else True
        if self.on is not None:
            self.show_state(want, "…")
        self.plugin.background(lambda: self.tile.toggle(want), then=lambda _r: self.refresh())

    def open_details(self):
        if self.tile.open_cmd:
            self.plugin.close()
            system.spawn(self.tile.open_cmd)

    def refresh(self):
        self.plugin.background(self.tile.status, then=lambda r: self.show_state(*r) if isinstance(r, tuple) else None)


class SliderRow(Gtk.Box):
    def __init__(self, plugin, source, css):
        super().__init__(spacing=12)
        self.plugin, self.source, self.busy, self.pending = plugin, source, False, None
        self.add_css_class("qs-slider")
        self.add_css_class(css)
        self.icon = Gtk.Button(label=source.icon)
        self.icon.add_css_class("qs-slider-icon")
        if hasattr(source, "toggle_mute"):
            self.icon.connect("clicked", lambda *_: plugin.background(source.toggle_mute, then=lambda _r: self.refresh()))
            self.icon.set_tooltip_text("Mute / unmute")
        else:
            self.icon.set_can_focus(False)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self.changed)
        self.value = ui.label("", "qs-value", width_chars=5, xalign=1)
        for w in (self.icon, self.scale, self.value):
            self.append(w)

    def changed(self, scale):
        from gi.repository import GLib
        v = int(scale.get_value())
        self.value.set_label(str(v))
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
        def show(r):
            if not isinstance(r, tuple):
                return
            v, muted = r
            self.busy = True
            self.scale.set_value(v)
            self.busy = False
            self.value.set_label("muted" if muted else str(v))
            if hasattr(self.source, "icon_muted"):
                self.icon.set_label(self.source.icon_muted if muted else self.source.icon)
        self.plugin.background(self.source.get, then=show)


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
        if self.tiles:
            self.tiles[0].grab_focus()
        return self.card

    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("qs")
        root.append(self._header())
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        for key in self.conf.get("tiles", DEFAULT_TILES):
            tile = system.make_tile(key, self.conf.get("tile", {}).get(key, {}))
            if not tile.available():
                continue  # tool missing or no such hardware: no tile
            b = TileButton(self, tile)
            n = len(self.tiles)
            grid.attach(b, n % 2, n // 2, 1, 1)
            self.tiles.append(b)
        root.append(grid)
        sliders = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sliders.add_css_class("qs-sliders")
        for src, css in ((system.Volume(), "volume"), (system.Brightness(), "brightness")):
            if src.available():
                row = SliderRow(self, src, css)
                sliders.append(row)
                self.sliders.append(row)
        root.append(sliders)
        foot = Gtk.Box(spacing=14)
        foot.add_css_class("qs-foot")
        for keys, what in (("Arrows", "move"), ("Enter", "toggle"), ("Shift+Enter", "details")):
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
        box.append(ui.label(system.user_name()[:1], "qs-avatar"))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        self.hello = ui.label("", "qs-hello", xalign=0)
        self.meta_l = ui.label("", "qs-meta", xalign=0)
        text.append(self.hello)
        text.append(self.meta_l)
        box.append(text)
        for icon, key, tip, css in (("\U000f033e", "lock", "Lock the screen", "lock"),
                                    ("\U000f0425", "power", "Power menu", "power")):
            cmd = self.conf.get(key, "loginctl lock-session" if key == "lock" else None)
            if not cmd or not system.have(cmd):
                continue
            b = Gtk.Button(label=icon, tooltip_text=tip)
            b.add_css_class("qs-round")
            b.add_css_class(css)
            b.connect("clicked", lambda _b, c=cmd: (self.close(), system.spawn(c)))
            box.append(b)
        return box

    def refresh_all(self):
        self.hello.set_label(f"{system.greeting()}, {system.user_name()}")
        parts = [system.uptime()]
        bat = system.battery()
        if bat:
            pct, charging, left = bat
            parts.append(f"{pct}% {'charging' if charging else 'battery'}"
                         + (f", {left} {'to full' if charging else 'left'}" if left else ""))
        self.meta_l.set_label(" · ".join(p for p in parts if p))
        for t in self.tiles:
            t.refresh()
        for s in self.sliders:
            s.refresh()

    def key(self, name, row, mods):
        if name in ("Return", "KP_Enter") and "shift" in mods and self.panel is not None:
            w = self.panel.get_focus()
            while w is not None and not isinstance(w, TileButton):
                w = w.get_parent()
            if w:
                w.open_details()
                return True
        return False
