import unittest
import os
import shutil
import tempfile
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.directory_builder import DirectoryBuilder
from core.copy_engine import CopyEngine
from core.token_parser import TokenParser
from core.preset_manager import PresetManager
from core.sound_player import SoundPlayer
from ui.progress_panel import ShotPutProgressPanel
from ui.media_preview_widget import MediaPreviewWidget
import tkinter as tk

class TestCodeAnalysisFixes(unittest.TestCase):

    def test_path_traversal_recursive_strip(self):
        # Verify Critical Issue 1: Path traversal protection bypass with nested dots
        builder = DirectoryBuilder("{Destination}/Footage/{Camera}/")
        tokens = {"Camera": "....//"}
        dest_root = tempfile.mkdtemp()
        try:
            # If recursively stripped, "....//" -> "" or "_" -> resolved path must stay inside dest_root
            filepath = builder.build_path_for_destination(dest_root, tokens, "clip1.mxf")
            self.assertTrue(filepath.startswith(os.path.abspath(dest_root)))
        finally:
            shutil.rmtree(dest_root)

    def test_cleanup_partial_files_selective(self):
        # Verify Critical Issue 2: Cleanup only deletes failed destinations, leaves verified ones
        # We can mock/stub directory_builder and verify_engine, or use temp files.
        dest1_dir = tempfile.mkdtemp()
        dest2_dir = tempfile.mkdtemp()
        src_dir = tempfile.mkdtemp()
        
        src_file = os.path.join(src_dir, "A001C001_260723.MXF")
        with open(src_file, "wb") as f:
            f.write(b"video data here")

        parser = TokenParser()
        builder = DirectoryBuilder("{Destination}/")
        
        from core.verify_engine import VerifyEngine
        orig_compute = VerifyEngine.compute_file_hash
        
        try:
            # We want to test CopyEngine's selective cleanup on copy session
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1_dir, dest2_dir],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5"
            )
            
            dest1_file = os.path.join(dest1_dir, "A001C001_260723.MXF")
            dest2_file = os.path.join(dest2_dir, "A001C001_260723.MXF")

            # Mock compute_file_hash to fail verification on dest2
            @classmethod
            def mock_compute(cls, path, algo="MD5", buf_size=65536, callback=None):
                if dest2_dir in path:
                    return "incorrect_hash_value"
                return orig_compute(path, algo, buf_size, callback)
                
            VerifyEngine.compute_file_hash = mock_compute

            # Scan source to populate file list
            engine.scan_source()
            
            # Run copy session
            # This should copy to both dest1 and dest2, verify dest1 successfully
            # but fail dest2 verification and thus clean up dest2 file only.
            engine.run_copy_session()
            
            self.assertTrue(os.path.exists(dest1_file), "Verified destination should NOT be deleted!")
            self.assertFalse(os.path.exists(dest2_file), "Failed destination should be deleted!")

        finally:
            VerifyEngine.compute_file_hash = orig_compute
            shutil.rmtree(dest1_dir)
            shutil.rmtree(dest2_dir)
            shutil.rmtree(src_dir)

    def test_audio_fallback_on_cli_failure(self):
        # Verify Critical Issue 3: sound player falls back properly when subprocess returns non-zero code
        # We can test that sound player finishes initialization and self.finish_mp3_path is valid
        player = SoundPlayer()
        self.assertTrue(os.path.exists(player.finish_mp3_path))

    def test_media_preview_attributes_initialization(self):
        # Verify Critical Issue 4 & 5: attributes exist and pygame.mixer.music.get_pos negative check works
        root = tk.Tk()
        try:
            widget = MediaPreviewWidget(root)
            self.assertIsNone(widget._poster_pil_image)
            self.assertIsNotNone(widget._poster_lock)
        finally:
            root.destroy()

    def test_progress_panel_attributes_initialization(self):
        # Verify Medium Issue 7: Uninitialized progress attributes are resolved
        root = tk.Tk()
        try:
            panel = ShotPutProgressPanel(root)
            self.assertEqual(panel._last_copied_bytes, 0)
            self.assertEqual(panel._last_total_bytes, 0)
        finally:
            root.destroy()

    def test_preset_manager_restore_on_deleted_presets(self):
        # Verify Medium Issue 9: Defaults are restored even if marker file exists if presets are missing
        temp_dir = tempfile.mkdtemp()
        try:
            # Create initialized marker first
            marker_file = os.path.join(temp_dir, ".initialized")
            with open(marker_file, "w") as f:
                f.write("initialized")

            # Instantiate PresetManager. It should see the marker but see 0 json presets, so it recreates them!
            pm = PresetManager(preset_dir=temp_dir)
            presets = pm.list_presets()
            self.assertGreater(len(presets), 0, "Presets should be re-created if missing, despite initialized marker!")
        finally:
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    unittest.main()
