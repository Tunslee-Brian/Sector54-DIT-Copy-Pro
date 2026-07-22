import sys
import os
import shutil
import tempfile
import unittest
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.token_parser import TokenParser, format_date
from core.directory_builder import DirectoryBuilder
from core.verify_engine import VerifyEngine
from core.copy_engine import CopyEngine
from core.report_generator import ReportGenerator


class TestCore(unittest.TestCase):

    def test_date_format_helper(self):
        dt = datetime(2021, 7, 26)
        self.assertEqual(format_date(dt, "YYMMDD"), "210726")
        self.assertEqual(format_date(dt, "DDMMYY"), "260721")
        self.assertEqual(format_date(dt, "DDMMYYYY"), "26072021")
        self.assertEqual(format_date(dt, "YYYYMMDD"), "20210726")
        self.assertEqual(format_date(dt, "YYYY-MM-DD"), "2021-07-26")
        self.assertEqual(format_date(dt, "YY-MM-DD"), "21-07-26")

    def test_token_parser(self):
        parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
        res = parser.parse("A005C012_25072026.MXF", fallback_project="TestProj")

        self.assertEqual(res["Camera"], "A")
        self.assertEqual(res["Roll"], "005")
        self.assertEqual(res["Clip"], "012")
        self.assertEqual(res["Date"], "25072026")
        self.assertEqual(res["Project"], "TestProj")

        # Test customizable date format parsing
        parser_yymmdd = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}", date_format="YYMMDD")
        dt = datetime(2021, 7, 26)
        res_date = parser_yymmdd.parse("A005C012_210726.MXF", dt=dt)
        self.assertEqual(res_date["Camera"], "A")
        self.assertEqual(res_date["Roll"], "005")
        self.assertEqual(res_date["Date"], "210726")

    def test_directory_builder(self):
        builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")
        tokens = {"Camera": "A", "Roll": "005"}
        paths = builder.build_paths_for_all_destinations(
            ["/tmp/RAID_01", "/tmp/BACKUP_01"],
            tokens,
            "A005C012_25072026.MXF"
        )

        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0], os.path.normpath("/tmp/RAID_01/Footage/A/Roll_005/A005C012_25072026.MXF"))
        self.assertEqual(paths[1], os.path.normpath("/tmp/BACKUP_01/Footage/A/Roll_005/A005C012_25072026.MXF"))

    def test_verify_engine(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(b"Hello DIT Copy Pro Test Content")
        tmp.close()

        try:
            md5_hash = VerifyEngine.compute_file_hash(tmp.name, "MD5")
            self.assertEqual(len(md5_hash), 32)
            self.assertTrue(VerifyEngine.verify_copy(md5_hash, md5_hash, "MD5"))
        finally:
            os.remove(tmp.name)

    def test_copy_engine_multi_dest(self):
        src_dir = tempfile.mkdtemp()
        dest1 = tempfile.mkdtemp()
        dest2 = tempfile.mkdtemp()

        # Create dummy source files
        f1 = os.path.join(src_dir, "A001C001_25072026.MXF")
        with open(f1, "wb") as f:
            f.write(b"Video stream dummy bytes content 1234567890" * 100)

        try:
            parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
            builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")

            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1, dest2],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5",
                buffer_size_mb=1
            )

            file_list = engine.scan_source()
            self.assertEqual(len(file_list), 1)

            summary = engine.run_copy_session()
            self.assertEqual(summary["verified"], 1)
            self.assertEqual(summary["failed"], 0)

            # Verify files created in dest1 and dest2
            dest1_file = os.path.join(dest1, "Footage/A/Roll_001/A001C001_25072026.MXF")
            dest2_file = os.path.join(dest2, "Footage/A/Roll_001/A001C001_25072026.MXF")

            self.assertTrue(os.path.exists(dest1_file))
            self.assertTrue(os.path.exists(dest2_file))
            self.assertEqual(os.path.getsize(dest1_file), os.path.getsize(f1))
            self.assertEqual(os.path.getsize(dest2_file), os.path.getsize(f1))
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest1)
            shutil.rmtree(dest2)

    def test_cancel_and_cleanup(self):
        src_dir = tempfile.mkdtemp()
        dest1 = tempfile.mkdtemp()
        f1 = os.path.join(src_dir, "A001C002_25072026.MXF")
        with open(f1, "wb") as f:
            f.write(b"Dummy test bytes" * 1000)

        try:
            parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
            builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")

            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5",
                buffer_size_mb=1
            )
            engine.scan_source()
            def cancel_on_start(f_info):
                engine.cancel()

            summary = engine.run_copy_session(on_file_start=cancel_on_start)

            self.assertTrue(summary["cancelled"])
            dest_file = os.path.join(dest1, "Footage/A/Roll_001/A001C002_25072026.MXF")
            self.assertFalse(os.path.exists(dest_file))
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest1)

    def test_verify_only_session(self):
        src_dir = tempfile.mkdtemp()
        dest1 = tempfile.mkdtemp()

        filename = "A001C003_25072026.MXF"
        src_file = os.path.join(src_dir, filename)
        content = b"Content for verify only testing 9876543210" * 50
        with open(src_file, "wb") as f:
            f.write(content)

        parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
        builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")
        dest_file = builder.build_path_for_destination(dest1, parser.parse(filename), filename)
        builder.ensure_directory_exists(dest_file)
        with open(dest_file, "wb") as f:
            f.write(content)

        try:
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5",
                buffer_size_mb=1
            )
            engine.scan_source()
            summary = engine.run_verify_only_session()

            self.assertEqual(summary["mode"], "VERIFY_ONLY")
            self.assertEqual(summary["verified"], 1)
            self.assertEqual(summary["failed"], 0)
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest1)

    def test_extra_files_detection(self):
        src_dir = tempfile.mkdtemp()
        dest1 = tempfile.mkdtemp()

        # Source file
        f1 = os.path.join(src_dir, "A001C001_25072026.MXF")
        with open(f1, "wb") as f:
            f.write(b"Source content 123")

        # Extra file in destination
        extra_path = os.path.join(dest1, "OLD_CLIP_EXTRA.MP4")
        with open(extra_path, "wb") as f:
            f.write(b"Orphan file content 999")

        try:
            parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
            builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")

            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5",
                buffer_size_mb=1
            )
            engine.scan_source()
            summary = engine.run_copy_session()

            self.assertEqual(summary["extra_count"], 1)
            self.assertEqual(summary["extra_files"][0]["filename"], "OLD_CLIP_EXTRA.MP4")
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest1)

    def test_verify_only_multi_dest_progress_count(self):
        src_dir = tempfile.mkdtemp()
        dest1 = tempfile.mkdtemp()
        dest2 = tempfile.mkdtemp()

        filename = "A001C004_25072026.MXF"
        src_file = os.path.join(src_dir, filename)
        content = b"Multi dest verify progress check content 12345" * 100
        with open(src_file, "wb") as f:
            f.write(content)

        parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
        builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")

        dest1_file = builder.build_path_for_destination(dest1, parser.parse(filename), filename)
        builder.ensure_directory_exists(dest1_file)
        with open(dest1_file, "wb") as f:
            f.write(content)

        dest2_file = builder.build_path_for_destination(dest2, parser.parse(filename), filename)
        builder.ensure_directory_exists(dest2_file)
        with open(dest2_file, "wb") as f:
            f.write(content)

        try:
            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1, dest2],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5",
                buffer_size_mb=1
            )
            engine.scan_source()
            summary = engine.run_verify_only_session()

            self.assertEqual(summary["verified"], 1)
            # Ensure copied_bytes is equal to total_bytes (not doubled)
            self.assertEqual(engine.copied_bytes, engine.total_bytes)
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest1)
            shutil.rmtree(dest2)

    def test_check_free_space(self):
        src_dir = tempfile.mkdtemp()
        dest1 = tempfile.mkdtemp()

        f1 = os.path.join(src_dir, "A001C005_25072026.MXF")
        with open(f1, "wb") as f:
            f.write(b"Test content 123")

        try:
            parser = TokenParser("{Camera:1}{Roll:3}C{Clip:3}_{Date:8}")
            builder = DirectoryBuilder("{Destination}/Footage/{Camera}/Roll_{Roll}/")

            engine = CopyEngine(
                source_dir=src_dir,
                destinations=[dest1],
                token_parser=parser,
                directory_builder=builder,
                hash_algorithm="MD5",
                buffer_size_mb=1
            )
            engine.scan_source()
            space_info = engine.check_free_space()

            self.assertIn(dest1, space_info)
            self.assertGreaterEqual(space_info[dest1]["free_bytes"], 0)
            self.assertTrue(space_info[dest1]["sufficient"])
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(dest1)

    def test_generate_html_report(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp.close()

        file_list = [
            {
                "filename": "A001C001_25072026.MXF",
                "size": 1024,
                "shot_time": "2026-07-22 12:00:00",
                "source_hash": "d41d8cd98f00b204e9800998ecf8427e",
                "status": "VERIFIED"
            }
        ]
        summary = {
            "total_files": 1,
            "verified": 1,
            "failed": 0,
            "extra_files": [],
            "total_bytes": 1024,
            "elapsed_seconds": 1.5,
            "avg_speed_bytes_sec": 1024
        }

        try:
            html = ReportGenerator.generate_html_report(
                project_name="Test Project",
                preset_name="ARRI ALEXA Standard",
                source_dir="/tmp/source",
                destinations=["/tmp/dest1"],
                hash_algorithm="MD5",
                file_list=file_list,
                summary=summary,
                output_filepath=tmp.name
            )

            self.assertIn("DIT COPY REPORT", html)
            self.assertIn("A001C001_25072026.MXF", html)
            self.assertIn("PASSED 100%", html)
            self.assertTrue(os.path.exists(tmp.name))
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_generate_txt_report(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.close()

        file_list = [
            {
                "filename": "A001C001_25072026.MXF",
                "size": 1024,
                "shot_time": "2026-07-22 12:00:00",
                "source_hash": "d41d8cd98f00b204e9800998ecf8427e",
                "status": "VERIFIED"
            }
        ]
        summary = {
            "total_files": 1,
            "verified": 1,
            "failed": 0,
            "extra_files": [],
            "total_bytes": 1024,
            "elapsed_seconds": 1.5,
            "avg_speed_bytes_sec": 1024
        }

        try:
            txt = ReportGenerator.generate_txt_report(
                project_name="Test Project",
                preset_name="ARRI ALEXA Standard",
                source_dir="/tmp/source",
                destinations=["/tmp/dest1"],
                hash_algorithm="MD5",
                file_list=file_list,
                summary=summary,
                output_filepath=tmp.name
            )

            self.assertIn("DIT COPY REPORT", txt)
            self.assertIn("A001C001_25072026.MXF", txt)
            self.assertIn("Summary", txt)
            self.assertTrue(os.path.exists(tmp.name))
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)



if __name__ == "__main__":
    unittest.main()





