import time
import subprocess
import threading
import queue
from PIL import Image
from core.logger_config import logger
from ui.preview.preview_helpers import get_subprocess_kwargs

class InAppVideoDecoder:
    """
    Background video decoder pipeline using ffmpeg rawvideo pipe.
    Extracts frames preserving target aspect ratio and pushes to thread-safe queue.
    """

    def __init__(self):
        self.filepath = ""
        self.proc = None
        self.thread = None
        self.queue = queue.Queue(maxsize=8)
        self.is_running = False
        self.is_paused = False
        self.fps = 24.0
        self.width = 640
        self.height = 360
        self._lock = threading.Lock()

    def start(self, filepath: str, start_sec: float = 0.0, render_w: int = 640, render_h: int = 360, fps: float = 24.0):
        self.stop()
        self.filepath = filepath
        self.width = max(160, render_w)
        self.height = max(120, render_h)
        self.fps = max(1.0, fps)
        self.is_running = True
        self.is_paused = False

        self.thread = threading.Thread(target=self._run_decoder, args=(start_sec,), daemon=True)
        self.thread.start()

    def _run_decoder(self, start_sec: float):
        cmd = [
            "ffmpeg", "-loglevel", "quiet",
            "-ss", str(start_sec),
            "-i", self.filepath,
            "-r", str(self.fps),
            "-f", "image2pipe",
            "-pix_fmt", "rgb24",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-"
        ]
        try:
            with self._lock:
                if not self.is_running:
                    return
                self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **get_subprocess_kwargs())
                proc = self.proc
        except Exception as e:
            logger.warning(f"Failed to start ffmpeg video decoder process: {e}")
            return

        frame_size = self.width * self.height * 3
        curr_time = start_sec

        while self.is_running and proc.poll() is None:
            if self.is_paused:
                time.sleep(0.05)
                continue

            try:
                raw_bytes = proc.stdout.read(frame_size)
                if not raw_bytes or len(raw_bytes) < frame_size:
                    break

                img = Image.frombytes("RGB", (self.width, self.height), raw_bytes)
                curr_time += (1.0 / self.fps)

                while self.is_running and not self.is_paused:
                    try:
                        self.queue.put((img, curr_time), timeout=0.1)
                        break
                    except queue.Full:
                        if not self.is_running:
                            break
                        time.sleep(0.02)
            except Exception as e:
                logger.debug(f"Video decoder frame read loop interrupted: {e}")
                break

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.is_paused = False
        with self._lock:
            proc = self.proc
            self.proc = None

        if proc:
            try:
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
                proc.terminate()
                proc.kill()
                proc.wait(timeout=1)
            except Exception as e:
                logger.debug(f"Notice during ffmpeg proc cleanup: {e}")

        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Exception:
                break
