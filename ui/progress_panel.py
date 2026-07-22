import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import time
import ui.theme as theme


class ShotPutProgressPanel(ctk.CTkFrame):
    """
    ShotPut Pro Dual-Card Progress Panel with resizable splitter bar.
    Left Card: Job Summary (Time Elapsed, Time Remaining, Size, Files, Phase Status Checklist).
    Right Card: Phase Progress Bars (Replication Green Bar, Verify Blue Bar, Metadata, Report).
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.start_time = None
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # -------------------------------------------------------------
        # Left Card: Job Details & Checklist
        # -------------------------------------------------------------
        left_card = ctk.CTkFrame(self.paned, fg_color=theme.CARD_BG, corner_radius=0, border_width=1, border_color=theme.CARD_BORDER)
        left_card.grid_columnconfigure(0, weight=1)
        self.paned.add(left_card, weight=1)

        # Job Name
        self.lbl_job_name = ctk.CTkLabel(
            left_card,
            text="◯ Chưa có Job",
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color=theme.TEXT_MAIN,
            anchor="w"
        )
        self.lbl_job_name.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 8))

        # Specs grid (Elapsed, Remaining, Size, Files, Folders, Speed)
        specs_frame = ctk.CTkFrame(left_card, fg_color="transparent")
        specs_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=0)

        self.lbl_elapsed = self._add_spec_row(specs_frame, 0, "Time Elapsed", "00:00:00")
        self.lbl_remaining = self._add_spec_row(specs_frame, 1, "Time Remaining", "00:00:00")
        self.lbl_size = self._add_spec_row(specs_frame, 2, "Size", "0.00 GB")
        self.lbl_files = self._add_spec_row(specs_frame, 3, "Files", "0")
        self.lbl_folders = self._add_spec_row(specs_frame, 4, "Folders", "0")
        self.lbl_speed = self._add_spec_row(specs_frame, 5, "Speed", "0.0 MB/s")

        # Checklist overview
        chk_frame = ctk.CTkFrame(left_card, fg_color="transparent")
        chk_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(6, 8))

        self.lbl_chk_repl = ctk.CTkLabel(chk_frame, text="Replication 0%", font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_MUTED, anchor="w", height=20)
        self.lbl_chk_repl.pack(fill="x", pady=0)

        self.lbl_chk_verify = ctk.CTkLabel(chk_frame, text="Verify 0%", font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_MUTED, anchor="w", height=20)
        self.lbl_chk_verify.pack(fill="x", pady=0)

        self.lbl_chk_meta = ctk.CTkLabel(chk_frame, text="Metadata 0%", font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_MUTED, anchor="w", height=20)
        self.lbl_chk_meta.pack(fill="x", pady=0)

        self.lbl_chk_report = ctk.CTkLabel(chk_frame, text="Report Pending", font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_MUTED, anchor="w", height=20)
        self.lbl_chk_report.pack(fill="x", pady=0)

        # -------------------------------------------------------------
        # Right Card: Phase Progress Bars (Replication & Verify)
        # -------------------------------------------------------------
        right_card = ctk.CTkFrame(self.paned, fg_color=theme.CARD_BG, corner_radius=0, border_width=1, border_color=theme.CARD_BORDER)
        right_card.grid_columnconfigure(0, weight=1)
        self.paned.add(right_card, weight=1)

        # Padding container
        progress_container = ctk.CTkFrame(right_card, fg_color="transparent")
        progress_container.pack(fill="both", expand=True, padx=18, pady=16)
        progress_container.grid_columnconfigure(0, weight=1)

        # ---------------- Phase 1: Replication ----------------
        repl_hdr = ctk.CTkFrame(progress_container, fg_color="transparent")
        repl_hdr.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        lbl_r_title = ctk.CTkLabel(
            repl_hdr,
            text="🟢 Replication (Sao Chép Dữ Liệu)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_r_title.pack(side="left")

        self.lbl_repl_pct = ctk.CTkLabel(
            repl_hdr,
            text="0%",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.ACCENT_REPLICATION
        )
        self.lbl_repl_pct.pack(side="right")

        self.bar_replication = ctk.CTkProgressBar(
            progress_container,
            fg_color=theme.PANEL_BG,
            progress_color=theme.PANEL_BG,
            height=24,
            corner_radius=4
        )
        self.bar_replication.set(0.0)
        self.bar_replication.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        self.lbl_repl_stats = ctk.CTkLabel(
            progress_container,
            text="0.00 GB / 0.00 GB",
            font=(theme.FONT_FAMILY, 10),
            text_color=theme.TEXT_MUTED
        )
        self.lbl_repl_stats.grid(row=2, column=0, sticky="e", pady=(0, 16))

        # ---------------- Phase 2: Verify ----------------
        verify_hdr = ctk.CTkFrame(progress_container, fg_color="transparent")
        verify_hdr.grid(row=3, column=0, sticky="ew", pady=(0, 4))

        lbl_v_title = ctk.CTkLabel(
            verify_hdr,
            text="🔵 Checksum Verify (Xác Thực File)",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_v_title.pack(side="left")

        self.lbl_verify_pct = ctk.CTkLabel(
            verify_hdr,
            text="0%",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        self.lbl_verify_pct.pack(side="right")

        self.bar_verify = ctk.CTkProgressBar(
            progress_container,
            fg_color=theme.PANEL_BG,
            progress_color=theme.PANEL_BG,
            height=24,
            corner_radius=4
        )
        self.bar_verify.set(0.0)
        self.bar_verify.grid(row=4, column=0, sticky="ew", pady=(0, 4))

        self.lbl_verify_stats = ctk.CTkLabel(
            progress_container,
            text="0 / 0 Files Verified",
            font=(theme.FONT_FAMILY, 10),
            text_color=theme.TEXT_MUTED
        )
        self.lbl_verify_stats.grid(row=5, column=0, sticky="e", pady=(0, 4))

    def _add_spec_row(self, parent, row, label_text, default_val):
        lbl_title = ctk.CTkLabel(parent, text=f"{label_text}", font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_MUTED, anchor="w", width=110, height=20)
        lbl_title.grid(row=row, column=0, sticky="w", pady=0)

        lbl_val = ctk.CTkLabel(parent, text=default_val, font=(theme.FONT_FAMILY, 11, "bold"), text_color=theme.TEXT_MAIN, anchor="w", height=20)
        lbl_val.grid(row=row, column=1, sticky="w", pady=0)
        return lbl_val

    def set_job_info(self, job_name: str, total_bytes: int, file_count: int, folder_count: int = 0):
        """Set initial job parameters when scanning completes."""
        self.start_time = time.time()
        self.lbl_job_name.configure(text=f"◯ {job_name}")

        gb_size = total_bytes / (1024**3)
        if gb_size >= 1.0:
            self.lbl_size.configure(text=f"{gb_size:.2f} GB")
        else:
            mb_size = total_bytes / (1024**2)
            self.lbl_size.configure(text=f"{mb_size:.2f} MB")

        self.lbl_files.configure(text=str(file_count))
        self.lbl_folders.configure(text=str(folder_count))

        self.lbl_repl_stats.configure(text=f"0.00 GB / {gb_size:.2f} GB")
        self.lbl_verify_stats.configure(text=f"0 / {file_count} Files Verified")

    def update_file_progress(self, filename: str, file_bytes_read: int, file_total_bytes: int, speed_bytes_sec: float, eta_sec: float):
        """Update current file speed and remaining time."""
        if self.start_time:
            elapsed = max(0.1, time.time() - self.start_time)
            m, s = divmod(int(elapsed), 60)
            h, m = divmod(m, 60)
            self.lbl_elapsed.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

            if speed_bytes_sec <= 0 and hasattr(self, "_last_copied_bytes") and self._last_copied_bytes > 0:
                speed_bytes_sec = self._last_copied_bytes / elapsed

            if eta_sec <= 0 and hasattr(self, "_last_copied_bytes") and hasattr(self, "_last_total_bytes"):
                rem_bytes = max(0, self._last_total_bytes - self._last_copied_bytes)
                if speed_bytes_sec > 0 and rem_bytes > 0:
                    eta_sec = rem_bytes / speed_bytes_sec

        if eta_sec > 0:
            eta_m, eta_s = divmod(int(eta_sec), 60)
            eta_h, eta_m = divmod(eta_m, 60)
            self.lbl_remaining.configure(text=f"{eta_h:02d}:{eta_m:02d}:{eta_s:02d}")
        else:
            if hasattr(self, "_last_copied_bytes") and hasattr(self, "_last_total_bytes") and self._last_copied_bytes >= self._last_total_bytes:
                self.lbl_remaining.configure(text="finishing up...")

        if speed_bytes_sec > 0:
            speed_mb = speed_bytes_sec / (1024 * 1024)
            if speed_mb >= 1024:
                self.lbl_speed.configure(text=f"{speed_mb / 1024:.2f} GB/s")
            else:
                self.lbl_speed.configure(text=f"{speed_mb:.1f} MB/s")

    def update_total_progress(self, copied_bytes: int, total_bytes: int, verified_files: int, total_files: int, metadata_pct: int = 0):
        """Update Replication & Verify bars."""
        self._last_copied_bytes = copied_bytes
        self._last_total_bytes = total_bytes

        # Continuously update overall speed and remaining time if start_time is set
        if self.start_time:
            elapsed = max(0.1, time.time() - self.start_time)
            m, s = divmod(int(elapsed), 60)
            h, m = divmod(m, 60)
            self.lbl_elapsed.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

            avg_speed = copied_bytes / elapsed
            if avg_speed > 0:
                speed_mb = avg_speed / (1024 * 1024)
                if speed_mb >= 1024:
                    self.lbl_speed.configure(text=f"{speed_mb / 1024:.2f} GB/s")
                else:
                    self.lbl_speed.configure(text=f"{speed_mb:.1f} MB/s")

                rem_bytes = max(0, total_bytes - copied_bytes)
                if rem_bytes > 0:
                    eta_sec = rem_bytes / avg_speed
                    eta_m, eta_s = divmod(int(eta_sec), 60)
                    eta_h, eta_m = divmod(eta_m, 60)
                    self.lbl_remaining.configure(text=f"{eta_h:02d}:{eta_m:02d}:{eta_s:02d}")
                elif verified_files == total_files:
                    self.lbl_remaining.configure(text="finishing up...")

        # 1. Replication progress
        repl_frac = copied_bytes / max(1, total_bytes)
        repl_frac_clamped = min(1.0, max(0.0, repl_frac))
        self.bar_replication.set(repl_frac_clamped)

        if repl_frac_clamped > 0.0:
            self.bar_replication.configure(progress_color=theme.ACCENT_REPLICATION)
        else:
            self.bar_replication.configure(progress_color=theme.PANEL_BG)

        repl_pct = int(repl_frac * 100)
        self.lbl_chk_repl.configure(text=f"Replication {repl_pct}%")
        self.lbl_repl_pct.configure(text=f"{repl_pct}%")

        copied_gb = copied_bytes / (1024**3)
        total_gb = total_bytes / (1024**3)
        if total_gb >= 1.0:
            self.lbl_repl_stats.configure(text=f"{copied_gb:.2f} GB / {total_gb:.2f} GB")
        else:
            copied_mb = copied_bytes / (1024**2)
            total_mb = total_bytes / (1024**2)
            self.lbl_repl_stats.configure(text=f"{copied_mb:.1f} MB / {total_mb:.1f} MB")

        # 2. Verify progress
        verify_frac = verified_files / max(1, total_files)
        verify_frac_clamped = min(1.0, max(0.0, verify_frac))
        self.bar_verify.set(verify_frac_clamped)

        if verify_frac_clamped > 0.0:
            self.bar_verify.configure(progress_color=theme.ACCENT_PRIMARY)
        else:
            self.bar_verify.configure(progress_color=theme.PANEL_BG)

        verify_pct = int(verify_frac * 100)
        self.lbl_chk_verify.configure(text=f"Verify {verify_pct}%")
        self.lbl_verify_pct.configure(text=f"{verify_pct}%")
        self.lbl_verify_stats.configure(text=f"{verified_files} / {total_files} Files Verified")

        # 3. Metadata progress (Checklist on left)
        meta_pct = metadata_pct if metadata_pct > 0 else (repl_pct if repl_pct < 100 else (100 if verify_pct == 100 else repl_pct))
        self.lbl_chk_meta.configure(text=f"Metadata {meta_pct}%")

        # 4. Report progress (Checklist on left)
        if verify_pct == 100:
            self.lbl_chk_report.configure(text="Report Complete ✓", text_color=theme.ACCENT_REPLICATION)
            self.lbl_remaining.configure(text="finishing up...")
        else:
            self.lbl_chk_report.configure(text="Report Pending", text_color=theme.TEXT_MUTED)

    def reset(self):
        self.start_time = None
        self.lbl_job_name.configure(text="◯ Chưa có Job")
        self.lbl_elapsed.configure(text="00:00:00")
        self.lbl_remaining.configure(text="00:00:00")
        self.lbl_size.configure(text="0.00 GB")
        self.lbl_files.configure(text="0")
        self.lbl_folders.configure(text="0")
        self.lbl_speed.configure(text="0.0 MB/s")
        self.lbl_chk_repl.configure(text="Replication 0%", text_color=theme.TEXT_MUTED)
        self.lbl_chk_verify.configure(text="Verify 0%", text_color=theme.TEXT_MUTED)
        self.lbl_chk_meta.configure(text="Metadata 0%", text_color=theme.TEXT_MUTED)
        self.lbl_chk_report.configure(text="Report Pending", text_color=theme.TEXT_MUTED)

        self.bar_replication.configure(progress_color=theme.PANEL_BG)
        self.bar_replication.set(0.0)
        self.bar_verify.configure(progress_color=theme.PANEL_BG)
        self.bar_verify.set(0.0)
        self.lbl_repl_pct.configure(text="0%")
        self.lbl_verify_pct.configure(text="0%")
        self.lbl_repl_stats.configure(text="0.00 GB / 0.00 GB")
        self.lbl_verify_stats.configure(text="0 / 0 Files Verified")
