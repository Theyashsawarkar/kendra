"""kendra's bento (2026-11-26): the panel's parts, by size.

Squares for what you pick from and want to see at a glance (Wi-Fi: signal,
speed now and the last minute as two lines; Bluetooth: the device that
matters, its buds and case), tall capsules for volume and brightness,
segments for the things you choose one of (Jyoti's lamps, power modes),
circles for plain on / off switches, and the wallpaper you're on as a pill.

Everywhere: left click (or Enter) does the obvious thing, right click (or o)
opens the full panel where there is one, and the line at the bottom of the
panel says what the thing under the pointer or the keyboard is doing.
"""
import math

import gi

gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango, PangoCairo
from vyom import ui

from . import live, system

CHEVRON = "\U000f0142"
# a connection's kind: its glyph (Material Design Icons) for the network square
NET_GLYPHS = {"wifi": "\U000f05a9", "ethernet": "\U000f0200", "usb": "\U000f0553", "mobile": "\U000f08be",
              "bluetooth": "\U000f00af", "vpn": "\U000f099d", "wireguard": "\U000f099d", "bridge": "\U000f0317"}
NET_OTHER = "\U000f06f3"
REFRESH = "\U000f0450"
NERD = "JetBrainsMono Nerd Font Propo"


def rgba(widget):
    c = widget.get_color()
    return c.red, c.green, c.blue, c.alpha


def glyph(text, size, cls=""):
    """A Nerd Font glyph drawn centred on its ink (an icon font leaves
    uneven room around its glyphs), in the CSS colour of `cls`."""
    area = Gtk.DrawingArea(content_width=size, content_height=size, can_target=False)
    area.add_css_class("k-glyph")
    if cls:
        area.add_css_class(cls)
    area.text = text

    def draw(widget, cr, w, h):
        layout = widget.create_pango_layout(widget.text)
        layout.set_font_description(Pango.FontDescription.from_string(f"{NERD} {size * 0.78:.1f}px"))
        ink, _ = layout.get_pixel_extents()
        cr.set_source_rgba(*rgba(widget))
        cr.move_to(round((w - ink.width) / 2 - ink.x), round((h - ink.height) / 2 - ink.y))
        PangoCairo.show_layout(cr, layout)
    area.set_draw_func(draw)
    return area


def set_glyph(area, text):
    area.text = text
    area.queue_draw()


class Hoverable:
    """Says what it is in the panel's bottom line on hover and on focus."""

    def say_on(self, widget, plugin, text_fn):
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: plugin.say(text_fn()))
        widget.add_controller(motion)
        widget.connect("notify::has-focus", lambda w, _p: w.has_focus() and plugin.say(text_fn()))


def right_click(widget, fn):
    g = Gtk.GestureClick(button=3)
    g.connect("pressed", lambda *_: fn())
    widget.add_controller(g)


# ------------------------------------------------------------- circles
class Circle(Gtk.Button, Hoverable):
    """A plain on / off switch: the icon in a circle, filled in its colour
    when on. Left click toggles, right click opens its panel."""

    def __init__(self, plugin, tile, size=40):
        super().__init__(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        self.plugin, self.tile, self.on, self.sub = plugin, tile, None, ""
        self.add_css_class("k-circle")
        self.add_css_class(f"q-{tile.color}")
        self.set_size_request(size, size)
        self.icon = glyph(tile.icon, 23)
        self.set_child(self.icon)
        self.connect("clicked", lambda *_: self.activate_tile())
        right_click(self, self.open_details)
        self.say_on(self, plugin, self.words)

    def words(self):
        state = self.sub or ("On" if self.on else "Off")
        tail = " · right click: details" if self.tile.open_cmd else ""
        return f"<b>{GLib.markup_escape_text(self.tile.title)}</b>  {GLib.markup_escape_text(state)}{tail}"

    def show_state(self, on, sub):
        self.on, self.sub = on, system_sentence(sub)
        (self.add_css_class if on else self.remove_css_class)("on")
        self.set_tooltip_text(f"{self.tile.title}: {self.sub}")
        self.icon.queue_draw()

    def activate_tile(self):
        want = not self.on if self.on is not None else True
        if self.on is not None:
            self.show_state(want, "…")
        self.plugin.background(lambda: self.tile.toggle(want), then=lambda _r: self.refresh())

    def open_details(self):
        return self.plugin.open_details(self.tile.key, self.tile.open_cmd)

    def refresh(self):
        r = self.tile.live_status()
        if r is not None:
            self.show_state(*r)
            if not (self.tile.key == "hotspot" and r[0]):   # on: who's connected is the command's to say
                return
        self.plugin.background(self.tile.status, then=lambda r: self.show_state(*r) if isinstance(r, tuple) else None)


def system_sentence(text):
    return text[:1].upper() + text[1:] if text else text


# ------------------------------------------------------------- segments
class Segments(Gtk.Box, Hoverable):
    """Pick one of a few (Jyoti: Off / Akhaṇḍa / Nandādīpa; power modes).
    Icons only; the one that's chosen grows into a pill in its colour and
    shows its name."""

    def __init__(self, plugin, title, options, on_pick, open_fn=None, words=None):
        super().__init__(spacing=4)
        words = words or {}
        self.plugin, self.title, self.on_pick, self.open_fn = plugin, title, on_pick, open_fn
        self.add_css_class("k-seg")
        self.buttons, self.current = {}, None
        for key, name, icon, color in options:
            b = Gtk.Button(hexpand=False)
            b.add_css_class("k-opt")
            b.add_css_class(f"q-{color}")
            box = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
            box.append(glyph(icon, 21))
            lab = ui.label(name, "k-opt-name")
            lab.set_visible(False)
            box.append(lab)
            b.set_child(box)
            b.name_label, b.key, b.name = lab, key, name
            b.connect("clicked", lambda _b, k=key: self.pick(k))
            if open_fn:
                right_click(b, open_fn)
            self.say_on(b, plugin, lambda n=name: f"<b>{GLib.markup_escape_text(title)}</b>  {n}"
                        + (f" · {words[n]}" if words.get(n) else "")
                        + ("  · right click: details" if open_fn else ""))
            b.set_tooltip_text(f"{title}: {name}")
            self.buttons[key] = b
            self.append(b)

    def show(self, key):
        self.current = key
        for k, b in self.buttons.items():
            on = k == key
            (b.add_css_class if on else b.remove_css_class)("on")
            b.set_hexpand(on)
            b.name_label.set_visible(on)

    def pick(self, key):
        if key == self.current:
            return
        self.show(key)
        self.on_pick(key)


# ------------------------------------------------------------- sliders
class Tall(Gtk.Overlay, Hoverable):
    """Volume or brightness as a tall capsule that fills from the bottom: the
    value at the top, the icon at the foot. Right click on volume mutes."""

    def __init__(self, plugin, source, css, name):
        super().__init__()
        self.plugin, self.source, self.name, self.busy, self.pending = plugin, source, name, False, None
        self.add_css_class("k-tall")
        self.add_css_class(css)
        self.level, self.vel, self.muted, self.tick = None, 0.0, False, None
        self.known = False      # the last refresh came from Vyom's live state
        # fills its column, a little in from the sides: the two stand as a
        # slim pair beside Wi-Fi
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.fill = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.fill.add_css_class("k-liquid")
        self.fill.set_draw_func(self.draw_fill)
        self.set_child(self.fill)
        # The scale does the keys (focus, h / l, 0 / $); the capsule is drawn.
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1)
        self.scale.set_inverted(True)
        self.scale.set_draw_value(False)
        self.scale.set_opacity(0)
        self.scale.set_can_target(False)
        self.scale.connect("value-changed", self.changed)
        self.add_overlay(self.scale)
        # The wheel (or two fingers on the touchpad): up raises, down lowers,
        # 5% a notch; a touchpad's smooth scroll adds up to the same.
        scroll = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self.scrolled)
        self.add_controller(scroll)
        self.scroll_rest = 0.0
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", lambda g, x, y: self.point(y))
        drag.connect("drag-update", lambda g, dx, dy: self.point(g.get_start_point()[2] + dy))
        self.add_controller(drag)
        self.value = ui.label("", "k-tall-value", valign=Gtk.Align.START, halign=Gtk.Align.CENTER, can_target=False)
        self.icon = glyph(source.icon, 24, "k-tall-icon")
        self.icon.set_valign(Gtk.Align.END)
        self.icon.set_halign(Gtk.Align.CENTER)
        self.add_overlay(self.value)
        self.add_overlay(self.icon)
        self.dev = ""
        if hasattr(source, "toggle_mute"):
            right_click(self, self.toggle_mute)
        self.say_on(self.scale, plugin, self.words)
        self.say_on(self, plugin, self.words)
        # The surface moves only while the panel shows (a frame clock tick).
        self.connect("map", lambda *_: self.start_motion())
        self.connect("unmap", lambda *_: self.stop_motion())

    def start_motion(self):
        if self.tick is None:
            self.tick = self.fill.add_tick_callback(self.step)

    def stop_motion(self):
        if self.tick is not None:
            self.fill.remove_tick_callback(self.tick)
            self.tick = None

    def step(self, widget, clock):
        """The surface springs to the value (a little slosh) and keeps a
        slow wave; redraws at most ~30 times a second."""
        target = self.scale.get_value()
        if self.level is None:
            self.level = target
        self.vel = (self.vel + (target - self.level) * 0.08) * 0.78
        self.level += self.vel
        t = clock.get_frame_time() / 1e6
        if t - getattr(self, "last", 0) >= 1 / 30:
            self.last, self.phase = t, t
            widget.queue_draw()
        return GLib.SOURCE_CONTINUE

    def scrolled(self, _ctl, _dx, dy):
        self.scroll_rest += dy
        steps = int(self.scroll_rest)          # whole notches; keep the rest
        if steps:
            self.scroll_rest -= steps
            v = self.scale.get_value() - 5 * steps
            self.scale.set_value(max(0, min(100, v)))
            self.plugin.say(self.words())
        return True

    def point(self, y):
        h = self.get_height() or 1
        self.scale.set_value(round(max(0, min(100, (1 - y / h) * 100))))
        self.scale.grab_focus()

    def draw_fill(self, area, cr, w, h):
        """A glass pill holding liquid up to the level: a faint wave behind,
        a shaded one in front, a thin highlight down the glass."""
        import cairo  # noqa: PLC0415

        def pill():
            # a rounded column (corners about a third of its width), not a
            # full capsule: the liquid fills the whole column
            r = min((w - 2) * 0.34, 26)   # the same corners as the squares
            x0, y0, x1, y1 = 1, 1, w - 1, h - 1
            cr.new_sub_path()
            cr.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
            cr.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
            cr.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
            cr.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()
        pill()
        cr.set_source_rgba(1, 1, 1, 0.07)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.13)
        cr.set_line_width(1)
        cr.stroke()
        lv = max(0.0, min(100.0, self.level if self.level is not None else self.scale.get_value())) / 100
        if lv <= 0:
            self.draw_rim(cr, pill)
            return
        top, full = 1, h - 2
        surf = top + full * (1 - lv)
        amp = 0 if self.muted else 2.2 + min(6, abs(self.vel) * 1.5)
        ph = getattr(self, "phase", 0) / 0.65
        red, g, b, a = rgba(area)
        if self.muted:
            red = g = b = 0.6
        cr.save()
        pill()
        cr.clip()
        for back, k, shift, alpha in ((True, 1.3, 1.0, 0.45), (False, 1.1, 0.0, 1.0)):
            cr.move_to(0, surf)
            x = 0.0
            while x <= w:
                sign = 1 if back else -1
                cr.line_to(x, surf + math.sin(x / (w / k) * 2 * math.pi + sign * ph * (1.3 if back else 1) + shift) * amp * (0.8 if back else 1))
                x += 2
            cr.line_to(w, h)
            cr.line_to(0, h)
            cr.close_path()
            if back:
                cr.set_source_rgba(red, g, b, a * alpha)
            else:
                grad = cairo.LinearGradient(0, surf, 0, h)
                grad.add_color_stop_rgba(0, red, g, b, a)
                grad.add_color_stop_rgba(1, red * 0.86, g * 0.86, b * 0.86, a)
                cr.set_source(grad)
            cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.18)
        cr.rectangle(w * 0.16, surf + 6, 2.5, max(0, h - surf - 14))
        cr.fill()
        cr.restore()
        self.draw_rim(cr, pill)

    def draw_rim(self, cr, pill):
        """Where you are (keyboard focus): a light rim on the column's own
        shape, drawn here so it can't differ from it."""
        if not self.has_css_class("sel"):
            return
        pill()
        cr.set_source_rgba(0.957, 0.957, 0.949, 0.9)
        cr.set_line_width(2.5)
        cr.stroke()

    def words(self):
        v = int(self.scale.get_value())
        what = f"{self.name}{' · ' + self.dev if self.dev else ''}"
        tail = "  · right click: mute" if hasattr(self.source, "toggle_mute") else ""
        return f"<b>{GLib.markup_escape_text(what)}</b>  {v}%{tail}"

    def toggle_mute(self):
        self.plugin.background(self.source.toggle_mute, then=lambda _r: self.refresh())

    def changed(self, scale):
        v = int(scale.get_value())
        self.value.set_label(f"{v}%")
        self.mark_dark(v)
        self.start_motion()
        self.remove_css_class("is-muted")
        if self.busy:
            return
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(80, self.apply, v)

    def mark_dark(self, v):
        # dark ink where the liquid covers the number (top) or the icon (foot)
        (self.add_css_class if v >= 88 else self.remove_css_class)("full")
        (self.add_css_class if v < 14 else self.remove_css_class)("low")

    def apply(self, v):
        self.pending = None
        self.plugin.background(lambda: self.source.set(v))
        return False

    def refresh(self, live_only=False):
        """From the live state at once when Vyom has it (volume, brightness);
        else wpctl / brightnessctl in a thread."""
        now = (live.volume(live.get("volume")) if self.name == "Volume" else
               live.brightness(live.get("brightness")))
        self.known = now is not None

        def get():
            return self.source.get(), (self.source.device() if hasattr(self.source, "device") else "")

        def show(r):
            if not isinstance(r, tuple):
                return
            (v, muted), self.dev = r
            self.busy = True
            self.scale.set_value(v)
            self.busy = False
            self.start_motion()
            self.value.set_label("Muted" if muted else f"{v}%")
            self.mark_dark(0 if muted else v)
            (self.add_css_class if muted else self.remove_css_class)("is-muted")
            self.muted = muted
            if hasattr(self.source, "icon_muted"):
                set_glyph(self.icon, self.source.icon_muted if muted else self.source.icon)
        if now is not None:
            if not self.pending:     # not while you're dragging it
                show(now)
            return
        if live_only:
            return
        self.plugin.background(get, then=show)


# ------------------------------------------------------------- squares
class Square(Gtk.Box, Hoverable):
    """A big rounded square: its toggle (the circle, top left), what more
    there is (the round arrow, top right; right click too) and a body."""

    def __init__(self, plugin, tile, color):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.plugin, self.tile, self.on, self.sub = plugin, tile, None, ""
        self.add_css_class("k-square")
        top = Gtk.Box(spacing=6)
        self.toggle = Gtk.Button(valign=Gtk.Align.CENTER)
        self.toggle.add_css_class("k-circle")
        self.toggle.add_css_class("k-sq-toggle")
        self.toggle.add_css_class(f"q-{color}")
        self.toggle.set_size_request(40, 40)
        self.toggle.set_child(glyph(tile.icon, 22))
        self.toggle.connect("clicked", lambda *_: self.activate_tile())
        self.toggle.owner = self
        top.append(self.toggle)
        top.append(Gtk.Box(hexpand=True))
        self.extra = Gtk.Box(valign=Gtk.Align.CENTER)
        top.append(self.extra)
        self.go = Gtk.Button(valign=Gtk.Align.CENTER)
        self.go.add_css_class("k-go")
        self.go.set_child(glyph(CHEVRON, 18))
        self.go.set_tooltip_text("Open the full panel (right click, o)")
        self.go.connect("clicked", lambda *_: self.open_details())
        self.go.set_can_focus(False)
        top.append(self.go)
        self.append(top)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, vexpand=True)
        self.append(self.body)
        click = Gtk.GestureClick(button=1)
        click.connect("released", lambda g, n, x, y: self.body_clicked(x, y))
        self.body.add_controller(click)
        right_click(self, self.open_details)
        self.say_on(self, self.plugin, self.words)
        self.say_on(self.toggle, self.plugin, self.words)

    def body_clicked(self, _x, _y):
        self.open_details()

    def words(self):
        return f"<b>{GLib.markup_escape_text(self.tile.title)}</b>  {GLib.markup_escape_text(self.sub)}  · right click: details"

    def activate_tile(self):
        want = not self.on if self.on is not None else True
        self.plugin.background(lambda: self.tile.toggle(want), then=lambda _r: self.refresh())

    def open_details(self):
        return self.plugin.open_details(self.tile.key, self.tile.open_cmd)

    def show_on(self, on):
        self.on = on
        (self.toggle.add_css_class if on else self.toggle.remove_css_class)("on")
        (self.add_css_class if on else self.remove_css_class)("on")


def bars(level, size=(18, 14)):
    """Signal bars: `level` of 4 lit in green."""
    area = Gtk.DrawingArea(content_width=size[0], content_height=size[1], valign=Gtk.Align.CENTER)
    area.level = level

    def draw(widget, cr, w, h):
        bw = 3.4
        for i in range(4):
            bh = h * (i + 1) / 4
            x = i * (bw + 1.4)
            if i < widget.level:
                cr.set_source_rgba(0.557, 0.886, 0.651, 1)
            else:
                cr.set_source_rgba(1, 1, 1, 0.18)
            r = bw / 2
            cr.new_sub_path()
            cr.arc(x + r, h - bh + r, r, math.pi, 0)
            cr.arc(x + r, h - r, r, 0, math.pi)
            cr.close_path()
            cr.fill()
    area.set_draw_func(draw)
    return area


def speed_text(mbps):
    """A link's speed in Mb/s, in words ("1 Gb/s", "100 Mb/s"); "" unknown."""
    try:
        v = float(mbps or 0)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return ""
    if v >= 1000:
        g = v / 1000
        return f"{g:.0f} Gb/s" if g == int(g) else f"{g:.1f} Gb/s"
    return f"{v:.0f} Mb/s"


class WifiSquare(Square):
    """The network you're on, whatever it runs over: Wi-Fi's signal bars or
    the connection's glyph (a cable, a phone, a modem, a VPN), its name and
    kind, the download speed big with upload beside it, and the last minute
    as two lines (download sky, upload mauve), each with its peak marked.
    The connection carrying your traffic shows; "+1" (top right) shows the
    next one. The circle stays Wi-Fi's on / off."""

    def __init__(self, plugin, tile, traffic):
        super().__init__(plugin, tile, "sky")
        self.traffic = traffic
        self.add_css_class("wifi")
        self.conns, self.idx, self.connected = [], 0, False
        self.state = (None, "", None, None)
        self.more = Gtk.Button(label="")
        self.more.add_css_class("k-more")
        self.more.connect("clicked", lambda *_: self.next_connection())
        self.more.set_can_focus(False)
        self.more.set_visible(False)
        self.extra.append(self.more)
        head = Gtk.Box(spacing=6)
        self.bars = bars(0)
        head.append(self.bars)
        self.kind_glyph = ui.label("", "k-net-glyph", valign=Gtk.Align.CENTER)
        self.kind_glyph.set_visible(False)
        head.append(self.kind_glyph)
        self.ssid = ui.label("", "k-sq-name", xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END,
                             max_width_chars=16)
        head.append(self.ssid)
        self.kind = ui.label("", "k-net-kind", valign=Gtk.Align.CENTER)
        self.kind.set_visible(False)
        head.append(self.kind)
        big = Gtk.Box(spacing=4)
        self.speed = ui.label("—", "k-big", valign=Gtk.Align.BASELINE)
        self.unit = ui.label("", "k-unit", valign=Gtk.Align.BASELINE)
        self.upl = ui.label("", "k-up", valign=Gtk.Align.BASELINE, hexpand=True, xalign=1)
        for w in (self.speed, self.unit, self.upl):
            big.append(w)
        self.chart = Gtk.DrawingArea(content_height=32, hexpand=True, vexpand=True)
        self.chart.set_draw_func(self.draw_chart)
        axis = Gtk.Box(spacing=8)
        axis.append(ui.label("60 s", "k-axis"))
        axis.append(Gtk.Box(hexpand=True))
        self.peak_d = ui.label("", "k-axis", "k-axis-down")
        self.peak_u = ui.label("", "k-axis", "k-axis-up")
        axis.append(self.peak_d)
        axis.append(self.peak_u)
        for w in (head, big, self.chart, axis):
            self.body.append(w)
        self.pct = self.dbm = None

    def show_state(self, on, sub, pct=None, dbm=None, conns=None):
        self.state = (on, sub, pct, dbm)
        self.show_on(on)
        self.pct, self.dbm = pct, dbm
        if conns:
            self.show_connection(on, conns, pct, dbm)
            return
        self.conns = []
        self.more.set_visible(False)
        self.kind.set_visible(False)
        self.kind_glyph.set_visible(False)
        self.bars.set_visible(True)
        connected = bool(on and sub and not sub.startswith("On ·") and sub != "Off")
        self.connected = connected
        lvl, word = system.signal_word(pct) if connected else (0, "")
        self.bars.level = lvl
        self.bars.queue_draw()
        self.ssid.set_label(sub if connected else ("Off" if not on else sub.removeprefix("On · ").capitalize()))
        self.sub = (f"{sub} · {word.lower()}" + (f", {dbm} dBm" if dbm is not None else "")) if connected else (sub or "Off")
        self.update_speed()

    def show_connection(self, on, conns, pct, dbm):
        """One connection of several (the main one unless "+1" moved on):
        the same square whatever it runs over."""
        self.conns = conns
        self.idx = self.idx if 0 <= self.idx < len(conns) else 0
        c = conns[self.idx]
        kind = c.get("type") or "other"
        self.connected = True
        self.add_css_class("on")      # online, whatever the Wi-Fi circle says
        wifi = kind == "wifi"
        name = (c.get("ssid") or c.get("name")) if wifi else (c.get("name") or c.get("device") or "Connected")
        lvl, word = system.signal_word(c.get("strength", pct)) if wifi else (0, "")
        self.bars.level = lvl
        self.bars.queue_draw()
        self.bars.set_visible(wifi)
        self.kind_glyph.set_label(NET_GLYPHS.get(kind, NET_OTHER))
        self.kind_glyph.set_visible(not wifi)
        self.ssid.set_label(name)
        self.kind.set_label(c.get("label") or kind.capitalize())
        self.kind.set_visible(True)
        others = [o for i, o in enumerate(conns) if i != self.idx]
        self.more.set_label(f"+{len(others)}")
        self.more.set_visible(bool(others))
        self.more.set_tooltip_text("Also on: " + ", ".join(f"{o.get('name')} ({o.get('label')})" for o in others)
                                   + " · click to show it")
        if wifi:
            detail = word.lower() + (f", {dbm} dBm" if dbm is not None else "")
        elif kind in ("vpn", "wireguard"):
            detail = f"over {c['via']}" if c.get("via") else ""
        elif kind == "mobile":
            detail = f"operator {c['operator']}" if c.get("operator") else ""
        else:
            detail = speed_text(c.get("speed"))
        standby = "" if (c.get("primary") or self.idx == 0) else " · standby"
        self.sub = name + (f" · {detail}" if detail else "") + standby
        dev = c.get("vpn_device") or c.get("device") or c.get("via_device") or None
        if dev and dev != self.traffic.dev:
            self.traffic.dev = dev
            self.traffic.down, self.traffic.up, self.traffic.last = [], [], None
            self.plugin.reload_traffic()
        self.update_speed()

    def next_connection(self):
        if len(self.conns) > 1:
            self.idx = (self.idx + 1) % len(self.conns)
            on, sub, pct, dbm = self.state
            self.show_state(on, sub, pct, dbm, self.conns)
            self.plugin.say(self.words())

    def update_speed(self):
        t = self.traffic
        if self.connected and t.down:
            n, u = system.rate(t.down[-1])
            self.speed.set_label(n)
            self.unit.set_label(f"↓ {u}")
            un, uu = system.rate(t.up[-1])
            self.upl.set_label(f"{un} {uu if uu != u else ''} ↑".replace("  ", " "))
            pd, pdu = system.rate(max(t.down))
            pu, puu = system.rate(max(t.up))
            self.peak_d.set_label(f"↓ peak {pd} {pdu}")
            self.peak_u.set_label(f"↑ {pu} {puu}")
        else:
            self.speed.set_label("—")
            self.unit.set_label("")
            self.upl.set_label("")
            self.peak_d.set_label("measuring…" if self.connected else "")
            self.peak_u.set_label("")
        self.chart.queue_draw()

    def words(self):
        t = self.traffic
        speeds = ""
        if self.connected and t.down:
            d, du = system.rate(t.down[-1])
            u, uu = system.rate(t.up[-1])
            speeds = f" · ↓ {d} {du} ↑ {u} {uu}"
        c = self.conns[self.idx] if 0 <= self.idx < len(self.conns) else None
        what = (c.get("label") or "Network") if c else "Wi-Fi"
        more = f" · +{len(self.conns) - 1} shows the next" if len(self.conns) > 1 else ""
        return f"<b>{what}</b>  {GLib.markup_escape_text(self.sub + speeds)}{more}  · right click: networks"

    def draw_chart(self, area, cr, w, h):
        t = self.traffic
        if not (self.connected and len(t.down) > 1):
            return
        cr.set_line_join(1)  # round
        n = t.keep

        def line(vals, color, width):
            m = max(vals) or 1
            pts = [(w - (len(vals) - 1 - i) * (w / (n - 1)), h - 3 - v / m * (h - 9)) for i, v in enumerate(vals)]
            cr.set_source_rgba(*color)
            cr.set_line_width(width)
            cr.move_to(*pts[0])
            for p in pts[1:]:
                cr.line_to(*p)
            cr.stroke()
            k = vals.index(max(vals))
            return pts, k
        # a faint middle line for scale
        cr.set_source_rgba(1, 1, 1, 0.07)
        cr.set_line_width(1)
        cr.set_dash([2, 3])
        cr.move_to(0, h / 2)
        cr.line_to(w, h / 2)
        cr.stroke()
        cr.set_dash([])
        sky, mauve = (0.561, 0.839, 0.925, 1), (0.788, 0.714, 0.949, 0.95)
        dp, dk = line(t.down, sky, 1.8)
        up, uk = line(t.up, mauve, 1.5)
        for (x, y), col, r in ((dp[dk], (0.95, 0.95, 0.94, 1), 2.6), (up[uk], mauve, 2.3)):
            cr.set_source_rgba(*col)
            cr.arc(x, y, r, 0, 2 * math.pi)
            cr.fill()
        x, y = dp[-1]
        cr.set_source_rgba(*sky)
        cr.arc(x - 3, y, 3, 0, 2 * math.pi)
        cr.fill()


class BtSquare(Square):
    """The device that matters: one at 20% or less (the lowest), else the
    one connected most recently. Buds: Left and Right big and light, one
    line split by their charge, the case under them, and what's charging.
    Anything else: its one battery. The rest as "+N more" (opens setu)."""

    def __init__(self, plugin, tile):
        super().__init__(plugin, tile, "blue")
        self.add_css_class("bt")
        self.more = Gtk.Button(label="")
        self.more.add_css_class("k-more")
        self.more.connect("clicked", lambda *_: self.open_details())
        self.more.set_can_focus(False)
        self.more.set_visible(False)
        self.extra.append(self.more)
        head = Gtk.Box(spacing=6)
        self.name = ui.label("", "k-sq-name", xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        self.low = ui.label("low", "k-lowtag")
        self.low.set_visible(False)
        head.append(self.name)
        head.append(self.low)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        # like the Wi-Fi square: the facts sit on the bottom line, the space
        # between them and the header
        self.body.set_valign(Gtk.Align.END)
        self.body.append(head)
        self.body.append(self.content)

    def clear(self):
        c = self.content.get_first_child()
        while c is not None:
            n = c.get_next_sibling()
            self.content.remove(c)
            c = n

    def show_state(self, on, devs, pick):
        self.show_on(on)
        self.clear()
        others = [d for d in devs if d is not pick]
        self.more.set_label(f"+{len(others)} more")
        self.more.set_visible(bool(others) and on)
        self.more.set_tooltip_text(", ".join(d["name"] for d in others) + " (opens setu)")
        self.low.set_visible(False)
        self.remove_css_class("is-low")
        if not on:
            self.name.set_label("Off")
            self.sub = "Off"
            self.content.append(ui.label("Turn it on with the circle", "k-quiet", xalign=0))
            return
        if pick is None:
            self.name.set_label("Nothing connected")
            self.sub = "On · nothing connected"
            self.content.append(ui.label("Right click to pick a device", "k-quiet", xalign=0))
            return
        self.name.set_label(pick["name"])
        parts = pick.get("parts") or {}
        charging = [k for k, p in parts.items() if p.get("charging")]
        if parts.get("Left") is not None or parts.get("Right") is not None:
            self.buds(parts)
            self.sub = f"{pick['name']} · L {self.pv(parts, 'Left')} · R {self.pv(parts, 'Right')}" + \
                       (f" · case {self.pv(parts, 'Case')}" if parts.get("Case") else "")
        elif pick.get("battery") is not None:
            self.single(pick)
            self.sub = f"{pick['name']} · {pick['battery']}%"
        else:
            self.content.append(ui.label(system.KINDS.get(pick.get("icon", ""), "Connected"), "k-quiet", xalign=0))
            self.sub = pick["name"]
        if charging:
            self.content.append(ui.label("⚡ charging", "k-charging", xalign=0))
            self.sub += " · charging"
        if others:
            self.sub += f" · +{len(others)} more"

    @staticmethod
    def pv(parts, k):
        p = parts.get(k)
        return f"{p['level']}%" if p and p.get("level") is not None else "—"

    def buds(self, parts):
        row = Gtk.Box(spacing=14)
        for i, k in enumerate(("Left", "Right")):
            if i:
                sep = Gtk.Box()
                sep.add_css_class("k-sep")
                row.append(sep)
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            p = parts.get(k) or {}
            lvl = p.get("level")
            col.append(ui.label("—" if lvl is None else str(lvl), "k-typo", xalign=0))
            col.append(ui.label(k, "k-typo-name", xalign=0))
            row.append(col)
        self.content.append(row)
        duo = Gtk.Box(spacing=4, homogeneous=False)
        duo.add_css_class("k-duo")
        for k in ("Left", "Right"):
            lvl = (parts.get(k) or {}).get("level") or 0
            bar = ui.progress(lvl / 100, "green" if lvl > 20 else "red")
            bar.set_hexpand(True)
            duo.append(bar)
        self.content.append(duo)
        case = parts.get("Case") or {}
        if case.get("level") is None:      # not heard yet: the row stays, with a dash
            cr = Gtk.Box(spacing=8)
            cr.add_css_class("k-case")
            cr.append(ui.label("Case", "k-quiet"))
            bar = ui.progress(0, "gray")
            bar.set_hexpand(True)
            bar.set_valign(Gtk.Align.CENTER)
            cr.append(bar)
            cr.append(ui.label("—", "k-case-v", "k-quiet"))
            cr.set_tooltip_text("The case reports its battery while the buds are in it, or it's open")
            self.content.append(cr)
        else:
            cr = Gtk.Box(spacing=8)
            cr.add_css_class("k-case")
            cr.append(ui.label("Case" + (" · " + case["age"] if case.get("age") else ""), "k-quiet"))
            bar = ui.progress(case["level"] / 100, "gray")
            bar.set_hexpand(True)
            bar.set_valign(Gtk.Align.CENTER)
            cr.append(bar)
            cr.append(ui.label(f"{case['level']}%", "k-case-v"))
            self.content.append(cr)

    def single(self, d):
        lvl = d["battery"]
        low = lvl <= 20
        big = Gtk.Box(spacing=2)
        big.append(ui.label(str(lvl), "k-typo", *(["k-red"] if low else []), valign=Gtk.Align.BASELINE))
        big.append(ui.label("%", "k-typo-unit", *(["k-red"] if low else []), valign=Gtk.Align.BASELINE))
        self.content.append(big)
        bar = ui.progress(lvl / 100, "red" if low else "green")
        self.content.append(bar)
        if low:
            self.low.set_visible(True)
            self.add_css_class("is-low")
            self.content.append(ui.label("Plug it in soon", "k-red-note", xalign=0))


# ------------------------------------------------------------- header
class BatteryRing(Gtk.DrawingArea):
    """Your initial on the accent, inside a ring that is the battery."""

    def __init__(self, letter):
        super().__init__(content_width=38, content_height=38, valign=Gtk.Align.CENTER)
        self.add_css_class("k-ring")
        self.letter, self.pct, self.color = letter, None, (0.557, 0.886, 0.651)
        self.set_draw_func(self.draw)

    def set(self, pct, charging):
        self.pct = pct
        self.color = (0.557, 0.886, 0.651) if charging or (pct or 0) > 30 else \
            (0.953, 0.831, 0.498) if (pct or 0) > 15 else (1, 0.576, 0.537)
        self.queue_draw()

    def draw(self, area, cr, w, h):
        cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 2.5
        cr.set_line_width(3.2)
        cr.set_source_rgba(1, 1, 1, 0.12)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        if self.pct is not None:
            cr.set_source_rgb(*self.color)
            cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * self.pct / 100)
            cr.stroke()
        cr.set_source_rgba(*rgba(self))
        cr.arc(cx, cy, r - 4.5, 0, 2 * math.pi)
        cr.fill()
        layout = self.create_pango_layout(self.letter)
        layout.set_font_description(Pango.FontDescription.from_string("Adwaita Sans Heavy 13px"))
        ink, _ = layout.get_pixel_extents()
        cr.set_source_rgb(0.055, 0.059, 0.067)
        cr.move_to(cx - ink.width / 2 - ink.x, cy - ink.height / 2 - ink.y)
        PangoCairo.show_layout(cr, layout)


# ------------------------------------------------------------- wallpaper
class WallpaperPill(Gtk.Button, Hoverable):
    """The wallpaper you're on, as a pill with its name; click for a new one."""

    def __init__(self, plugin, tile):
        super().__init__(hexpand=True)
        self.plugin, self.tile = plugin, tile
        self.add_css_class("k-wall")
        self.set_overflow(Gtk.Overflow.HIDDEN)
        over = Gtk.Overlay()
        self.pic = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.pic.set_draw_func(self.draw_pic)
        self.pixbuf = None
        over.set_child(self.pic)
        shade = Gtk.Box()
        shade.add_css_class("k-wall-shade")
        over.add_overlay(shade)
        row = Gtk.Box(spacing=8, margin_start=16, margin_end=8)
        self.title = ui.label("", "k-wall-name", xalign=0, hexpand=True, valign=Gtk.Align.CENTER,
                              ellipsize=Pango.EllipsizeMode.END)
        row.append(self.title)
        rf = Gtk.Box(valign=Gtk.Align.CENTER)
        rf.add_css_class("k-wall-refresh")
        rf.append(glyph(REFRESH, 28))
        row.append(rf)
        over.add_overlay(row)
        self.set_child(over)
        self.path, self.mtime = None, None
        self.connect("clicked", lambda *_: self.fetch())
        self.say_on(self, plugin, lambda: f"<b>Wallpaper</b>  {GLib.markup_escape_text(self.title.get_label())}  · click: a new one")

    def refresh(self):
        def load():
            path = system.wallpaper_image(self.plugin.conf.get("tile", {}).get("wallpaper", {}))
            if not path:
                return None
            try:
                mt = __import__("os").stat(path).st_mtime
            except OSError:
                return None
            if (path, mt) == (self.path, self.mtime):
                return "same"
            px = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 640, -1, True)
            return path, mt, px

        def show(r):
            if r in (None, "same") or not isinstance(r, tuple):
                return
            self.path, self.mtime, self.pixbuf = r
            self.pic.queue_draw()
            self.title.set_label(system.wallpaper_name(self.path))
        self.plugin.background(load, then=show)

    def draw_pic(self, area, cr, w, h):
        px = self.pixbuf
        if px is None:
            return
        sc = max(w / px.get_width(), h / px.get_height())
        cr.translate((w - px.get_width() * sc) / 2, (h - px.get_height() * sc) * 0.6)
        cr.scale(sc, sc)
        Gdk.cairo_set_source_pixbuf(cr, px, 0, 0)
        cr.paint()

    def fetch(self):
        self.title.set_label("Fetching a new one…")
        self.plugin.background(lambda: self.tile.toggle(True))
        # the fetch runs on its own; look for the new picture for a while
        tries = [0]

        def look():
            tries[0] += 1
            self.refresh()
            return tries[0] < 20
        GLib.timeout_add_seconds(2, look)
