import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import threading
import subprocess
import shutil
from core.path_utils import get_sound_path

class SoundPlayer:
    """
    Plays notification sounds for success (finish.mp3) and failure alerts.
    Ensures sound plays EXACTLY ONCE without looping or repeating.
    """

    def __init__(self, finish_mp3_path: str = None):
        if not finish_mp3_path:
            finish_mp3_path = get_sound_path("finish.mp3")
        self.finish_mp3_path = os.path.abspath(finish_mp3_path)
        self._is_playing = False
        self._lock = threading.Lock()

    def play_success(self):
        """
        Plays finish.mp3 asynchronously on success.
        Selects the single best player available and ensures playback happens ONLY ONCE.
        """
        with self._lock:
            if self._is_playing:
                return
            self._is_playing = True

        def _play():
            try:
                if not os.path.exists(self.finish_mp3_path):
                    return

                # Select EXACTLY ONE player command using if/elif (NO LOOPING over multiple players)
                cmd = None
                if shutil.which("mpg123"):
                    cmd = ["mpg123", "-q", self.finish_mp3_path]
                elif shutil.which("mpv"):
                    cmd = ["mpv", "--no-video", "--really-quiet", self.finish_mp3_path]
                elif shutil.which("ffplay"):
                    cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", self.finish_mp3_path]
                elif shutil.which("pw-play"):
                    cmd = ["pw-play", self.finish_mp3_path]
                elif shutil.which("afplay"):  # macOS
                    cmd = ["afplay", self.finish_mp3_path]

                if cmd:
                    try:
                        kwargs = {}
                        if sys.platform == "win32":
                            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, **kwargs)
                    except Exception:
                        cmd = None

                if not cmd:
                    try:
                        import pygame.mixer
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.music.load(self.finish_mp3_path)
                        pygame.mixer.music.play()
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                with self._lock:
                    self._is_playing = False

        threading.Thread(target=_play, daemon=True).start()

    def play_error(self):
        """
        Plays alert sound on failure.
        """
        def _play():
            print("\a", end="", flush=True)

        threading.Thread(target=_play, daemon=True).start()
