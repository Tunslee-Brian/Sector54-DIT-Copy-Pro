import sys
import os


def get_exec_dir() -> str:
    """
    Returns the absolute path of the directory containing the executable file
    (when compiled/frozen with PyInstaller) or the main project root directory.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_preset_dir() -> str:
    """
    Returns the presets directory path alongside the executable file.
    """
    return os.path.join(get_exec_dir(), "presets")


def get_sound_path(filename: str = "finish.mp3") -> str:
    """
    Returns the sound file path alongside the executable file.
    """
    return os.path.join(get_exec_dir(), filename)
