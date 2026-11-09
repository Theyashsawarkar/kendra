"""kendra's vim keys, as data. A card: always NORMAL (nothing to type).
h / j / k / l move through the tile grid and down into the sliders (by
where things are on screen, so h / l never jump rows); on a slider h / l
change it by 5 (a count first: 3l is +15) and 0 / $ go to its ends.
Enter toggles the focused tile (on a slider: mute). Space is the leader
and never toggles a tile. Space groups follow Vayu's shared letters
(g go to, r refresh); l (lock) and p (power menu) are kendra's own.

An action "verb:arg" runs Plugin.v_<verb>(count, arg) in kendra/__init__.py,
or Vyom's own (moved, nop...).
"""
from vyom.keys import Bind

B = Bind
CARD = True
GROUPS = {" g": "go to"}


def moved(seq, to):
    """An old key that moved in v0.4 (for one release): says where to."""
    return B(seq, f"moved:{to}", "", hidden=True)


NORMAL = [
    B("h", "move:left", "Move left in the tiles (on a slider: lower it by 5)"),
    B("l", "move:right", "Move right in the tiles (on a slider: raise it by 5)"),
    B("j", "move:down", "Move down (from the tiles into the sliders)"),
    B("k", "move:up", "Move up"),
    B("<Left>", "move:left", "", hidden=True), B("<Right>", "move:right", "", hidden=True),
    B("<Down>", "move:down", "", hidden=True), B("<Up>", "move:up", "", hidden=True),
    B("gg", "top", "Jump to the first tile"),
    B("G", "bottom", "Jump to the last control (the bottom slider)"),
    B("0", "ends:min", "Set the focused slider to its minimum"),
    B("$", "ends:max", "Set the focused slider to its maximum"),
    B("<CR>", "enter", "Toggle the focused setting (on a slider: mute it)"),
    B("o", "details", "Open the focused tile's details (Wi-Fi in tarang, Bluetooth in setu)"),
    B("m", "mute", "Toggle mute on the sound output"),
    B("p", "power", "", hidden=True),          # kept: p isn't a vim key
    moved("L", "Space l"),
]

LEADER = [
    B(" l", "lock", "Lock the screen"),
    B(" p", "power", "Open the power menu"),
    B(" gw", "goto:tarang", "Open the Wi-Fi panel (tarang)"),
    B(" gb", "goto:setu", "Open the Bluetooth panel (setu)"),
    B(" gh", "goto:tarang:hotspot", "Open the hotspot (tarang's Hotspot tab)"),
    B(" gp", "goto:vishram", "Open the power menu (vishram)"),
    B(" ga", "goto:urja", "Open the battery panel (urja)"),
    B(" r", "refresh", "Reload every tile and slider"),
]

SECTIONS = [
    ("quick settings", "normal", "Keys (it's always in NORMAL mode: there's nothing to type)", NORMAL),
    ("quick settings leader", "normal", "Leader (Space)", LEADER),
    ("quick settings", "any", "Both", [B("<S-CR>", "nop", "Open the focused setting's details (same as o)")]),
]


def keys(_tab):
    return NORMAL + LEADER
