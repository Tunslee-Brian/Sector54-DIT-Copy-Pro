import unittest
import customtkinter as ctk
from ui.config_panel import ConfigPanel

class TestConfigPreview(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_sample_filename_generation(self):
        panel = ConfigPanel(self.root)
        pattern = "{Camera:1}{Roll:3}C{Clip:3}_{Date:8}"

        sample1 = panel._generate_sample_filename(pattern, 1)
        sample2 = panel._generate_sample_filename(pattern, 2)
        sample3 = panel._generate_sample_filename(pattern, 3)

        self.assertTrue(sample1.startswith("A001C001_"))
        self.assertTrue(sample2.startswith("A001C002_"))
        self.assertTrue(sample3.startswith("B001C003_"))
        self.assertTrue(sample1.endswith(".MOV"))

    def test_token_explanations(self):
        panel = ConfigPanel(self.root)
        pattern = "{Camera:1}{Roll:3}C{Clip:3}_{Date:8}"

        explanations = panel._get_token_explanations(pattern)
        titles = [t[0] for t in explanations]

        self.assertTrue(any("Camera" in t for t in titles))
        self.assertTrue(any("Roll" in t for t in titles))
        self.assertTrue(any("Clip" in t for t in titles))
        self.assertTrue(any("Date" in t for t in titles))

    def test_destination_update(self):
        panel = ConfigPanel(self.root)
        dest_path = "/Volumes/RAID_STORAGE_TEST"
        panel.set_destinations([dest_path])

        self.assertEqual(panel.destinations, [dest_path])
        self.assertIn("RAID_STORAGE_TEST", panel.lbl_dest_status.cget("text"))

    def test_date_format_selection(self):
        panel = ConfigPanel(self.root)
        panel.set_date_format("DDMMYY")
        self.assertEqual(panel._get_selected_date_format(), "DDMMYY")

        config = panel.get_config()
        self.assertEqual(config["date_format"], "DDMMYY")

    def test_visual_token_chips(self):
        panel = ConfigPanel(self.root)
        panel._apply_quick_pattern("{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}")
        self.assertEqual(panel.entry_naming.get(), "{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}")

        panel._add_token_to_naming("_Test")
        self.assertTrue(panel.entry_naming.get().endswith("_Test"))

if __name__ == "__main__":
    unittest.main()
