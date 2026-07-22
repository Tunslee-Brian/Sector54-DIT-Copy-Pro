import os
import unittest
import tempfile
import shutil
from core.preset_manager import PresetManager


class TestPresetManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="dit_preset_test_")
        self.preset_mgr = PresetManager(preset_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_load_delete_preset(self):
        preset_data = {
            "name": "Test Preset 123",
            "naming_rule": "{Camera:1}{Roll:3}",
            "folder_template": "{Destination}/Footage/",
            "hash_algorithm": "MD5",
            "log_format": "TXT",
            "buffer_size_mb": 64
        }

        # Save preset
        saved = self.preset_mgr.save_preset(preset_data)
        self.assertTrue(saved)
        self.assertIn("Test Preset 123", self.preset_mgr.list_presets())

        # Load preset
        loaded = self.preset_mgr.load_preset("Test Preset 123")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.get("name"), "Test Preset 123")

        # Delete preset
        deleted = self.preset_mgr.delete_preset("Test Preset 123")
        self.assertTrue(deleted)
        self.assertNotIn("Test Preset 123", self.preset_mgr.list_presets())

    def test_deleted_preset_not_recreated_on_restart(self):
        # Default presets are initialized in setUp
        presets = self.preset_mgr.list_presets()
        self.assertTrue(len(presets) > 0)
        target = presets[0]

        # Delete default preset
        self.preset_mgr.delete_preset(target)
        self.assertNotIn(target, self.preset_mgr.list_presets())

        # Re-instantiate PresetManager targeting same directory (simulating app restart)
        new_pm = PresetManager(preset_dir=self.temp_dir)
        self.assertNotIn(target, new_pm.list_presets())

    def test_rename_and_description_preset(self):
        preset_data = {
            "name": "Original Name",
            "description": "Original description for camera A",
            "naming_rule": "{Camera:1}{Roll:3}",
            "folder_template": "{Destination}/Footage/",
            "hash_algorithm": "MD5",
            "log_format": "TXT",
            "buffer_size_mb": 64
        }
        self.preset_mgr.save_preset(preset_data)

        # Rename preset
        preset_data["name"] = "Renamed Name"
        preset_data["description"] = "Updated description"
        saved = self.preset_mgr.save_preset(preset_data, old_name="Original Name")
        self.assertTrue(saved)
        self.assertNotIn("Original Name", self.preset_mgr.list_presets())
        self.assertIn("Renamed Name", self.preset_mgr.list_presets())

        loaded = self.preset_mgr.load_preset("Renamed Name")
        self.assertEqual(loaded.get("description"), "Updated description")

    def test_export_and_import_preset(self):
        preset_data = {
            "name": "Export Import Test Preset",
            "description": "Export and Import test preset",
            "naming_rule": "{Camera:1}{Roll:3}",
            "folder_template": "{Destination}/Footage/",
            "hash_algorithm": "MD5",
            "buffer_size_mb": 64
        }
        self.preset_mgr.save_preset(preset_data)

        export_dir = tempfile.mkdtemp(prefix="dit_export_test_")
        export_file = os.path.join(export_dir, "custom_export.json")

        try:
            # Test Export
            exported = self.preset_mgr.export_preset("Export Import Test Preset", export_file)
            self.assertTrue(exported)
            self.assertTrue(os.path.exists(export_file))

            # Test Import in a new manager
            new_temp = tempfile.mkdtemp(prefix="dit_import_test_")
            try:
                new_pm = PresetManager(preset_dir=new_temp)
                imported = new_pm.import_preset(export_file)
                self.assertIsNotNone(imported)
                self.assertEqual(imported["name"], "Export Import Test Preset")
                self.assertIn("Export Import Test Preset", new_pm.list_presets())
            finally:
                shutil.rmtree(new_temp, ignore_errors=True)
        finally:
            shutil.rmtree(export_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

