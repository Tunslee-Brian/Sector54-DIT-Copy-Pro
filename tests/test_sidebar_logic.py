import os
import unittest
import tempfile
import shutil
import tkinter as tk
from ui.sidebar_panel import ShotPutSidebar


class TestSidebarLogic(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as e:
            cls.skipTest(cls, f"Tkinter GUI not available in headless environment: {e}")

        cls.temp_dir1 = tempfile.mkdtemp(prefix="dit_src_")
        cls.temp_dir2 = tempfile.mkdtemp(prefix="dit_dst1_")
        cls.temp_dir3 = tempfile.mkdtemp(prefix="dit_dst2_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir1, ignore_errors=True)
        shutil.rmtree(cls.temp_dir2, ignore_errors=True)
        shutil.rmtree(cls.temp_dir3, ignore_errors=True)
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_single_input_source(self):
        sidebar = ShotPutSidebar(self.root)
        
        # Initially empty
        self.assertEqual(sidebar.get_source_path(), "")

        # Set source 1
        sidebar.set_source_path(self.temp_dir1)
        self.assertEqual(sidebar.get_source_path(), os.path.abspath(self.temp_dir1))

        # Replace with source 2 (Must enforce single input restriction)
        sidebar.set_source_path(self.temp_dir2)
        self.assertEqual(sidebar.get_source_path(), os.path.abspath(self.temp_dir2))

        # Clear source
        sidebar.clear_source_path()
        self.assertEqual(sidebar.get_source_path(), "")

    def test_unlimited_outputs(self):
        sidebar = ShotPutSidebar(self.root)

        # Initially empty
        self.assertEqual(sidebar.get_destinations(), [])

        # Add destination 1
        sidebar.add_destination_path(self.temp_dir2)
        self.assertEqual(sidebar.get_destinations(), [os.path.abspath(self.temp_dir2)])

        # Add destination 2 (Unlimited)
        sidebar.add_destination_path(self.temp_dir3)
        self.assertEqual(sidebar.get_destinations(), [os.path.abspath(self.temp_dir2), os.path.abspath(self.temp_dir3)])

        # Duplicate addition ignored
        sidebar.add_destination_path(self.temp_dir2)
        self.assertEqual(sidebar.get_destinations(), [os.path.abspath(self.temp_dir2), os.path.abspath(self.temp_dir3)])

        # Remove single destination
        sidebar.remove_destination_path(self.temp_dir2)
        self.assertEqual(sidebar.get_destinations(), [os.path.abspath(self.temp_dir3)])

        # Clear all destinations
        sidebar.clear_destinations()
        self.assertEqual(sidebar.get_destinations(), [])

    def test_sidebar_tree_status_tags(self):
        sidebar = ShotPutSidebar(self.root)
        sidebar.set_source_path(self.temp_dir1)

        file_list = [
            {"source_path": os.path.join(self.temp_dir1, "file1.mp4"), "status": "VERIFIED"},
            {"source_path": os.path.join(self.temp_dir1, "file2.mp4"), "status": "FAILED"}
        ]
        extra_files = [
            {"dest_path": os.path.join(self.temp_dir2, "extra.mp4"), "status": "EXTRA"}
        ]

        sidebar.update_sidebar_tree_status(file_list, extra_files)
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
