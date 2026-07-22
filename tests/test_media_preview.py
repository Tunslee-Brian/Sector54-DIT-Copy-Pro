import os
import unittest
import tempfile
import shutil
import tkinter as tk
from ui.app import DITCopyProApp
from ui.media_preview_widget import is_media_file, get_media_category


class TestMediaPreview(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="dit_preview_test_")
        cls.test_image = os.path.join(cls.temp_dir, "test_clip.png")
        cls.test_audio = os.path.join(cls.temp_dir, "sample.mp3")

        # Create dummy media files
        with open(cls.test_image, "w") as f:
            f.write("dummy image content")
        with open(cls.test_audio, "w") as f:
            f.write("dummy audio content")

        try:
            cls.app = DITCopyProApp()
            cls.app.withdraw()
        except Exception as e:
            cls.skipTest(cls, f"Tkinter GUI not available: {e}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        if hasattr(cls, "app") and cls.app:
            try:
                cls.app.destroy()
            except Exception:
                pass

    def test_media_file_detection(self):
        self.assertTrue(is_media_file("sample.mp4"))
        self.assertTrue(is_media_file("sample.jpg"))
        self.assertTrue(is_media_file("sample.mp3"))
        self.assertTrue(is_media_file("sample.txt"))

        self.assertEqual(get_media_category("sample.jpg"), "IMAGE")
        self.assertEqual(get_media_category("sample.mp3"), "AUDIO")
        self.assertEqual(get_media_category("sample.mp4"), "VIDEO")
        self.assertEqual(get_media_category("sample.txt"), "DOCUMENT")

    def test_fixed_single_preview_tab(self):
        app = self.app

        # 1. Click sidebar media file -> loads file into permanent preview panel
        app._on_sidebar_media_file_selected(self.test_image)

        abs_img_path = os.path.abspath(self.test_image)
        self.assertEqual(app.preview_panel.filepath, abs_img_path)
        self.assertEqual(app.preview_panel.category, "IMAGE")

        # 2. Click another media file -> reloads single preview panel
        app._on_sidebar_media_file_selected(self.test_audio)
        abs_audio_path = os.path.abspath(self.test_audio)
        self.assertEqual(app.preview_panel.filepath, abs_audio_path)
        self.assertEqual(app.preview_panel.category, "AUDIO")

        # 3. Switch away to another tab -> clears preview data
        app._on_tab_changed("Job Flow Diagram")
        self.assertEqual(app.preview_panel.filepath, "")
        self.assertEqual(app.preview_panel.category, "NONE")


if __name__ == "__main__":
    unittest.main()
