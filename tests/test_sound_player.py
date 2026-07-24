import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from core.sound_player import SoundPlayer

class TestSoundPlayer(unittest.TestCase):

    def test_sound_player_init(self):
        player = SoundPlayer()
        self.assertIsNotNone(player.finish_mp3_path)

    def test_play_error_does_not_crash(self):
        player = SoundPlayer()
        player.play_error()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_play_success_cli_player(self, mock_run, mock_which):
        mock_which.side_effect = lambda cmd: cmd == "mpg123"
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("pygame.mixer.music.play", side_effect=Exception("mock fail")):
                player = SoundPlayer(finish_mp3_path=tmp_path)
                player.play_success()
                import time
                time.sleep(0.1)
                self.assertTrue(mock_run.called)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    @patch("core.sound_player.shutil.which")
    def test_play_success_pygame_fallback(self, mock_which):
        mock_which.return_value = None

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            player = SoundPlayer(finish_mp3_path=tmp_path)
            player.play_success()
            import time
            time.sleep(0.1)
            self.assertFalse(player._is_playing)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
