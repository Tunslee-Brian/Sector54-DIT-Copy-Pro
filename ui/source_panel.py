import customtkinter as ctk
from tkinter import filedialog
import os
import ui.theme as theme

class SourcePanel(ctk.CTkFrame):
    """
    Compact Panel for selecting camera card source directory (VS Code style).
    """

    def __init__(self, master, on_source_changed_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)
        self.on_source_changed = on_source_changed_callback
        self.source_path = ""

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Path Entry
        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="Chọn thư mục Nguồn (DCIM / Card)...",
            fg_color=theme.CARD_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            font=(theme.FONT_FAMILY, 11),
            height=28
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)

        # Browse Button
        self.btn_browse = ctk.CTkButton(
            self,
            text="+",
            width=32,
            height=28,
            font=(theme.FONT_FAMILY, 14, "bold"),
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._browse_folder
        )
        self.btn_browse.grid(row=0, column=1, sticky="e", pady=2)

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn Thư Mục Thẻ Nhớ Nguồn")
        if folder:
            self.set_source_path(folder)

    def set_source_path(self, path: str):
        self.source_path = os.path.abspath(path)
        self.entry.delete(0, "end")
        self.entry.insert(0, self.source_path)
        if self.on_source_changed:
            self.on_source_changed(self.source_path)

    def get_source_path(self) -> str:
        return self.entry.get().strip()
