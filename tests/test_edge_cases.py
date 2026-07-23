import unittest
import os
import shutil
import tempfile
import sys
import html

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.directory_builder import DirectoryBuilder
from core.copy_engine import CopyEngine
from core.token_parser import TokenParser
from core.report_generator import ReportGenerator

class TestEdgeCases(unittest.TestCase):

    def test_unicode_filenames(self):
        """Test scanning and copying files with Unicode/non-ASCII characters."""
        src_dir = tempfile.mkdtemp()
        dest_dir = tempfile.mkdtemp()
        try:
            unicode_name = "Phim_Điện_Ảnh_🎥_A001C001.mxf"
            src_file = os.path.join(src_dir, unicode_name)
            with open(src_file, "wb") as f:
                f.write(b"unicode video content")

            parser = TokenParser()
            builder = DirectoryBuilder("{Destination}/Footage/")
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest_dir],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="Size-only"
            )

            file_list = engine.scan_source()
            self.assertEqual(len(file_list), 1)
            self.assertEqual(file_list[0]["filename"], unicode_name)

            # Run copy session
            summary = engine.run_copy_session()
            self.assertEqual(summary["verified"], 1)
            self.assertEqual(summary["failed"], 0)

            # Check that copy exists
            copied_file = os.path.join(dest_dir, "Footage", unicode_name)
            self.assertTrue(os.path.exists(copied_file))
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest_dir)

    def test_path_traversal_in_template(self):
        """Test that path traversal inside the folder template raises ValueError."""
        dest_root = tempfile.mkdtemp()
        builder = DirectoryBuilder("{Destination}/../outside/")
        try:
            with self.assertRaises(ValueError):
                builder.build_path_for_destination(dest_root, {}, "clip.mxf")
        finally:
            shutil.rmtree(dest_root)

    def test_empty_source_directory(self):
        """Test scanning and executing copy sessions on empty source directory."""
        src_dir = tempfile.mkdtemp()
        dest_dir = tempfile.mkdtemp()
        try:
            parser = TokenParser()
            builder = DirectoryBuilder("{Destination}/")
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest_dir],
                token_parser=parser,
                directory_builder=builder
            )
            file_list = engine.scan_source()
            self.assertEqual(len(file_list), 0)

            summary = engine.run_copy_session()
            self.assertEqual(summary["total_files"], 0)
            self.assertEqual(summary["verified"], 0)
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest_dir)

    def test_check_free_space_permission_denied(self):
        """Test check_free_space behavior when a destination path raises permission errors."""
        src_dir = tempfile.mkdtemp()
        forbidden_dir = tempfile.mkdtemp()
        
        # Mock shutil.disk_usage to raise PermissionError
        import shutil as real_shutil
        orig_disk_usage = real_shutil.disk_usage
        
        def mock_disk_usage(path):
            if path == forbidden_dir:
                raise PermissionError("[Errno 13] Permission denied")
            return orig_disk_usage(path)
            
        real_shutil.disk_usage = mock_disk_usage
        
        try:
            parser = TokenParser()
            builder = DirectoryBuilder("{Destination}/")
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[forbidden_dir],
                token_parser=parser,
                directory_builder=builder
            )
            
            space_info = engine.check_free_space()
            self.assertIn(forbidden_dir, space_info)
            info = space_info[forbidden_dir]
            self.assertFalse(info["sufficient"])
            self.assertEqual(info["error"], "Permission Denied")
        finally:
            real_shutil.disk_usage = orig_disk_usage
            shutil.rmtree(forbidden_dir)
            shutil.rmtree(src_dir)

    def test_html_report_xss_escaping(self):
        """Test that HTML report generator escapes XSS payloads in filenames, project names, etc."""
        xss_payload = "<script>alert('XSS')</script>"
        file_list = [{
            "filename": f"clip_{xss_payload}.mxf",
            "size": 100,
            "shot_time": f"time_{xss_payload}",
            "source_hash": f"hash_{xss_payload}",
            "status": "VERIFIED",
            "dest_hashes": {"/dest/path": "hash"}
        }]
        summary = {
            "total_files": 1,
            "verified": 1,
            "failed": 0,
            "total_bytes": 100,
            "elapsed_seconds": 1.5,
            "avg_speed_bytes_sec": 100,
            "extra_files": [{"filename": f"extra_{xss_payload}.mxf", "size": 50, "dest_path": f"/dest/extra_{xss_payload}"}]
        }

        html_content = ReportGenerator.generate_html_report(
            project_name=f"proj_{xss_payload}",
            preset_name=f"preset_{xss_payload}",
            source_dir=f"src_{xss_payload}",
            destinations=[f"dest_{xss_payload}"],
            hash_algorithm="MD5",
            file_list=file_list,
            summary=summary,
            output_filepath=None
        )

        # The XSS payload should be escaped in HTML report content
        escaped_payload = html.escape(xss_payload)
        self.assertIn(escaped_payload, html_content)
        self.assertNotIn(xss_payload, html_content)

    def test_empty_directory_cleanup(self):
        """Test that empty directories created during a failed copy are cleaned up."""
        src_dir = tempfile.mkdtemp()
        dest_dir = tempfile.mkdtemp()
        
        try:
            src_file = os.path.join(src_dir, "clip1.mxf")
            with open(src_file, "wb") as f:
                f.write(b"data")

            # Output path will create a nested directory
            # We want to fail verification so it triggers cleanup
            parser = TokenParser()
            builder = DirectoryBuilder("{Destination}/Nested/Subfolder/")
            
            from core.verify_engine import VerifyEngine
            orig_compute = VerifyEngine.compute_file_hash
            
            @classmethod
            def mock_compute(cls, path, algo="MD5", buf_size=65536, callback=None):
                if dest_dir in path:
                    return "failed_hash"
                return orig_compute(path, algo, buf_size, callback)
                
            VerifyEngine.compute_file_hash = mock_compute

            try:
                engine = CopyEngine(
                    source_dir=src_dir,
                    destinations=[dest_dir],
                    token_parser=parser,
                    directory_builder=builder,
                    hash_algorithm="MD5"
                )
                engine.scan_source()
                engine.run_copy_session()
                
                # Check that destination file is deleted AND the empty subfolders are also deleted
                nested_dir = os.path.join(dest_dir, "Nested")
                self.assertFalse(os.path.exists(nested_dir), "Empty parent folders should be cleaned up!")
            finally:
                VerifyEngine.compute_file_hash = orig_compute
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest_dir)

    def test_verify_only_progress_calculation(self):
        """Test progress calculation and copied_bytes correctness in run_verify_only_session."""
        src_dir = tempfile.mkdtemp()
        dest_dir = tempfile.mkdtemp()
        
        try:
            src_file = os.path.join(src_dir, "clip1.mxf")
            with open(src_file, "wb") as f:
                f.write(b"video data")
            
            # Destination already exists (needed for verify-only)
            dest_file = os.path.join(dest_dir, "clip1.mxf")
            with open(dest_file, "wb") as f:
                f.write(b"video data")

            parser = TokenParser()
            builder = DirectoryBuilder("{Destination}/")
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest_dir],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5"
            )
            engine.scan_source()

            # Mock callback to verify progress params
            progress_calls = []
            def on_progress(file_info, bytes_read, speed, eta):
                progress_calls.append(bytes_read)

            engine.run_verify_only_session(on_file_progress=on_progress)
            
            # Verify total_bytes was updated to total_work_bytes (source hash + dest verify = 2 * file_size)
            self.assertEqual(engine.total_bytes, 20)
            self.assertEqual(engine.copied_bytes, 20)
            self.assertTrue(len(progress_calls) > 0)
            
            # The maximum reported bytes_read in any progress call should not exceed the current file size (10)
            self.assertLessEqual(max(progress_calls), 10)
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest_dir)

if __name__ == '__main__':
    unittest.main()
