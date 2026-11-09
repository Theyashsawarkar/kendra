"""kendra (केन्द्र, "centre"): quick settings for Vyom.

Toggles, sliders, battery and session buttons in a panel under the bar's
top-right corner. Opens with the last known state, then every tile
refreshes in a background thread, so slow tools never hold it up.
"""
from gi.repository import GLib, Gtk, Pango

from vyom import Plugin as Base
from vyom import Hint, ui

from . import system, vim

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
        box = Gtk.Box(spacing=9)
        icon = ui.label(tile.icon, "qs-icon", halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        box.append(icon)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        text.append(ui.label(tile.title, "qs-title", xalign=0))
        self.sub = ui.label("…", "qs-sub", xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=13)
        text.append(self.sub)
        box.append(text)
        self.state = ui.label("", "qs-state", valign=Gtk.Align.CENTER)
        self.state.set_visible(False)
        box.append(self.state)
        if self.has_details():
            # The arrow is its own target: a click on it opens the details
            # (tarang, setu…); a click anywhere else on the tile toggles it.
            more = ui.label(CHEVRON, "qs-more", valign=Gtk.Align.CENTER)
            more.set_tooltip_text("Open details")
            arrow = Gtk.GestureClick(button=1)
            arrow.connect("pressed", self.arrow_pressed)
            arrow.connect("released", lambda *_: self.open_details())
            more.add_controller(arrow)
            box.append(more)
            click = Gtk.GestureClick(button=3)
            click.connect("pressed", lambda *_: self.open_details())
            self.add_controller(click)
            self.set_tooltip_text("Click or Enter: toggle · the arrow, right click or o: details")
        self.set_child(box)
        self.connect("clicked", lambda *_: self.activate_tile())

    @staticmethod
    def arrow_pressed(gesture, *_):
        # Claim the press so the tile's own click (toggle) never sees it.
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

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
            self.icon.set_tooltip_text("Mute / unmute (m)")
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
    width = 360
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
        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
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
        sliders = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sliders.add_css_class("qs-sliders")
        for src, css, name in ((system.Volume(), "volume", "Volume"), (system.Brightness(), "brightness", "Brightness")):
            if src.available():
                row = SliderRow(self, src, css, name)
                sliders.append(row)
                self.sliders.append(row)
        root.append(sliders)
        # The keys are in Vyom's footer (a modal card has one).
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
        if self.panel.get_focus() is None and self.tiles:
            self.tiles[0].grab_focus()
            return
        d = {"left": Gtk.DirectionType.LEFT, "right": Gtk.DirectionType.RIGHT,
             "down": Gtk.DirectionType.DOWN, "up": Gtk.DirectionType.UP}[way]
        for _ in range(n):
            self.panel.child_focus(d)

    def v_top(self, _n, _a):
        if self.tiles:
            self.tiles[0].grab_focus()

    def v_bottom(self, _n, _a):
        last = ([s.scale for s in self.sliders] or self.tiles)[-1:]
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
        if t is None or not t.open_details():
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
