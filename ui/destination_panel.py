import customtkinter as ctk
from tkinter import filedialog
import os
import ui.theme as theme

class DestinationPanel(ctk.CTkFrame):
    """
    Compact Panel for selecting multiple backup destination directories (VS Code style).
    """

    def __init__(self, master, on_destinations_changed_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)
        self.on_destinations_changed = on_destinations_changed_callback
        self.destination_rows = []

        self._build_ui()
        self._add_destination_row(notify=False)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Header Action Bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
        header.grid_columnconfigure(0, weight=1)

        btn_add = ctk.CTkButton(
            header,
            text="+ Thêm Ổ Đích",
            width=90,
            height=24,
            font=(theme.FONT_FAMILY, 10, "bold"),
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self._add_destination_row
        )
        btn_add.grid(row=0, column=1, sticky="e")

        # Container for destination rows
        self.rows_container = ctk.CTkFrame(self, fg_color="transparent")
        self.rows_container.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self.rows_container.grid_columnconfigure(0, weight=1)

    def _add_destination_row(self, initial_path: str = "", notify: bool = True):
        row_idx = len(self.destination_rows)

        entry = ctk.CTkEntry(
            self.rows_container,
            placeholder_text=f"Đường dẫn Đích #{row_idx + 1}...",
            fg_color=theme.CARD_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            font=(theme.FONT_FAMILY, 11),
            height=26
        )
        if initial_path:
            entry.insert(0, initial_path)
        entry.grid(row=row_idx, column=0, sticky="ew", padx=(0, 4), pady=2)

        btn_browse = ctk.CTkButton(
            self.rows_container,
            text="+",
            width=32,
            height=26,
            font=(theme.FONT_FAMILY, 13, "bold"),
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=lambda e=entry: self._browse_folder(e)
        )
        btn_browse.grid(row=row_idx, column=1, sticky="e", padx=(0, 2), pady=2)

        # Delete button if row > 0
        btn_del = None
        if row_idx > 0:
            row_data = {"entry": entry, "browse": btn_browse, "delete": None}
            btn_del = ctk.CTkButton(
                self.rows_container,
                text="✕",
                width=24,
                height=26,
                font=(theme.FONT_FAMILY, 10, "bold"),
                fg_color=theme.ACCENT_DANGER,
                hover_color=theme.ACCENT_DANGER_HOVER,
                command=lambda r=row_data: self._remove_destination_row(r)
            )
            btn_del.grid(row=row_idx, column=2, sticky="e", pady=2)
            row_data["delete"] = btn_del

        self.destination_rows.append({
            "entry": entry,
            "browse": btn_browse,
            "delete": btn_del
        })

        if notify:
            self._notify_changed()

    def _remove_destination_row(self, row_data: dict):
        if row_data in self.destination_rows:
            for key, w in row_data.items():
                if w:
                    w.destroy()
            self.destination_rows.remove(row_data)
            self._rebuild_grid()
            self._notify_changed()

    def _rebuild_grid(self):
        for idx, row in enumerate(self.destination_rows):
            row["entry"].grid(row=idx, column=0, sticky="ew", padx=(0, 4), pady=2)
            row["browse"].grid(row=idx, column=1, sticky="e", padx=(0, 2), pady=2)
            if row["delete"]:
                row["delete"].grid(row=idx, column=2, sticky="e", pady=2)
                row["delete"].configure(command=lambda r=row: self._remove_destination_row(r))

    def _browse_folder(self, entry_widget: ctk.CTkEntry):
        folder = filedialog.askdirectory(title="Chọn Thư Mục Lưu Trữ Đích")
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, os.path.abspath(folder))
            self._notify_changed()

    def get_destinations(self) -> list[str]:
        paths = []
        for row in self.destination_rows:
            val = row["entry"].get().strip()
            if val:
                paths.append(val)
        return paths

    def _notify_changed(self):
        if self.on_destinations_changed:
            self.on_destinations_changed(self.get_destinations())
