import customtkinter as ctk
import ui.theme as theme

class FileStatusTable(ctk.CTkFrame):
    """
    Scrollable real-time file status list with color-coded badges.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=theme.PANEL_BG, corner_radius=10, **kwargs)
        self.file_rows = {}
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text="[5] BẢNG THEO DÕI TRẠNG THÁI FILE THỜI GIAN THỰC",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        # Scrollable Frame for file items
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.CARD_BG,
            corner_radius=8
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 12))
        self.scroll_frame.grid_columnconfigure(1, weight=1)

    def populate_files(self, file_list: list[dict]):
        # Clear existing rows
        for row_dict in self.file_rows.values():
            for widget in row_dict.values():
                widget.destroy()
        self.file_rows.clear()

        for idx, f in enumerate(file_list):
            rel_path = f["rel_path"]
            filename = f["filename"]
            size_gb = f["size"] / (1024 * 1024 * 1024)

            # Badge Label
            badge = ctk.CTkLabel(
                self.scroll_frame,
                text="[░ QUEUED  ]",
                font=(theme.FONT_FAMILY, 11, "bold"),
                text_color=theme.COLOR_QUEUED,
                width=110,
                anchor="w"
            )
            badge.grid(row=idx, column=0, sticky="w", padx=(8, 4), pady=4)

            # File Info Label
            info = ctk.CTkLabel(
                self.scroll_frame,
                text=f"{filename} ({size_gb:.2f} GB) - Đang chờ xử lý...",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.TEXT_MAIN,
                anchor="w"
            )
            info.grid(row=idx, column=1, sticky="ew", padx=4, pady=4)

            self.file_rows[rel_path] = {
                "badge": badge,
                "info": info
            }

            # If already verified/failed in initial state
            if f.get("status") != "QUEUED":
                self.update_file_status(f)

    def update_file_status(self, file_info: dict):
        rel_path = file_info["rel_path"]
        if rel_path not in self.file_rows:
            return

        row = self.file_rows[rel_path]
        status = file_info.get("status", "QUEUED")
        fname = file_info.get("filename", "")
        size_gb = file_info.get("size", 0) / (1024 * 1024 * 1024)
        hash_val = file_info.get("source_hash", "")
        hash_short = hash_val[:10] + "..." if len(hash_val) > 10 else hash_val

        if status == "VERIFIED":
            row["badge"].configure(text="[✓ VERIFIED]", text_color=theme.COLOR_VERIFIED)
            row["info"].configure(
                text=f"{fname} ({size_gb:.2f} GB) - Hash: {hash_short} - Trùng khớp 100%",
                text_color=theme.COLOR_VERIFIED
            )
        elif status == "COPYING":
            row["badge"].configure(text="[▶ COPYING ]", text_color=theme.COLOR_COPYING)
            row["info"].configure(
                text=f"{fname} ({size_gb:.2f} GB) - Đang ghi dữ liệu & tính checksum...",
                text_color=theme.COLOR_COPYING
            )
        elif status == "FAILED":
            err = file_info.get("error_msg", "Checksum mismatch!")
            row["badge"].configure(text="[✗ FAILED  ]", text_color=theme.COLOR_FAILED)
            row["info"].configure(
                text=f"{fname} ({size_gb:.2f} GB) - {err}",
                text_color=theme.COLOR_FAILED
            )
        else:
            row["badge"].configure(text="[░ QUEUED  ]", text_color=theme.COLOR_QUEUED)
            row["info"].configure(
                text=f"{fname} ({size_gb:.2f} GB) - Đang chờ xử lý...",
                text_color=theme.TEXT_MUTED
            )

    def populate_extra_files(self, extra_files: list[dict]):
        if not extra_files:
            return
        base_row = len(self.file_rows)
        for idx, ef in enumerate(extra_files, start=base_row):
            rel_path = ef.get("rel_path", ef.get("filename", ""))
            filename = ef.get("filename", "")
            size_mb = ef.get("size", 0) / (1024 * 1024)

            badge = ctk.CTkLabel(
                self.scroll_frame,
                text="[⚠ EXTRA  ]",
                font=(theme.FONT_FAMILY, 11, "bold"),
                text_color=theme.ACCENT_WARNING,
                width=110,
                anchor="w"
            )
            badge.grid(row=idx, column=0, sticky="w", padx=(8, 4), pady=4)

            info = ctk.CTkLabel(
                self.scroll_frame,
                text=f"{filename} ({size_mb:.2f} MB) - File thừa ở ổ đích (Không có trên thẻ Nguồn)",
                font=(theme.FONT_FAMILY, 12),
                text_color=theme.ACCENT_WARNING,
                anchor="w"
            )
            info.grid(row=idx, column=1, sticky="ew", padx=4, pady=4)

            self.file_rows[f"extra_{rel_path}"] = {
                "badge": badge,
                "info": info
            }

    def clear(self):
        """Clear all file status rows from table."""
        for row_dict in self.file_rows.values():
            for widget in row_dict.values():
                try:
                    widget.destroy()
                except Exception:
                    pass
        self.file_rows.clear()

