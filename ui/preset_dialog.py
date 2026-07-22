import customtkinter as ctk
import ui.theme as theme


class SavePresetDialog(ctk.CTkToplevel):
    """
    Modal dialog for saving a new Preset.
    """

    def __init__(self, parent, on_save_callback, existing_names=None):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.existing_names = existing_names or []

        self.title("Lưu Preset Cấu Hình")
        self.geometry("400x240")
        self.resizable(False, False)
        self.configure(fg_color=theme.PANEL_BG)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        lbl = ctk.CTkLabel(
            self,
            text="Nhập tên Preset mới:",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl.pack(padx=20, pady=(20, 10), anchor="w")

        self.entry_name = ctk.CTkEntry(
            self,
            placeholder_text="Ví dụ: ARRI ALEXA Mini LF - 4K...",
            fg_color=theme.CARD_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            height=36
        )
        self.entry_name.pack(padx=20, pady=5, fill="x")

        self.lbl_error = ctk.CTkLabel(
            self,
            text="",
            font=(theme.FONT_FAMILY, 11),
            text_color=theme.ACCENT_DANGER
        )
        self.lbl_error.pack(padx=20, pady=(0, 5), anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=15, fill="x")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Hủy",
            width=90,
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(10, 0))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="Lưu",
            width=90,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._on_save
        )
        btn_save.pack(side="right")

    def _on_save(self):
        name = self.entry_name.get().strip()
        if not name:
            self.lbl_error.configure(text="Tên preset không được để trống!")
            return
        if name.lower() in [n.lower() for n in self.existing_names]:
            self.lbl_error.configure(text="Tên preset đã tồn tại!")
            return
        self.on_save_callback(name)
        self.destroy()


class DeletePresetDialog(ctk.CTkToplevel):
    """
    Modal confirmation dialog for deleting an existing Preset.
    """

    def __init__(self, parent, preset_name: str, on_delete_callback):
        super().__init__(parent)
        self.preset_name = preset_name
        self.on_delete_callback = on_delete_callback

        self.title("Xóa Preset Cấu Hình")
        self.geometry("420x210")
        self.resizable(False, False)
        self.configure(fg_color=theme.PANEL_BG)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        lbl = ctk.CTkLabel(
            self,
            text="⚠️ Xác Nhận Xóa Preset",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.ACCENT_DANGER
        )
        lbl.pack(padx=20, pady=(20, 8), anchor="w")

        lbl_desc = ctk.CTkLabel(
            self,
            text=f"Bạn có chắc chắn muốn xóa Preset '{self.preset_name}' không?\nHành động này không thể hoàn tác.",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MAIN,
            justify="left",
            wraplength=380
        )
        lbl_desc.pack(padx=20, pady=5, anchor="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=20, fill="x")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Hủy Bỏ",
            width=90,
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(10, 0))

        btn_delete = ctk.CTkButton(
            btn_frame,
            text="🗑️ Xóa Preset",
            width=110,
            fg_color=theme.ACCENT_DANGER,
            hover_color=theme.ACCENT_DANGER_HOVER,
            command=self._on_delete
        )
        btn_delete.pack(side="right")

    def _on_delete(self):
        self.on_delete_callback(self.preset_name)
        self.destroy()
