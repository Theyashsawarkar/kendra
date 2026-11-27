"""The bento's pure helpers: which Bluetooth device shows, names, rates."""
import unittest

from kendra import system


class PickDevice(unittest.TestCase):
    def test_low_one_wins(self):
        devs = [{"mac": "A", "low": 82}, {"mac": "B", "low": 12}, {"mac": "C", "low": 18}]
        self.assertEqual(system.pick_device(devs, {"A": 9})["mac"], "B")

    def test_else_most_recent(self):
        devs = [{"mac": "A", "low": 82}, {"mac": "B", "low": 64}]
        self.assertEqual(system.pick_device(devs, {"A": 5, "B": 9})["mac"], "B")

    def test_no_battery_known(self):
        devs = [{"mac": "A", "low": None}]
        self.assertEqual(system.pick_device(devs, {})["mac"], "A")

    def test_none(self):
        self.assertIsNone(system.pick_device([], {}))


class Traffic(unittest.TestCase):
    def test_load_takes_the_last_minute(self):
        t = system.Traffic()
        t.load({"rx": list(range(40)), "tx": [1.0] * 40})
        self.assertEqual(len(t.down), t.keep)
        self.assertEqual(t.down[-1], 39)
        t.load({"rx": [], "tx": []})
        self.assertEqual(t.down, [])


class Words(unittest.TestCase):
    def test_wallpaper_name(self):
        self.assertEqual(system.wallpaper_name("/w/wallpaper-20261126-RFHilo.jpg"), "RF Hilo")
        self.assertEqual(system.wallpaper_name("/w/wallpaper-20261125-TrailCedars.jpg"), "Trail Cedars")
        self.assertEqual(system.wallpaper_name("Trail_Cedars.png"), "Trail Cedars")

    def test_rate(self):
        self.assertEqual(system.rate(12_400_000), ("12.4", "MB/s"))
        self.assertEqual(system.rate(4_200), ("4", "kB/s"))
        self.assertEqual(system.rate(900), ("900", "B/s"))

    def test_signal_word(self):
        self.assertEqual(system.signal_word(80), (4, "Excellent"))
        self.assertEqual(system.signal_word(20), (1, "Weak"))

    def test_colour_codes_stripped(self):
        self.assertEqual(system.run("printf '\\033[1;30mDevice AA Buds\\033[0m'")[1], "Device AA Buds")


if __name__ == "__main__":
    unittest.main()
