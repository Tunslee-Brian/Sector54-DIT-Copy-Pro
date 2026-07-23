import os
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from core.metadata_reader import MetadataReader

class TestMetadataReader(unittest.TestCase):

    def test_nonexistent_file_fallback(self):
        shot_time = MetadataReader.get_shot_time("/nonexistent/file/path.mov")
        self.assertIsNotNone(shot_time)

    def test_temp_file_mtime_fallback(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"sample content")
            tmp_path = tmp.name

        try:
            shot_time = MetadataReader.get_shot_time(tmp_path)
            self.assertIsNotNone(shot_time)
            self.assertEqual(len(shot_time), 19)  # YYYY-MM-DD HH:MM:SS format
        finally:
            os.remove(tmp_path)

    @patch("subprocess.run")
    def test_ffprobe_shot_time_extraction(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "2026-07-20T14:30:00.000000Z\n"
        mock_run.return_value = mock_res

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            shot_time = MetadataReader.get_shot_time(tmp_path)
            self.assertEqual(shot_time, "2026-07-20 14:30:00")
        finally:
            os.remove(tmp_path)

    @patch("PIL.Image.open")
    def test_pil_exif_shot_time_extraction(self, mock_image_open):
        mock_img = MagicMock()
        mock_img._getexif.return_value = {
            36867: "2026:07:21 10:15:30"  # DateTimeOriginal EXIF tag (%Y:%m:%d %H:%M:%S)
        }
        mock_image_open.return_value.__enter__.return_value = mock_img

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            shot_time = MetadataReader.get_shot_time(tmp_path)
            self.assertEqual(shot_time, "2026-07-21 10:15:30")
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
