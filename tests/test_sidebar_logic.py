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
            raise unittest.SkipTest(f"Tkinter GUI not available in headless environment: {e}")

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

        f1 = os.path.join(self.temp_dir1, "file1.mp4")
        f2 = os.path.join(self.temp_dir1, "file2.mp4")
        extra_file = os.path.join(self.temp_dir2, "extra.mp4")

        file_list = [
            {"source_path": f1, "status": "VERIFIED"},
            {"source_path": f2, "status": "FAILED"}
        ]
        extra_files = [
            {"dest_path": extra_file, "status": "EXTRA"}
        ]

        sidebar.update_sidebar_tree_status(file_list, extra_files)
        
        # Verify status mappings exist in tree status dictionary
        norm_f1 = os.path.normpath(f1)
        norm_f2 = os.path.normpath(f2)
        self.assertIn(norm_f1, sidebar.tree_input._current_status_dict)
        self.assertEqual(sidebar.tree_input._current_status_dict[norm_f1], "VERIFIED")
        self.assertEqual(sidebar.tree_input._current_status_dict[norm_f2], "FAILED")

    def test_external_drag_and_drop(self):
        sidebar = ShotPutSidebar(self.root)
        
        class MockEvent:
            def __init__(self, data):
                self.data = data
        
        path_with_space = os.path.join(self.temp_dir1, "sub folder")
        os.makedirs(path_with_space, exist_ok=True)
        
        # Test drop input
        event = MockEvent(f"{{{path_with_space}}}")
        sidebar._on_external_drop_input(event)
        self.assertEqual(sidebar.get_source_path(), os.path.abspath(path_with_space))
        
        # Test drop multiple outputs
        event_out = MockEvent(f"{{{self.temp_dir2}}} {{{self.temp_dir3}}}")
        sidebar._on_external_drop_output(event_out)
        self.assertEqual(
            sidebar.get_destinations(),
            [os.path.abspath(self.temp_dir2), os.path.abspath(self.temp_dir3)]
        )


if __name__ == "__main__":
    unittest.main()
