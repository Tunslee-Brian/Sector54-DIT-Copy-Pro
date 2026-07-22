import os
import sys
import time
import subprocess
import tempfile
import threading
import queue
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk
import pygame

import ui.theme as theme


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


def _get_subprocess_kwargs():
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


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
            "-f", "image2pipe",
            "-pix_fmt", "rgb24",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-"
        ]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_get_subprocess_kwargs())
        except Exception:
            return

        frame_size = self.width * self.height * 3
        curr_time = start_sec

        while self.is_running and self.proc and self.proc.poll() is None:
            if self.is_paused:
                time.sleep(0.05)
                continue

            try:
                raw_bytes = self.proc.stdout.read(frame_size)
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
            except Exception:
                break

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.is_paused = False
        if self.proc:
            try:
                if self.proc.stdout:
                    self.proc.stdout.close()
                if self.proc.stderr:
                    self.proc.stderr.close()
                self.proc.terminate()
                self.proc.kill()
                self.proc.wait(timeout=1)
            except Exception:
                pass
            self.proc = None

        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Exception:
                break


class MediaPreviewWidget(ctk.CTkFrame):
    """
    Rich In-App Media Preview Panel designed for dark cinematography theme.
    Supports in-app image viewer (with Zoom), audio player, in-app video player with synced audio,
    single combined Play/Pause toggle buttons, native aspect ratio preservation, and technical specs column.
    """

    def __init__(self, master, filepath: str = "", on_clear_callback=None, **kwargs):
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=6, **kwargs)

        self.filepath = os.path.abspath(filepath) if filepath else ""
        self.on_clear_callback = on_clear_callback
        self.category = get_media_category(self.filepath)

        # Image state
        self._orig_pil_image = None
        self._zoom_factor = 1.0

        # Audio state
        self._is_playing_audio = False
        self._audio_paused = False
        self._audio_duration = 0.0
        self._audio_start_time = 0.0
        self._audio_update_job = None
        self.audio_ffplay_proc = None

        # Video state
        self.video_decoder = InAppVideoDecoder()
        self.video_audio_proc = None
        self._is_playing_video = False
        self._video_paused = False
        self._video_duration = 0.0
        self._video_fps = 24.0
        self._video_orig_w = 1920
        self._video_orig_h = 1080
        self._video_current_sec = 0.0
        self._video_tick_job = None

        self._build_ui()
        if self.filepath and os.path.exists(self.filepath):
            self.load_file(self.filepath)
        else:
            self.clear_preview()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)     # Header fixed
        self.grid_rowconfigure(1, weight=1)     # Content container

        # Header Bar
        self.header_frame = ctk.CTkFrame(self, fg_color=theme.PANEL_BG, corner_radius=0, height=44)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.pack_propagate(False)

        # Category Badge Icon & Title
        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text="🎬 Xem Trước File (Media Preview)",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_MAIN
        )
        self.lbl_title.pack(side="left", padx=(12, 10), pady=6)

        # Format Badge
        self.badge_lbl = ctk.CTkLabel(
            self.header_frame,
            text=" PREVIEW ",
            font=(theme.FONT_FAMILY, 10, "bold"),
            fg_color=theme.ACCENT_PRIMARY,
            text_color="#ffffff",
            corner_radius=4,
            height=20
        )
        self.badge_lbl.pack(side="left", padx=(0, 10), pady=6)

        # File Size & Date info
        self.lbl_meta = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED
        )
        self.lbl_meta.pack(side="left", padx=5, pady=6)

        # Right Action Buttons
        self.btn_open_folder = ctk.CTkButton(
            self.header_frame,
            text="📂 Mở Thư Mục",
            font=(theme.FONT_FAMILY, 11),
            width=90,
            height=28,
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self._open_containing_folder
        )
        self.btn_open_folder.pack(side="right", padx=(5, 10), pady=6)

        self.btn_copy_path = ctk.CTkButton(
            self.header_frame,
            text="📋 Sao Chép Đường Dẫn",
            font=(theme.FONT_FAMILY, 11),
            width=130,
            height=28,
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self._copy_path_to_clipboard
        )
        self.btn_copy_path.pack(side="right", padx=3, pady=6)

        # Main Content Frame
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    # -----------------------------------------------------------------
    # Public Load & Clear Methods
    # -----------------------------------------------------------------
    def load_file(self, filepath: str):
        """Load and display preview for a new file."""
        self._stop_all_playback()
        self._clear_container_widgets()

        if not filepath or not os.path.exists(filepath):
            self.clear_preview()
            return

        self.filepath = os.path.abspath(filepath)
        self.category = get_media_category(self.filepath)

        filename = os.path.basename(self.filepath)
        icons = {
            "IMAGE": "🖼️",
            "AUDIO": "🎵",
            "VIDEO": "🎬",
            "DOCUMENT": "📄",
            "FILE": "📁"
        }
        icon = icons.get(self.category, "📄")
        self.lbl_title.configure(text=f"{icon} {filename}")
        self.badge_lbl.configure(text=f" {self.category} ")

        size_str = self._format_file_size(os.path.getsize(self.filepath))
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(self.filepath)))
        self.lbl_meta.configure(text=f"Dung lượng: {size_str}  •  Sửa đổi: {mtime}")

        self.btn_open_folder.configure(state="normal")
        self.btn_copy_path.configure(state="normal")

        if self.category == "IMAGE":
            self._build_image_preview()
        elif self.category == "AUDIO":
            self._build_audio_preview()
        elif self.category == "VIDEO":
            self._build_video_preview()
        elif self.category == "DOCUMENT":
            self._build_document_preview()
        else:
            self._build_generic_preview()

    def clear_preview(self):
        """Clear all loaded preview data and reset panel to empty state."""
        self._stop_all_playback()
        self.filepath = ""
        self.category = "NONE"
        self._orig_pil_image = None
        self._zoom_factor = 1.0

        self.lbl_title.configure(text="🎬 Xem Trước File (Media Preview)")
        self.badge_lbl.configure(text=" TRỐNG ")
        self.lbl_meta.configure(text="")

        self.btn_open_folder.configure(state="disabled")
        self.btn_copy_path.configure(state="disabled")

        self._clear_container_widgets()

        card = ctk.CTkFrame(self.container, fg_color=theme.PANEL_BG, corner_radius=8)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            card,
            text="🎞️",
            font=(theme.FONT_FAMILY, 64)
        ).pack(pady=(50, 10))

        ctk.CTkLabel(
            card,
            text="Chưa Chọn Tệp Để Xem Trước",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_MAIN
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            card,
            text="Bấm vào một tệp hình ảnh, âm thanh, video hoặc tài liệu ở Sidebar để xem trực tiếp tại đây.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MUTED
        ).pack(pady=(0, 20))

        if self.on_clear_callback:
            try:
                self.on_clear_callback()
            except Exception:
                pass

    def _stop_all_playback(self):
        self._stop_audio()
        self._stop_video()

    def _clear_container_widgets(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # -----------------------------------------------------------------
    # 1. IMAGE PREVIEW
    # -----------------------------------------------------------------
    def _build_image_preview(self):
        toolbar = ctk.CTkFrame(self.container, fg_color=theme.PANEL_BG, height=36, corner_radius=4)
        toolbar.pack(fill="x", side="top", pady=(0, 8))

        self.lbl_img_info = ctk.CTkLabel(
            toolbar,
            text="Đang tải ảnh...",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED
        )
        self.lbl_img_info.pack(side="left", padx=10)

        btn_fit = ctk.CTkButton(
            toolbar,
            text="🔍 Fit Window",
            width=80,
            height=24,
            font=(theme.FONT_FAMILY, 10),
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            command=self._reset_image_zoom
        )
        btn_fit.pack(side="right", padx=5)

        btn_zoom_out = ctk.CTkButton(
            toolbar,
            text="➖ Zoom -",
            width=70,
            height=24,
            font=(theme.FONT_FAMILY, 10),
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            command=lambda: self._adjust_image_zoom(0.8)
        )
        btn_zoom_out.pack(side="right", padx=2)

        btn_zoom_in = ctk.CTkButton(
            toolbar,
            text="➕ Zoom +",
            width=70,
            height=24,
            font=(theme.FONT_FAMILY, 10),
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            command=lambda: self._adjust_image_zoom(1.25)
        )
        btn_zoom_in.pack(side="right", padx=2)

        self.img_scroll_frame = ctk.CTkScrollableFrame(self.container, fg_color="#121417")
        self.img_scroll_frame.pack(fill="both", expand=True)

        self.lbl_image_display = ctk.CTkLabel(self.img_scroll_frame, text="")
        self.lbl_image_display.pack(expand=True, padx=20, pady=20)

        self.after(50, self._load_image_file)

    def _load_image_file(self):
        if not self.filepath or not os.path.exists(self.filepath):
            return
        try:
            self._orig_pil_image = Image.open(self.filepath)
            w, h = self._orig_pil_image.size
            mode = self._orig_pil_image.mode
            fmt = self._orig_pil_image.format or os.path.splitext(self.filepath)[1].upper()
            if hasattr(self, "lbl_img_info") and self.lbl_img_info.winfo_exists():
                self.lbl_img_info.configure(text=f"Độ phân giải: {w} × {h} px  |  Định dạng: {fmt} ({mode})")
            self._display_image()
        except Exception as e:
            if hasattr(self, "lbl_image_display") and self.lbl_image_display.winfo_exists():
                self.lbl_image_display.configure(text=f"❌ Không thể tải ảnh: {e}", text_color=theme.ACCENT_DANGER)

    def _display_image(self):
        if not self._orig_pil_image or not hasattr(self, "lbl_image_display") or not self.lbl_image_display.winfo_exists():
            return

        w, h = self._orig_pil_image.size
        new_w = max(50, int(w * self._zoom_factor))
        new_h = max(50, int(h * self._zoom_factor))

        if self._zoom_factor == 1.0:
            avail_w = max(400, self.img_scroll_frame.winfo_width() - 40)
            avail_h = max(300, self.img_scroll_frame.winfo_height() - 40)
            ratio = min(avail_w / max(1, w), avail_h / max(1, h), 1.0)
            new_w = max(50, int(w * ratio))
            new_h = max(50, int(h * ratio))

        resized_pil = self._orig_pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=resized_pil, dark_image=resized_pil, size=(new_w, new_h))

        self.lbl_image_display.configure(image=ctk_img, text="")

    def _adjust_image_zoom(self, factor: float):
        if self._zoom_factor == 1.0:
            self._zoom_factor = 1.0 * factor
        else:
            self._zoom_factor *= factor
        self._zoom_factor = max(0.1, min(5.0, self._zoom_factor))
        self._display_image()

    def _reset_image_zoom(self):
        self._zoom_factor = 1.0
        self._display_image()

    # -----------------------------------------------------------------
    # 2. AUDIO PREVIEW (Single Toggle Play/Pause Button)
    # -----------------------------------------------------------------
    def _build_audio_preview(self):
        card = ctk.CTkFrame(self.container, fg_color=theme.PANEL_BG, corner_radius=8)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_big_icon = ctk.CTkLabel(card, text="🎧", font=(theme.FONT_FAMILY, 64))
        lbl_big_icon.pack(pady=(30, 10))

        lbl_track_name = ctk.CTkLabel(
            card,
            text=os.path.basename(self.filepath),
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_track_name.pack(pady=(0, 5))

        self.lbl_audio_status = ctk.CTkLabel(
            card,
            text="Sẵn sàng phát âm thanh",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MUTED
        )
        self.lbl_audio_status.pack(pady=(0, 20))

        self.lbl_audio_time = ctk.CTkLabel(
            card,
            text="00:00 / 00:00",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        self.lbl_audio_time.pack(pady=(0, 10))

        self.slider_audio_progress = ctk.CTkSlider(
            card,
            from_=0,
            to=100,
            height=14,
            fg_color=theme.CARD_BG,
            progress_color=theme.ACCENT_PRIMARY,
            button_color=theme.ACCENT_PRIMARY,
            button_hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._on_audio_seek
        )
        self.slider_audio_progress.pack(fill="x", padx=40, pady=(0, 20))
        self.slider_audio_progress.set(0)

        controls_frame = ctk.CTkFrame(card, fg_color="transparent")
        controls_frame.pack(pady=10)

        # Single Integrated Play / Pause Toggle Button
        self.btn_toggle_audio_play = ctk.CTkButton(
            controls_frame,
            text="▶ Phát Audio",
            font=(theme.FONT_FAMILY, 12, "bold"),
            width=140,
            height=38,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._toggle_audio_playback
        )
        self.btn_toggle_audio_play.pack(side="left", padx=8)

        self.btn_stop_audio = ctk.CTkButton(
            controls_frame,
            text="⏹ Dừng",
            font=(theme.FONT_FAMILY, 12),
            width=90,
            height=38,
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            state="disabled",
            command=self._stop_audio
        )
        self.btn_stop_audio.pack(side="left", padx=8)

        self._init_audio_duration()

    def _has_mixer(self) -> bool:
        try:
            import pygame.mixer
            return pygame.mixer is not None and hasattr(pygame.mixer, "get_init")
        except (ImportError, AttributeError, Exception):
            return False

    def _init_audio_duration(self):
        self._audio_duration = 0.0
        target_filepath = self.filepath

        def _worker():
            dur = 0.0
            try:
                cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    target_filepath
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3, **_get_subprocess_kwargs())
                if res.returncode == 0 and res.stdout.strip():
                    dur = float(res.stdout.strip())
            except Exception:
                pass

            if dur <= 0 and self._has_mixer():
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    sound = pygame.mixer.Sound(target_filepath)
                    dur = sound.get_length()
                except Exception:
                    pass

            def _apply():
                if getattr(self, "filepath", "") != target_filepath:
                    return
                self._audio_duration = dur
                if hasattr(self, "lbl_audio_time") and self.lbl_audio_time.winfo_exists():
                    self.lbl_audio_time.configure(text=f"00:00 / {self._format_seconds(self._audio_duration)}")

            if hasattr(self, "after"):
                try:
                    self.after(0, _apply)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_audio_playback(self):
        if self._is_playing_audio:
            self._pause_audio()
        else:
            self._play_audio()

    def _play_audio(self):
        try:
            if self._audio_paused:
                if self._has_mixer() and pygame.mixer.get_init():
                    try:
                        pygame.mixer.music.unpause()
                    except Exception:
                        pass
                else:
                    self._start_audio_ffplay(self._audio_start_time)
            else:
                if self._has_mixer():
                    try:
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.music.load(self.filepath)
                        pygame.mixer.music.set_volume(1.0)
                        pygame.mixer.music.play()
                    except Exception:
                        self._start_audio_ffplay(0.0)
                else:
                    self._start_audio_ffplay(0.0)

                self._audio_start_time = time.time()

            self._audio_paused = False
            self._is_playing_audio = True

            self.btn_toggle_audio_play.configure(text="⏸ Tạm Dừng", fg_color=theme.CARD_BG, hover_color=theme.CARD_BORDER)
            self.btn_stop_audio.configure(state="normal", fg_color=theme.ACCENT_DANGER, hover_color=theme.ACCENT_DANGER_HOVER)
            self.lbl_audio_status.configure(text="Đang phát âm thanh...", text_color=theme.ACCENT_SUCCESS)

            self._update_audio_loop()
        except Exception as e:
            self.lbl_audio_status.configure(text=f"Lỗi phát âm thanh: {e}", text_color=theme.ACCENT_DANGER)

    def _start_audio_ffplay(self, start_sec: float = 0.0):
        self._stop_audio_ffplay()
        if not self.filepath or not os.path.exists(self.filepath):
            return
        cmd = ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_sec), self.filepath]
        try:
            self.audio_ffplay_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **_get_subprocess_kwargs())
        except Exception:
            self.audio_ffplay_proc = None

    def _pause_audio(self):
        if self._is_playing_audio:
            if self._has_mixer() and pygame.mixer.get_init():
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
            self._stop_audio_ffplay()

            self._audio_paused = True
            self._is_playing_audio = False

            self.btn_toggle_audio_play.configure(text="▶ Phát Audio", fg_color=theme.ACCENT_PRIMARY, hover_color=theme.ACCENT_PRIMARY_HOVER)
            self.lbl_audio_status.configure(text="Đã tạm dừng", text_color=theme.ACCENT_WARNING)

    def _stop_audio(self):
        if self._has_mixer() and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._stop_audio_ffplay()

        self._is_playing_audio = False
        self._audio_paused = False

        if hasattr(self, "btn_toggle_audio_play") and self.btn_toggle_audio_play.winfo_exists():
            self.btn_toggle_audio_play.configure(text="▶ Phát Audio", fg_color=theme.ACCENT_PRIMARY, hover_color=theme.ACCENT_PRIMARY_HOVER)
            self.btn_stop_audio.configure(state="disabled", fg_color=theme.CARD_BG)
            self.slider_audio_progress.set(0)
            self.lbl_audio_time.configure(text=f"00:00 / {self._format_seconds(self._audio_duration)}")
            self.lbl_audio_status.configure(text="Đã dừng phát", text_color=theme.TEXT_MUTED)

        if self._audio_update_job:
            try:
                self.after_cancel(self._audio_update_job)
            except Exception:
                pass
            self._audio_update_job = None

    def _stop_audio_ffplay(self):
        if hasattr(self, "audio_ffplay_proc") and self.audio_ffplay_proc:
            try:
                self.audio_ffplay_proc.terminate()
                self.audio_ffplay_proc.kill()
                self.audio_ffplay_proc.wait(timeout=1)
            except Exception:
                pass
            self.audio_ffplay_proc = None

    def _on_audio_seek(self, val):
        if self._audio_duration > 0:
            target_sec = (val / 100.0) * self._audio_duration
            if self._has_mixer() and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.set_pos(target_sec)
                except Exception:
                    pass
            elif self._is_playing_audio:
                self._start_audio_ffplay(target_sec)

            self._audio_start_time = time.time() - target_sec

    def _set_audio_volume(self, val):
        if self._has_mixer() and pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(val)
            except Exception:
                pass

    def _update_audio_loop(self):
        if not self._is_playing_audio or not hasattr(self, "lbl_audio_time") or not self.lbl_audio_time.winfo_exists():
            return

        is_busy = False
        current_sec = 0.0

        if self._has_mixer() and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms >= 0:
                current_sec = pos_ms / 1000.0
                is_busy = True
        elif self.audio_ffplay_proc and self.audio_ffplay_proc.poll() is None:
            current_sec = time.time() - getattr(self, "_audio_start_time", time.time())
            is_busy = True

        if is_busy and not self._audio_paused:
            if self._audio_duration > 0:
                pct = min(100.0, (current_sec / self._audio_duration) * 100.0)
                self.slider_audio_progress.set(pct)
                self.lbl_audio_time.configure(
                    text=f"{self._format_seconds(current_sec)} / {self._format_seconds(self._audio_duration)}"
                )
            if self._audio_duration > 0 and current_sec >= self._audio_duration:
                self._stop_audio()
            else:
                self._audio_update_job = self.after(200, self._update_audio_loop)
        elif not self._audio_paused:
            self._stop_audio()

    # -----------------------------------------------------------------
    # 3. NATIVE IN-APP VIDEO PREVIEW PLAYER (Single Play/Pause Toggle + Video Audio Sync)
    # -----------------------------------------------------------------
    def _build_video_preview(self):
        grid_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.grid_columnconfigure(0, weight=3)
        grid_frame.grid_columnconfigure(1, weight=2)
        grid_frame.grid_rowconfigure(0, weight=1)

        # Left Column Container (Video Canvas + Control Bar)
        self.left_video_container = ctk.CTkFrame(grid_frame, fg_color="#0a0c0e", corner_radius=8)
        self.left_video_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.left_video_container.grid_columnconfigure(0, weight=1)
        self.left_video_container.grid_rowconfigure(0, weight=1)
        self.left_video_container.grid_rowconfigure(1, weight=0)

        # Video Frame Display Label
        self.lbl_video_display = ctk.CTkLabel(
            self.left_video_container,
            text="🎬 Đang chuẩn bị trình phát video...",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MUTED
        )
        self.lbl_video_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Video Control Panel Bar
        v_ctrl_frame = ctk.CTkFrame(self.left_video_container, fg_color=theme.PANEL_BG, corner_radius=0, height=75)
        v_ctrl_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        v_ctrl_frame.grid_columnconfigure(0, weight=1)

        # Progress / Seek Slider
        self.lbl_video_time = ctk.CTkLabel(
            v_ctrl_frame,
            text="00:00 / 00:00",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        self.lbl_video_time.pack(side="top", anchor="w", padx=15, pady=(6, 2))

        self.slider_video_seek = ctk.CTkSlider(
            v_ctrl_frame,
            from_=0,
            to=100,
            height=12,
            fg_color=theme.CARD_BG,
            progress_color=theme.ACCENT_PRIMARY,
            button_color=theme.ACCENT_PRIMARY,
            button_hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._on_video_seek
        )
        self.slider_video_seek.pack(side="top", fill="x", padx=15, pady=(0, 6))
        self.slider_video_seek.set(0)

        # Buttons Row: Combined Single Play/Pause Toggle & Reset Stop Button
        btn_row = ctk.CTkFrame(v_ctrl_frame, fg_color="transparent")
        btn_row.pack(side="top", fill="x", padx=15, pady=(0, 6))

        # Single Combined Play / Pause Button
        self.btn_toggle_video_play = ctk.CTkButton(
            btn_row,
            text="▶ Phát Video",
            font=(theme.FONT_FAMILY, 11, "bold"),
            width=130,
            height=32,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._toggle_video_playback
        )
        self.btn_toggle_video_play.pack(side="left", padx=(0, 6))

        self.btn_stop_video = ctk.CTkButton(
            btn_row,
            text="⏹ Dừng",
            font=(theme.FONT_FAMILY, 11),
            width=80,
            height=32,
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            state="disabled",
            command=self._stop_video
        )
        self.btn_stop_video.pack(side="left", padx=6)

        # Right Column Container (Video Specs Card)
        specs_frame = ctk.CTkFrame(grid_frame, fg_color=theme.PANEL_BG, corner_radius=8)
        specs_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        specs_frame.pack_propagate(False)

        ctk.CTkLabel(
            specs_frame,
            text="🎥 THÔNG SỐ KỸ THUẬT VIDEO",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.ACCENT_PRIMARY
        ).pack(anchor="w", padx=15, pady=(15, 10))

        self.lbl_video_specs = ctk.CTkLabel(
            specs_frame,
            text="Đang phân tích định dạng...",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MAIN,
            justify="left",
            anchor="w"
        )
        self.lbl_video_specs.pack(anchor="w", padx=15, pady=5, fill="x")

        btn_open_external = ctk.CTkButton(
            specs_frame,
            text="▶ MỞ BẰNG PLAYER HỆ THỐNG",
            font=(theme.FONT_FAMILY, 12, "bold"),
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            height=40,
            command=self._open_in_system_player
        )
        btn_open_external.pack(side="bottom", fill="x", padx=15, pady=15)

        self.after(80, self._load_video_metadata_and_poster)

    def _get_aspect_fitted_dimensions(self) -> tuple[int, int]:
        """Calculates scaled width and height that preserve native video aspect ratio without stretching."""
        try:
            w_real = self.left_video_container.winfo_width()
            h_real = self.left_video_container.winfo_height()

            if w_real <= 250:
                c_w = self.container.winfo_width()
                w_real = max(580, int(c_w * 0.6)) if c_w > 300 else 640

            if h_real <= 150:
                c_h = self.container.winfo_height()
                h_real = max(380, c_h - 40) if c_h > 200 else 380

            avail_w = max(320, w_real - 20)
            avail_h = max(200, h_real - 85)
        except Exception:
            avail_w, avail_h = 640, 360

        orig_w = getattr(self, "_video_orig_w", 1920) or 1920
        orig_h = getattr(self, "_video_orig_h", 1080) or 1080

        ratio = min(avail_w / max(1, orig_w), avail_h / max(1, orig_h))
        scaled_w = max(320, int(orig_w * ratio))
        scaled_h = max(180, int(orig_h * ratio))

        return scaled_w, scaled_h

    def _render_poster_image(self):
        if hasattr(self, "_poster_pil_image") and self._poster_pil_image and hasattr(self, "lbl_video_display") and self.lbl_video_display.winfo_exists() and not self._is_playing_video:
            nw, nh = self._get_aspect_fitted_dimensions()
            resized = self._poster_pil_image.resize((nw, nh), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=resized, dark_image=resized, size=(nw, nh))
            self.lbl_video_display.configure(image=ctk_img, text="")

    def _load_video_metadata_and_poster(self):
        if not self.filepath or not os.path.exists(self.filepath):
            return

        self._video_duration = 0.0
        self._video_fps = 24.0
        self._video_orig_w = 1920
        self._video_orig_h = 1080

        target_filepath = self.filepath

        def _worker():
            v_duration = 0.0
            v_fps = 24.0
            v_orig_w = 1920
            v_orig_h = 1080
            res_str = "N/A"
            codec_str = "N/A"
            fps_str = "N/A"
            poster_pil = None

            try:
                cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,r_frame_rate,codec_name:format=duration",
                    "-of", "default=noprint_wrappers=1",
                    target_filepath
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3, **_get_subprocess_kwargs())
                if res.returncode == 0:
                    lines = res.stdout.strip().split("\n")
                    probe_data = {}
                    for line in lines:
                        if "=" in line:
                            k, v = line.split("=", 1)
                            probe_data[k.strip()] = v.strip()

                    w = probe_data.get("width", "")
                    h = probe_data.get("height", "")
                    if w and h:
                        v_orig_w = int(w)
                        v_orig_h = int(h)
                        res_str = f"{w} × {h} px"

                    codec_str = probe_data.get("codec_name", "Unknown").upper()
                    fps_eval = probe_data.get("r_frame_rate", "")
                    if "/" in fps_eval:
                        num, den = map(float, fps_eval.split("/"))
                        if den > 0:
                            v_fps = num / den
                            fps_str = f"{v_fps:.2f} fps"

                    dur = probe_data.get("duration", "")
                    if dur:
                        v_duration = float(dur)
            except Exception:
                pass

            try:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                    tmp_thumb_path = tmp_file.name

                cmd_thumb = [
                    "ffmpeg", "-y", "-ss", "00:00:00", "-i", target_filepath,
                    "-vframes", "1", "-vf", "scale=1280:-1", tmp_thumb_path
                ]
                subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4, **_get_subprocess_kwargs())
                if os.path.exists(tmp_thumb_path) and os.path.getsize(tmp_thumb_path) > 0:
                    with Image.open(tmp_thumb_path) as img:
                        poster_pil = img.copy()
                    os.remove(tmp_thumb_path)
            except Exception:
                pass

            def _apply():
                if getattr(self, "filepath", "") != target_filepath:
                    return
                self._video_duration = v_duration
                self._video_fps = v_fps
                self._video_orig_w = v_orig_w
                self._video_orig_h = v_orig_h

                specs_text = (
                    f"• Đơn vị tệp: {os.path.basename(target_filepath)}\n\n"
                    f"• Thời lượng: {self._format_seconds(v_duration)}\n\n"
                    f"• Độ phân giải: {res_str}\n\n"
                    f"• Chuẩn nén (Codec): {codec_str}\n\n"
                    f"• Tốc độ khung hình: {fps_str}\n\n"
                    f"• Đường dẫn tệp:\n  {target_filepath}"
                )
                if hasattr(self, "lbl_video_specs") and self.lbl_video_specs.winfo_exists():
                    self.lbl_video_specs.configure(text=specs_text)

                if hasattr(self, "lbl_video_time") and self.lbl_video_time.winfo_exists():
                    self.lbl_video_time.configure(text=f"00:00 / {self._format_seconds(v_duration)}")

                if poster_pil:
                    self._poster_pil_image = poster_pil
                    self._render_poster_image()

            if hasattr(self, "after"):
                try:
                    self.after(0, _apply)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_video_playback(self):
        if self._is_playing_video:
            self._pause_video()
        else:
            self._play_video()

    def _start_video_audio(self, start_sec: float = 0.0):
        self._stop_video_audio()
        if not self.filepath or not os.path.exists(self.filepath):
            return

        cmd = [
            "ffplay", "-nodisp", "-autoexit",
            "-ss", str(start_sec),
            self.filepath
        ]
        try:
            self.video_audio_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_get_subprocess_kwargs()
            )
        except Exception:
            self.video_audio_proc = None

    def _stop_video_audio(self):
        if hasattr(self, "video_audio_proc") and self.video_audio_proc:
            try:
                self.video_audio_proc.terminate()
                self.video_audio_proc.kill()
                self.video_audio_proc.wait(timeout=1)
            except Exception:
                pass
            self.video_audio_proc = None

    def _play_video(self):
        if not self.filepath or not os.path.exists(self.filepath):
            return

        if self._video_paused:
            self.video_decoder.resume()
            self._video_paused = False
            self._is_playing_video = True
        else:
            scaled_w, scaled_h = self._get_aspect_fitted_dimensions()
            self.video_decoder.start(
                self.filepath,
                start_sec=self._video_current_sec,
                render_w=scaled_w,
                render_h=scaled_h,
                fps=self._video_fps
            )
            self._start_video_audio(self._video_current_sec)
            self._is_playing_video = True
            self._video_paused = False

        self.btn_toggle_video_play.configure(
            text="⏸ Tạm Dừng",
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER
        )
        self.btn_stop_video.configure(state="normal", fg_color=theme.ACCENT_DANGER, hover_color=theme.ACCENT_DANGER_HOVER)

        self._video_frame_tick()

    def _pause_video(self):
        if self._is_playing_video:
            self.video_decoder.pause()
            self._stop_video_audio()
            self._video_paused = True
            self._is_playing_video = False

            self.btn_toggle_video_play.configure(
                text="▶ Phát Video",
                fg_color=theme.ACCENT_PRIMARY,
                hover_color=theme.ACCENT_PRIMARY_HOVER
            )

    def _stop_video(self):
        self.video_decoder.stop()
        self._stop_video_audio()
        self._is_playing_video = False
        self._video_paused = False
        self._video_current_sec = 0.0

        if hasattr(self, "btn_toggle_video_play") and self.btn_toggle_video_play.winfo_exists():
            self.btn_toggle_video_play.configure(
                text="▶ Phát Video",
                fg_color=theme.ACCENT_PRIMARY,
                hover_color=theme.ACCENT_PRIMARY_HOVER
            )
            self.btn_stop_video.configure(state="disabled", fg_color=theme.CARD_BG)
            self.slider_video_seek.set(0)
            self.lbl_video_time.configure(text=f"00:00 / {self._format_seconds(self._video_duration)}")

        if self._video_tick_job:
            try:
                self.after_cancel(self._video_tick_job)
            except Exception:
                pass
            self._video_tick_job = None

    def _on_video_seek(self, val):
        if self._video_duration > 0:
            target_sec = (val / 100.0) * self._video_duration
            self._video_current_sec = target_sec

            if self._is_playing_video or self._video_paused:
                scaled_w, scaled_h = self._get_aspect_fitted_dimensions()
                self.video_decoder.start(
                    self.filepath,
                    start_sec=target_sec,
                    render_w=scaled_w,
                    render_h=scaled_h,
                    fps=self._video_fps
                )
                if self._is_playing_video:
                    self._start_video_audio(target_sec)
                elif self._video_paused:
                    self.video_decoder.pause()

    def _video_frame_tick(self):
        if not self._is_playing_video or not hasattr(self, "lbl_video_display") or not self.lbl_video_display.winfo_exists():
            return

        if not self.video_decoder.queue.empty():
            try:
                img, curr_t = self.video_decoder.queue.get_nowait()
                self._video_current_sec = curr_t
                w, h = img.size
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                self.lbl_video_display.configure(image=ctk_img, text="")

                if self._video_duration > 0:
                    pct = (curr_t / self._video_duration) * 100.0
                    self.slider_video_seek.set(pct)
                    self.lbl_video_time.configure(
                        text=f"{self._format_seconds(curr_t)} / {self._format_seconds(self._video_duration)}"
                    )
            except Exception:
                pass

        delay_ms = max(10, int(1000.0 / max(1.0, self._video_fps)))
        self._video_tick_job = self.after(delay_ms, self._video_frame_tick)

    # -----------------------------------------------------------------
    # 4. DOCUMENT / LOG PREVIEW
    # -----------------------------------------------------------------
    def _build_document_preview(self):
        text_box = ctk.CTkTextbox(
            self.container,
            fg_color="#101214",
            text_color=theme.TEXT_MAIN,
            font=("Consolas", 11),
            corner_radius=6,
            wrap="word"
        )
        text_box.pack(fill="both", expand=True)

        try:
            with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(50000)
                text_box.insert("1.0", content)
        except Exception as e:
            text_box.insert("1.0", f"❌ Lỗi khi đọc tệp văn bản: {e}")

        text_box.configure(state="disabled")

    # -----------------------------------------------------------------
    # 5. GENERIC PREVIEW
    # -----------------------------------------------------------------
    def _build_generic_preview(self):
        card = ctk.CTkFrame(self.container, fg_color=theme.PANEL_BG, corner_radius=8)
        card.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(card, text="📄", font=(theme.FONT_FAMILY, 64)).pack(pady=(40, 10))

        ctk.CTkLabel(
            card,
            text=os.path.basename(self.filepath),
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_MAIN
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            card,
            text=f"Đường dẫn: {self.filepath}",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.TEXT_MUTED
        ).pack(pady=(0, 20))

        btn_open = ctk.CTkButton(
            card,
            text="📂 Mở Tệp Bằng Ứng Dụng Mặc Định",
            font=(theme.FONT_FAMILY, 12, "bold"),
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            height=38,
            command=self._open_in_system_player
        )
        btn_open.pack()

    # -----------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------
    def _open_containing_folder(self):
        if not self.filepath:
            return
        folder = os.path.dirname(self.filepath)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _copy_path_to_clipboard(self):
        if not self.filepath:
            return
        self.clipboard_clear()
        self.clipboard_append(self.filepath)
        self.update()

    def _open_in_system_player(self):
        if not self.filepath:
            return
        try:
            if sys.platform == "win32":
                os.startfile(self.filepath)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.filepath])
            else:
                subprocess.Popen(["xdg-open", self.filepath])
        except Exception:
            pass

    def destroy(self):
        self._stop_all_playback()
        for job_attr in ("_audio_update_job", "_video_tick_job"):
            job_id = getattr(self, job_attr, None)
            if job_id:
                try:
                    self.after_cancel(job_id)
                except Exception:
                    pass
                setattr(self, job_attr, None)
        super().destroy()

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
