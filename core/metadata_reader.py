import os
import time
import subprocess
from datetime import datetime
from PIL import Image, ExifTags


class MetadataReader:
    """
    Extracts authentic camera shot creation timestamps from media headers or filesystem stats.
    """

    @staticmethod
    def get_shot_time(filepath: str) -> str:
        """
        Returns formatted shot date/time string (YYYY-MM-DD HH:MM:SS).
        """
        if not filepath or not os.path.exists(filepath):
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ext = os.path.splitext(filepath)[1].lower()

        # 1. Try ffprobe for video & audio formats
        if ext in (".mov", ".mxf", ".mp4", ".avi", ".mkv", ".m4v", ".mp3", ".wav"):
            try:
                cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format_tags=creation_time:stream_tags=creation_time",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    filepath
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                if res.returncode == 0 and res.stdout.strip():
                    raw_time = res.stdout.strip().split("\n")[0].replace("Z", "")
                    dt = datetime.fromisoformat(raw_time)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        # 2. Try PIL EXIF for image formats
        if ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".dng"):
            try:
                with Image.open(filepath) as img:
                    exif = img._getexif()
                    if exif:
                        for tag_id, val in exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, "")
                            if tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                                dt = datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S")
                                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        # 3. Fallback to filesystem modification time
        try:
            stat = os.stat(filepath)
            mtime = stat.st_mtime
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        except Exception:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

