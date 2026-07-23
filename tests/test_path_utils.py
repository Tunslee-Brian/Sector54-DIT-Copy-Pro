import os
import sys
import unittest
from unittest.mock import patch

from core.path_utils import get_exec_dir, get_preset_dir, get_sound_path

class TestPathUtils(unittest.TestCase):

    def test_get_exec_dir(self):
        path = get_exec_dir()
        self.assertTrue(os.path.isabs(path))

    def test_get_preset_dir(self):
        path = get_preset_dir()
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.endswith("presets"))

    def test_get_sound_path(self):
        sound_file = "finish.mp3"
        path = get_sound_path(sound_file)
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(path.endswith("finish.mp3"))

    def test_frozen_executable_path(self):
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', '/mock/dist/DIT_Copy_Pro'):
            exec_dir = get_exec_dir()
            self.assertEqual(exec_dir, "/mock/dist")
            preset_dir = get_preset_dir()
            self.assertEqual(preset_dir, "/mock/dist/presets")


if __name__ == "__main__":
    unittest.main()
