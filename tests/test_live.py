"""kendra.live: Vyom's live-state snapshots turned into what the tiles take."""
import unittest

from kendra import live


class Conversions(unittest.TestCase):
    def test_wifi(self):
        self.assertIsNone(live.wifi(None))
        self.assertIsNone(live.wifi({"running": False}))
        snap = {"running": True, "device": "wlan0", "enabled": True, "wired": "",
                "active": {"ssid": "Demo Cafe", "strength": 64}}
        self.assertEqual(live.wifi(snap), (True, "Demo Cafe", 64))
        self.assertEqual(live.wifi({**snap, "enabled": False}), (False, "Off", None))
        self.assertEqual(live.wifi({**snap, "active": None, "wired": "Wired 1"})[1], "On · ethernet in use")

    def test_bluetooth(self):
        snap = {"running": True, "adapter": {"powered": True}, "devices": [
            {"mac": "AA:BB:CC:DD:EE:01", "alias": "Demo Buds", "icon": "audio-headset", "connected": True, "battery": 80},
            {"mac": "AA:BB:CC:DD:EE:02", "name": "Demo Mouse", "connected": False}]}
        on, devs = live.bluetooth(snap)
        self.assertTrue(on)
        self.assertEqual([d["name"] for d in devs], ["Demo Buds"])
        self.assertEqual(live.bluetooth({**snap, "adapter": {"powered": False}}), (False, []))

    def test_upower_batteries_needs_two(self):
        snap = {"running": True, "devices": [
            {"native_path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_01", "type": "headphones", "model": "L", "percentage": 70},
            {"native_path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_01", "type": "headphones", "model": "R", "percentage": 60},
            {"native_path": "BAT0", "type": "battery", "percentage": 90}]}
        out = live.upower_batteries(snap)
        self.assertEqual(out, {"AA:BB:CC:DD:EE:01": [("Headphones l", 70), ("Headphones r", 60)]})

    def test_power_and_sliders(self):
        self.assertEqual(live.power({"profiles": ["balanced", "performance"], "active": "balanced"})[1], "balanced")
        self.assertIsNone(live.power({"profiles": []}))
        self.assertEqual(live.volume({"volume": 40, "muted": True, "device": "Demo"}), ((40, True), "Demo"))
        self.assertEqual(live.brightness({"percent": 55}), ((55, False), ""))

    def test_text_from_a_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("high\n")
        self.assertEqual(live.text(f"file:{f.name}", None), "high")
        self.assertIsNone(live.text("nonsense", None))


if __name__ == "__main__":
    unittest.main()


class Connections(unittest.TestCase):
    def test_primary_first_hotspot_out_older_vyom_none(self):
        snap = {"running": True, "connections": [
            {"name": "Home", "type": "wifi"}, {"name": "Office VPN", "type": "vpn", "primary": True},
            {"name": "Vayu Hotspot", "type": "hotspot"}]}
        self.assertEqual([c["name"] for c in live.connections(snap)], ["Office VPN", "Home"])
        self.assertIsNone(live.connections({"running": True, "wired": "Wired connection 1"}))
        self.assertIsNone(live.connections(None))
