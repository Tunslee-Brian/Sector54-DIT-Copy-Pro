import os
import sys
import subprocess

def is_media_file(filepath: str) -> bool:
    """Returns True if the file extension corresponds to a previewable media or document file."""
    if not filepath:
        return False

    ext = os.path.splitext(filepath)[1].lower()
    media_extensions = {
        # Video
        ".mp4", ".mov", ".mxf", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".ts",
        ".ari", ".r3d", ".braw", ".arw", ".cr3",
        # Image
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".dng", ".ico",
        # Audio
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".aiff",
        # Documents / Logs / Metadata
        ".txt", ".json", ".csv", ".md", ".log", ".xml", ".mhl", ".ini", ".py", ".sh"
    }
    return ext in media_extensions


def get_media_category(filepath: str) -> str:
    if not filepath:
        return "NONE"
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".dng", ".ico"}:
        return "IMAGE"
    elif ext in {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".aiff"}:
        return "AUDIO"
    elif ext in {".mp4", ".mov", ".mxf", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv", ".ts", ".ari", ".r3d", ".braw", ".arw", ".cr3"}:
        return "VIDEO"
    elif ext in {".txt", ".json", ".csv", ".md", ".log", ".xml", ".mhl", ".ini", ".py", ".sh"}:
        return "DOCUMENT"
    return "FILE"


def get_subprocess_kwargs():
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs
