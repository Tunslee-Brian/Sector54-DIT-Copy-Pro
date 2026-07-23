import os
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
import ui.theme as theme
from core.preset_manager import PresetManager
from core.token_parser import format_date
from ui.config.color_syntax_entry import ColorSyntaxEntry
from core.logger_config import logger


class ConfigPanel(ctk.CTkFrame):
    """
    Panel for configuring Naming Rules, Folder Templates, Hash Algorithms, and Buffer size.
    Features integrated Preset Management for deep customization (Preset Name, Description, Rules),
    live interactive preview for file naming structure (3 sample files + explanation)
    and output-aware folder structure tree view.
    """

    AVAILABLE_TOKENS = [
        ("{Camera}", "Chỉ số máy quay (A, B, C...)"),
        ("{Roll}", "Số cuộn / thẻ nhớ (001-999)"),
        ("{Clip}", "Số thứ tự clip (C001, C002...)"),
        ("{UID}", "Ký tự ngẫu nhiên (BB, AX, 5R...)"),
        ("{Date}", "Ngày ghi hình (YYMMDD)"),
        ("{Project}", "Tên dự án (Film Project)")
    ]

    FILE_TOKENS_WITH_LENGTH = {
        "{Camera}": "{Camera:1}",
        "{Roll}": "{Roll:3}",
        "{Clip}": "{Clip:3}",
        "{UID}": "{UID:2}",
        "{Date}": "{Date:YYMMDD}",
    }

    TOKEN_HELP_MAP = {
        "Camera": ("Chỉ số máy quay", "Ký tự A-Z (Ví dụ: A, B, C)"),
        "Roll": ("Số cuộn / thẻ nhớ", "3 chữ số 001-999"),
        "Clip": ("Số thứ tự clip", "Thường đi kèm 'C' (Ví dụ: C001)"),
        "UID": ("Ký tự ngẫu nhiên", "2 ký tự prevent trùng tên (Ví dụ: BB, 5R)"),
        "Date": ("Ngày ghi hình", "YYMMDD hoặc YYYYMMDD"),
        "Project": ("Tên dự án", "Để trống hoặc tự điền"),
        "Destination": ("Thư mục Output", "Ổ đĩa đích sao chép")
    }

    TOKEN_COLOR_MAP = {
        "Camera": "#42A5F5",
        "Roll": "#AB47BC",
        "Clip": "#FFA726",
        "UID": "#EC407A",
        "Date": "#66BB6A",
        "Project": "#26C6DA",
        "Destination": "#5C6BC0"
    }
    STATIC_TEXT_COLOR = "#90A4AE"
    EXT_TEXT_COLOR = "#78909C"

    def __init__(self, master, preset_manager: PresetManager = None, on_config_changed_callback=None, **kwargs):
        super().__init__(master, fg_color=theme.PANEL_BG, corner_radius=10, **kwargs)
        self.on_config_changed = on_config_changed_callback
        self.preset_manager = preset_manager or PresetManager()
        self.destinations: list[str] = []
        self.current_loaded_preset_name = None
        self._preview_timer = None
        self._last_rendered_file_pattern = None
        self._last_rendered_folder_pattern = None
        self._last_rendered_dests = None

        self._init_tree_style()
        self._build_ui()
        self._load_presets_to_combo()
        self._bind_mouse_wheel()
        self._update_all_previews(immediate=True)

    def _is_descendant(self, widget):
        curr = widget
        while curr:
            if curr == self:
                return True
            try:
                parent_name = curr.winfo_parent()
                if not parent_name:
                    break
                curr = curr.nametowidget(parent_name)
            except Exception:
                break
        return False

    def _bind_mouse_wheel(self):
        """Binds mouse wheel scrolling cross-platform (Linux/Windows/macOS) anywhere over panel and child widgets."""
        def _on_mouse_wheel(event):
            if not hasattr(self, "scroll_container") or not self.scroll_container:
                return

            try:
                top = self.winfo_toplevel()
                under = top.winfo_containing(event.x_root, event.y_root)
                if under and self._is_descendant(under):
                    canvas = self.scroll_container._parent_canvas
                    if event.num == 4 or (hasattr(event, "delta") and event.delta > 0):
                        canvas.yview_scroll(-3, "units")
                    elif event.num == 5 or (hasattr(event, "delta") and event.delta < 0):
                        canvas.yview_scroll(3, "units")
            except Exception:
                pass

        def _recursive_bind(w):
            try:
                w.bind("<Button-4>", _on_mouse_wheel, add="+")
                w.bind("<Button-5>", _on_mouse_wheel, add="+")
                w.bind("<MouseWheel>", _on_mouse_wheel, add="+")
            except Exception:
                pass
            try:
                for child in w.winfo_children():
                    _recursive_bind(child)
            except Exception:
                pass

        _recursive_bind(self)

    def _init_tree_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "ConfigTree.Treeview",
            background=theme.CARD_BG,
            foreground=theme.TEXT_MAIN,
            fieldbackground=theme.CARD_BG,
            bordercolor=theme.CARD_BG,
            relief="flat",
            borderwidth=0,
            rowheight=22,
            font=(theme.FONT_FAMILY, 9)
        )
        style.map(
            "ConfigTree.Treeview",
            background=[("selected", theme.ACCENT_PRIMARY)],
            foreground=[("selected", "#ffffff")]
        )

    def _init_tree_tags(self):
        """Configure color tags for Output Folder Structure Treeview."""
        if hasattr(self, "tree_folder_preview"):
            self.tree_folder_preview.tag_configure("Destination", foreground="#7986CB")  # Soft Indigo
            self.tree_folder_preview.tag_configure("Camera", foreground="#42A5F5")       # Bright Blue
            self.tree_folder_preview.tag_configure("Roll", foreground="#AB47BC")         # Vibrant Purple
            self.tree_folder_preview.tag_configure("Date", foreground="#66BB6A")         # Fresh Green
            self.tree_folder_preview.tag_configure("Project", foreground="#26C6DA")      # Cyan
            self.tree_folder_preview.tag_configure("Clip", foreground="#FFA726")         # Warm Orange
            self.tree_folder_preview.tag_configure("UID", foreground="#EC407A")          # Vibrant Pink
            self.tree_folder_preview.tag_configure("StaticFolder", foreground="#B0BEC5") # Blue Gray
            self.tree_folder_preview.tag_configure("SampleFile", foreground="#81C784")   # Soft Green for file samples

    def set_destinations(self, dests: list[str]):
        """Update active destination output paths from app sidebar."""
        self.destinations = [d for d in dests if d and d.strip()]
        self._update_all_previews(immediate=True)

    def refresh_scroll(self):
        self.update_idletasks()
        if hasattr(self, "scroll_container"):
            canvas = self.scroll_container._parent_canvas
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Scrollable Frame to avoid UI overflow
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_container.grid_columnconfigure(1, weight=1)

        # -------------------------------------------------------------
        # 0. Preset Selection & Deep Customization Section
        # -------------------------------------------------------------
        preset_section = ctk.CTkFrame(self.scroll_container, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER)
        preset_section.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(6, 8))
        preset_section.grid_columnconfigure(1, weight=1)

        # Preset Header Bar
        preset_title_frame = ctk.CTkFrame(preset_section, fg_color=theme.PANEL_BG, corner_radius=0, height=28)
        preset_title_frame.grid(row=0, column=0, columnspan=4, sticky="ew", padx=0, pady=0)

        lbl_preset_sec_title = ctk.CTkLabel(
            preset_title_frame,
            text="⚙️ QUẢN LÝ PRESET & TÙY CHỈNH SÂU CẤU HÌNH",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        lbl_preset_sec_title.pack(side="left", padx=10, pady=4)

        # Row 1: Preset Select Dropdown & Action Buttons
        ctk.CTkLabel(preset_section, text="Job Preset:", font=(theme.FONT_FAMILY, 12, "bold"), text_color=theme.TEXT_MAIN).grid(row=1, column=0, sticky="w", padx=(10, 5), pady=6)

        self.combo_presets = ctk.CTkOptionMenu(
            preset_section,
            values=["(Tùy chỉnh)"],
            fg_color=theme.PANEL_BG,
            button_color=theme.ACCENT_PRIMARY,
            button_hover_color=theme.ACCENT_PRIMARY_HOVER,
            dropdown_fg_color=theme.CARD_BG,
            height=32,
            command=self._on_preset_dropdown_selected
        )
        self.combo_presets.grid(row=1, column=1, sticky="ew", padx=5, pady=6)

        preset_btns_frame = ctk.CTkFrame(preset_section, fg_color="transparent")
        preset_btns_frame.grid(row=1, column=2, columnspan=2, sticky="e", padx=(5, 10), pady=6)

        btn_save_preset = ctk.CTkButton(
            preset_btns_frame,
            text="💾 Lưu / Cập Nhật",
            width=115,
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            command=self._on_save_preset_clicked
        )
        btn_save_preset.pack(side="left", padx=(0, 4))

        btn_save_as_new = ctk.CTkButton(
            preset_btns_frame,
            text="➕ Tạo Mới",
            width=90,
            fg_color=theme.PANEL_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self._on_save_as_new_preset_clicked
        )
        btn_save_as_new.pack(side="left", padx=(0, 4))

        btn_import_preset = ctk.CTkButton(
            preset_btns_frame,
            text="📥 Nhập",
            width=75,
            fg_color=theme.PANEL_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self._on_import_preset_clicked
        )
        btn_import_preset.pack(side="left", padx=(0, 4))

        btn_export_preset = ctk.CTkButton(
            preset_btns_frame,
            text="📤 Xuất",
            width=75,
            fg_color=theme.PANEL_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            command=self._on_export_preset_clicked
        )
        btn_export_preset.pack(side="left", padx=(0, 4))

        btn_delete_preset = ctk.CTkButton(
            preset_btns_frame,
            text="🗑️ Xóa",
            width=65,
            fg_color=theme.PANEL_BG,
            hover_color=theme.ACCENT_DANGER_HOVER,
            text_color=theme.ACCENT_DANGER,
            command=self._on_delete_preset_clicked
        )
        btn_delete_preset.pack(side="left")

        # Row 2: Deep Customization - Preset Name Entry
        ctk.CTkLabel(preset_section, text="Tên Preset:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).grid(row=2, column=0, sticky="w", padx=(10, 5), pady=(2, 6))

        self.entry_preset_name = ctk.CTkEntry(
            preset_section,
            placeholder_text="Nhập tên preset (Ví dụ: ARRI ALEXA Standard...)",
            fg_color=theme.PANEL_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            height=32
        )
        self.entry_preset_name.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(5, 10), pady=(2, 6))

        # Row 3: Deep Customization - Preset Description Entry
        ctk.CTkLabel(preset_section, text="Mô Tả / Ghi Chú:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).grid(row=3, column=0, sticky="w", padx=(10, 5), pady=(0, 8))

        self.entry_preset_desc = ctk.CTkEntry(
            preset_section,
            placeholder_text="Ghi chú thêm về thiết bị, định dạng hoặc dự án áp dụng preset này...",
            fg_color=theme.PANEL_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            height=32
        )
        self.entry_preset_desc.grid(row=3, column=1, columnspan=3, sticky="ew", padx=(5, 10), pady=(0, 8))

        # -------------------------------------------------------------
        # 1. Section Title
        # -------------------------------------------------------------
        title = ctk.CTkLabel(
            self.scroll_container,
            text="[3] THÔNG SỐ CẤU HÌNH QUY TẮC & XÁC THỰC",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        title.grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(6, 4))

        # -------------------------------------------------------------
        # 2. Live Config Preview (Compact Top View - Equal 50/50 Width)
        # -------------------------------------------------------------
        preview_section = ctk.CTkFrame(self.scroll_container, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER)
        preview_section.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 8))
        preview_section.grid_columnconfigure(0, weight=1, uniform="preview_cols")
        preview_section.grid_columnconfigure(1, weight=1, uniform="preview_cols")

        # Preview Header
        sec_title_frame = ctk.CTkFrame(preview_section, fg_color=theme.PANEL_BG, corner_radius=0, height=28)
        sec_title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        
        lbl_sec_title = ctk.CTkLabel(
            sec_title_frame,
            text="👁️ TRỰC QUAN CẤU HÌNH (LIVE CONFIG PREVIEW)",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.ACCENT_PRIMARY
        )
        lbl_sec_title.pack(side="left", padx=10, pady=4)

        # Top Left Column: Compact 3 Sample Files
        file_preview_frame = ctk.CTkFrame(preview_section, fg_color="transparent")
        file_preview_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)

        lbl_file_sec = ctk.CTkLabel(
            file_preview_frame,
            text="📄 File input mẫu:",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_file_sec.pack(anchor="w", pady=(0, 4))

        self.samples_container = ctk.CTkFrame(file_preview_frame, fg_color=theme.PANEL_BG, corner_radius=6)
        self.samples_container.pack(fill="both", expand=True)

        # Top Right Column: Compact Folder Tree Preview
        folder_preview_frame = ctk.CTkFrame(preview_section, fg_color="transparent")
        folder_preview_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=6)

        lbl_folder_hdr = ctk.CTkFrame(folder_preview_frame, fg_color="transparent")
        lbl_folder_hdr.pack(fill="x", pady=(0, 2))

        self.lbl_folder_hdr_title = ctk.CTkLabel(
            lbl_folder_hdr,
            text="📁 Cấu Trúc Folder Output:",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.TEXT_MAIN
        )
        self.lbl_folder_hdr_title.pack(side="left")

        self.lbl_dest_status = ctk.CTkLabel(
            lbl_folder_hdr,
            text="🟡 Chưa chọn Output",
            font=(theme.FONT_FAMILY, 9, "italic"),
            text_color=theme.TEXT_DIM
        )
        self.lbl_dest_status.pack(side="right")

        tree_box = ctk.CTkFrame(folder_preview_frame, fg_color=theme.PANEL_BG, corner_radius=6)
        tree_box.pack(fill="both", expand=True)
        tree_box.grid_columnconfigure(0, weight=1)
        tree_box.grid_rowconfigure(0, weight=1)

        self.tree_folder_preview = ttk.Treeview(
            tree_box,
            style="ConfigTree.Treeview",
            selectmode="browse",
            height=5,
            show="tree"
        )
        self.tree_folder_preview.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self._init_tree_tags()

        # -------------------------------------------------------------
        # 3. Config Inputs & Settings Section (Side-by-Side Same Row 50/50)
        # -------------------------------------------------------------
        inputs_container = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        inputs_container.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=(4, 6))
        inputs_container.grid_columnconfigure(0, weight=1, uniform="input_cols")
        inputs_container.grid_columnconfigure(1, weight=1, uniform="input_cols")

        # Left Column: File Naming Section
        file_section = ctk.CTkFrame(inputs_container, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER)
        file_section.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        file_section.grid_columnconfigure(1, weight=1)

        lbl_naming = ctk.CTkLabel(file_section, text="Cấu trúc File:", font=(theme.FONT_FAMILY, 11, "bold"), text_color=theme.TEXT_MAIN)
        lbl_naming.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=(6, 2))

        self.entry_naming = ColorSyntaxEntry(file_section, height=34)
        self.entry_naming.insert(0, "{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}")
        self.entry_naming.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=(6, 2))
        self.entry_naming.bind_change(lambda: self._on_input_changed())

        token_badges_frame = ctk.CTkFrame(file_section, fg_color=theme.PANEL_BG, corner_radius=6)
        token_badges_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=8, pady=(2, 6))

        lbl_file_token_title = ctk.CTkLabel(
            token_badges_frame,
            text="Placeholder:",
            font=(theme.FONT_FAMILY, 9),
            text_color=theme.TEXT_MUTED
        )
        lbl_file_token_title.pack(side="left", padx=(6, 2), pady=2)

        file_badges_container = ctk.CTkFrame(token_badges_frame, fg_color="transparent")
        file_badges_container.pack(side="left", fill="x", expand=True, pady=2)

        FILE_BTN_COLORS = {
            "{Camera:1}": "#42A5F5",
            "{Roll:3}": "#AB47BC",
            "{Clip:3}": "#FFA726",
            "{UID:2}": "#EC407A",
            "{Date:YYMMDD}": "#66BB6A",
            "{Project}": "#26C6DA"
        }

        for raw_token, _ in self.AVAILABLE_TOKENS:
            display_token = self.FILE_TOKENS_WITH_LENGTH.get(raw_token, raw_token)
            if raw_token == "{Date}":
                self.combo_date_file = ctk.CTkOptionMenu(
                    file_badges_container,
                    values=[
                        "YYMMDD", "DDMMYY", "DDMMYYYY",
                        "YYYYMMDD", "YYYY-MM-DD", "YY-MM-DD"
                    ],
                    font=(theme.FONT_FAMILY, 9, "bold"),
                    fg_color=theme.PANEL_BG,
                    button_color="#66BB6A",
                    button_hover_color="#4CAF50",
                    dropdown_fg_color=theme.CARD_BG,
                    text_color="#66BB6A",
                    dropdown_text_color="#66BB6A",
                    dropdown_hover_color="#388E3C",
                    width=85,
                    height=22,
                    command=self._on_date_format_file_selected
                )
                self.combo_date_file.set("YYMMDD")
                self.combo_date_file.pack(side="left", padx=(0, 3), pady=1)
            else:
                btn = ctk.CTkButton(
                    file_badges_container,
                    text=display_token,
                    font=(theme.FONT_FAMILY, 9, "bold"),
                    fg_color=theme.PANEL_BG,
                    hover_color=theme.ACCENT_PRIMARY,
                    text_color=FILE_BTN_COLORS.get(display_token, theme.ACCENT_PRIMARY),
                    height=22,
                    width=72,
                    command=lambda t=display_token: self._insert_token(t, target="file")
                )
                btn.pack(side="left", padx=(0, 3), pady=1)

        hint_lbl = ctk.CTkLabel(
            file_section,
            text="* Cú pháp độ dài cố định: {Token:ĐộDài} — Ví dụ: {Roll:3} (001), {Date:YYMMDD} (260722 hoặc 260721)",
            font=(theme.FONT_FAMILY, 10, "italic"),
            text_color=theme.TEXT_DIM
        )
        hint_lbl.grid(row=2, column=0, columnspan=4, sticky="w", padx=(10, 10), pady=(0, 6))

        # Right Column: Folder Template Section
        folder_section = ctk.CTkFrame(inputs_container, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER)
        folder_section.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        folder_section.grid_columnconfigure(1, weight=1)

        lbl_folder = ctk.CTkLabel(folder_section, text="Cấu trúc Folder:", font=(theme.FONT_FAMILY, 11, "bold"), text_color=theme.TEXT_MAIN)
        lbl_folder.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=(6, 2))

        self.entry_folder = ColorSyntaxEntry(folder_section, height=34, locked_prefix="{Destination}")
        self.entry_folder.insert(0, "{Destination}/Footage/{Camera}/Roll_{Roll}/")
        self.entry_folder.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=(6, 2))
        self.entry_folder.bind_change(lambda: self._on_input_changed())

        folder_badges_frame = ctk.CTkFrame(folder_section, fg_color=theme.PANEL_BG, corner_radius=6)
        folder_badges_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=8, pady=(2, 6))

        lbl_folder_token_title = ctk.CTkLabel(
            folder_badges_frame,
            text="Placeholder:",
            font=(theme.FONT_FAMILY, 9),
            text_color=theme.TEXT_MUTED
        )
        lbl_folder_token_title.pack(side="left", padx=(6, 2), pady=2)

        badges_container = ctk.CTkFrame(folder_badges_frame, fg_color="transparent")
        badges_container.pack(side="left", fill="x", expand=True, pady=2)

        FOLDER_BTN_COLORS = {
            "{Camera}": "#42A5F5",
            "{Roll}": "#AB47BC",
            "{Clip}": "#FFA726",
            "{UID}": "#EC407A",
            "{Date}": "#66BB6A",
            "{Project}": "#26C6DA"
        }

        for token_code, desc in self.AVAILABLE_TOKENS:
            if token_code in FOLDER_BTN_COLORS:
                btn_token = ctk.CTkButton(
                    badges_container,
                    text=token_code,
                    font=(theme.FONT_FAMILY, 9, "bold"),
                    fg_color=theme.PANEL_BG,
                    hover_color=theme.ACCENT_PRIMARY,
                    text_color=FOLDER_BTN_COLORS.get(token_code, theme.ACCENT_PRIMARY),
                    height=22,
                    width=72,
                    command=lambda t=token_code: self._insert_token(t, target="folder")
                )
                btn_token.pack(side="left", padx=(0, 3), pady=1)

        # Options Row 2: File Extension Blacklist & Suppress Reports
        extra_opt_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        extra_opt_frame.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=(4, 2))

        ctk.CTkLabel(extra_opt_frame, text="Bỏ qua đuôi file:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.entry_blacklist = ctk.CTkEntry(
            extra_opt_frame,
            placeholder_text=".txt, .py, .json",
            fg_color=theme.CARD_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            width=180,
            height=32
        )
        self.entry_blacklist.pack(side="left", padx=(0, 15))
        self.entry_blacklist.bind("<KeyRelease>", lambda e: self._on_input_changed())

        ctk.CTkLabel(extra_opt_frame, text="Không tạo file báo cáo:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.switch_suppress_reports = ctk.CTkSwitch(
            extra_opt_frame,
            text="",
            fg_color=theme.CARD_BORDER,
            progress_color=theme.ACCENT_PRIMARY,
            button_color=theme.ACCENT_PRIMARY_HOVER,
            button_hover_color=theme.ACCENT_PRIMARY,
            onvalue=True,
            offvalue=False,
            width=40,
            height=24
        )
        self.switch_suppress_reports.pack(side="left")
        self.switch_suppress_reports.configure(command=lambda: self._on_input_changed())

        # Options Row: Hash Algo | Log Format | Buffer Size
        # Options Row: Project Name | Hash Algo | Log Format | Buffer Size
        opt_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        opt_frame.grid(row=6, column=0, columnspan=4, sticky="ew", padx=10, pady=(4, 6))

        ctk.CTkLabel(opt_frame, text="Dự án:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.entry_project_name = ctk.CTkEntry(
            opt_frame,
            placeholder_text="Film Project",
            fg_color=theme.CARD_BG,
            border_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            width=120,
            height=32
        )
        self.entry_project_name.insert(0, "Film Project")
        self.entry_project_name.pack(side="left", padx=(0, 15))
        self.entry_project_name.bind("<KeyRelease>", lambda e: self._on_input_changed())

        ctk.CTkLabel(opt_frame, text="Xác thực:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.combo_hash = ctk.CTkOptionMenu(
            opt_frame,
            values=["MD5", "XXHash64", "SHA-256", "Size-only"],
            fg_color=theme.CARD_BG,
            button_color=theme.ACCENT_PRIMARY,
            button_hover_color=theme.ACCENT_PRIMARY_HOVER,
            dropdown_fg_color=theme.CARD_BG,
            width=110,
            height=32
        )
        self.combo_hash.set("MD5")
        self.combo_hash.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(opt_frame, text="Định dạng Log:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.combo_log = ctk.CTkOptionMenu(
            opt_frame,
            values=["TXT"],
            fg_color=theme.CARD_BG,
            button_color=theme.ACCENT_PRIMARY,
            button_hover_color=theme.ACCENT_PRIMARY_HOVER,
            dropdown_fg_color=theme.CARD_BG,
            width=80,
            height=32
        )
        self.combo_log.set("TXT")
        self.combo_log.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(opt_frame, text="Buffer Cache:", font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.combo_buffer = ctk.CTkOptionMenu(
            opt_frame,
            values=["8MB", "16MB", "32MB", "64MB", "128MB"],
            fg_color=theme.CARD_BG,
            button_color=theme.ACCENT_PRIMARY,
            button_hover_color=theme.ACCENT_PRIMARY_HOVER,
            dropdown_fg_color=theme.CARD_BG,
            width=85,
            height=32
        )
        self.combo_buffer.set("64MB")
        self.combo_buffer.pack(side="left")

        # -------------------------------------------------------------
        # 4. Dedicated Token Breakdown Explanation Section (At Bottom)
        # -------------------------------------------------------------
        explanation_section = ctk.CTkFrame(self.scroll_container, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER)
        explanation_section.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=(6, 12))
        explanation_section.grid_columnconfigure(0, weight=1)

        exp_title_frame = ctk.CTkFrame(explanation_section, fg_color=theme.PANEL_BG, corner_radius=0, height=28)
        exp_title_frame.pack(fill="x", padx=0, pady=0)

        lbl_exp_sec = ctk.CTkLabel(
            exp_title_frame,
            text="🔍 GIẢI THÍCH CHI TIẾT CÁC THÀNH PHẦN (TOKEN BREAKDOWN)",
            font=(theme.FONT_FAMILY, 11, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_exp_sec.pack(side="left", padx=10, pady=4)

        self.explanation_container = ctk.CTkFrame(explanation_section, fg_color="transparent")
        self.explanation_container.pack(fill="x", padx=10, pady=8)

    def _get_selected_date_format(self) -> str:
        pattern = self.entry_naming.get().strip()
        m = re.search(r'\{Date:([A-Za-z0-9_\-]+)\}', pattern)
        if m and not m.group(1).isdigit():
            return m.group(1)
        if hasattr(self, 'combo_date_file') and self.combo_date_file:
            return self.combo_date_file.get()
        return "YYMMDD"

    def set_date_format(self, date_format_key: str):
        fmt = (date_format_key or "YYMMDD").upper().strip()
        if hasattr(self, 'combo_date_file') and self.combo_date_file:
            try:
                self.combo_date_file.set(fmt)
            except Exception:
                pass
        pattern = self.entry_naming.get().strip()
        if re.search(r'\{Date(?::[A-Za-z0-9_\-]+)?\}', pattern):
            new_pattern = re.sub(r'\{Date(?::[A-Za-z0-9_\-]+)?\}', f'{{Date:{fmt}}}', pattern)
            if new_pattern != pattern:
                self.entry_naming.delete(0, "end")
                self.entry_naming.insert(0, new_pattern)
                self._on_input_changed()

    def _insert_token(self, token_text: str, target: str = "folder"):
        if target == "file":
            self.entry_naming.insert("end", token_text)
        else:
            self.entry_folder.insert("end", token_text)
        self._update_all_previews(immediate=True)

    def _add_token_to_naming(self, token_text: str):
        self._insert_token(token_text, target="file")

    def _on_date_format_file_selected(self, fmt: str):
        self._insert_token(f"{{Date:{fmt}}}", target="file")

    def _apply_quick_pattern(self, pattern: str):
        self.entry_naming.delete(0, "end")
        self.entry_naming.insert(0, pattern)
        self._on_input_changed()

    def _on_input_changed(self):
        self._update_all_previews(immediate=False)
        if self.on_config_changed:
            self.on_config_changed()

    def _generate_sample_filename_parts(self, pattern: str, sample_idx: int) -> list[tuple[str, str]]:
        """Evaluates file pattern into list of (text, color) tuples matching visual token builder."""
        active_date_fmt = self._get_selected_date_format()
        token_regex = re.compile(r'\{([A-Za-z0-9_]+)(?::([A-Za-z0-9_\-]+))?\}')

        parts = []
        last_pos = 0

        for match in token_regex.finditer(pattern):
            start, end = match.span()
            if start > last_pos:
                static_text = pattern[last_pos:start]
                parts.append((static_text, self.STATIC_TEXT_COLOR))

            token_name = match.group(1)
            length_str = match.group(2)

            if token_name == "Camera":
                val = "A" if sample_idx <= 2 else "B"
            elif token_name == "Roll":
                val = "001"
            elif token_name == "Clip":
                val = str(sample_idx).zfill(3)
            elif token_name == "UID":
                uids = ["BB", "AX", "5R"]
                val = uids[(sample_idx - 1) % len(uids)]
            elif token_name == "Date":
                fmt = length_str if (length_str and not length_str.isdigit()) else active_date_fmt
                val = format_date(datetime.now(), fmt)
            elif token_name == "Project":
                val = self.entry_project_name.get().strip() or "FilmProject"
            elif token_name == "Destination":
                val = "Output_Root"
            else:
                val = f"VAL{sample_idx}"

            if length_str and length_str.isdigit():
                length = int(length_str)
                if val.isdigit():
                    val = val.zfill(length)
                elif len(val) > 1 and val[0] in ('C', 'c'):
                    # For Clip C001, keep the prefix and pad the rest
                    num_part = val[1:]
                    val = val[0] + num_part.zfill(length - 1) if length > 1 else val[:length]
                else:
                    val = val[:length].ljust(length, "A")

            part_color = self.TOKEN_COLOR_MAP.get(token_name, "#5E35B1")
            parts.append((val, part_color))
            last_pos = end

        if last_pos < len(pattern):
            static_text = pattern[last_pos:]
            parts.append((static_text, self.STATIC_TEXT_COLOR))

        full_str = "".join(p[0] for p in parts)
        if not re.search(r'\.[A-Za-z0-9]+$', full_str):
            parts.append((".MOV", self.EXT_TEXT_COLOR))

        return parts

    def _generate_sample_filename(self, pattern: str, sample_idx: int) -> str:
        parts = self._generate_sample_filename_parts(pattern, sample_idx)
        return "".join(p[0] for p in parts)

    def _get_token_explanations(self, pattern: str) -> list[tuple[str, str, str]]:
        """Parses pattern to extract token/static component breakdowns."""
        token_regex = re.compile(r'\{([A-Za-z0-9_]+)(?::([A-Za-z0-9_\-]+))?\}')
        explanations = []
        last_pos = 0

        for match in token_regex.finditer(pattern):
            start, end = match.span()
            if start > last_pos:
                static_text = pattern[last_pos:start]
                explanations.append(("🔤 Phân cách cố định", f"Chuỗi: '{static_text}'", theme.TEXT_MUTED))

            token_name = match.group(1)
            length_str = match.group(2)
            raw_token = match.group(0)

            help_info = self.TOKEN_HELP_MAP.get(token_name, (f"Token '{token_name}'", "Giá trị tùy chỉnh"))
            desc = help_info[0]

            if length_str and length_str.isdigit():
                len_info = f"Cố định {length_str} ký tự — {help_info[1]}"
            else:
                len_info = help_info[1]

            explanations.append((f"🏷️ {raw_token} — {desc}", len_info, theme.ACCENT_PRIMARY))
            last_pos = end

        if last_pos < len(pattern):
            static_text = pattern[last_pos:]
            explanations.append(("🔤 Phân cách cố định", f"Chuỗi: '{static_text}'", theme.TEXT_MUTED))

        if not explanations:
            explanations.append(("📄 Tên file cố định", pattern, theme.TEXT_MAIN))

        return explanations

    def _update_all_previews(self, immediate: bool = False):
        """Schedules or immediately executes preview updates with debouncing."""
        if hasattr(self, "_preview_timer") and self._preview_timer is not None:
            try:
                self.after_cancel(self._preview_timer)
            except Exception:
                pass
            self._preview_timer = None

        if immediate:
            self._do_update_previews()
        else:
            self._preview_timer = self.after(80, self._do_update_previews)

    def _do_update_previews(self):
        """Re-render both File Preview (samples + breakdown) and Folder Preview tree if pattern changed."""
        self._preview_timer = None

        file_pattern = self.entry_naming.get().strip() or "{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}"
        folder_pattern = self.entry_folder.get().strip() or "{Destination}/Footage/{Camera}/Roll_{Roll}/"
        current_dests = tuple(self.destinations)
        current_project_name = self.entry_project_name.get().strip()

        if (
            file_pattern == getattr(self, "_last_rendered_file_pattern", None) and
            folder_pattern == getattr(self, "_last_rendered_folder_pattern", None) and
            current_dests == getattr(self, "_last_rendered_dests", None) and
            current_project_name == getattr(self, "_last_rendered_project_name", None)
        ):
            return

        self._last_rendered_file_pattern = file_pattern
        self._last_rendered_folder_pattern = folder_pattern
        self._last_rendered_dests = current_dests
        self._last_rendered_project_name = current_project_name

        # Generate 3 sample files
        sample_files = [self._generate_sample_filename(file_pattern, i) for i in (1, 2, 3)]

        # -------------------------------------------------------------
        # 1. Update File Samples Container with Token Color Highlighting
        # -------------------------------------------------------------
        for child in self.samples_container.winfo_children():
            child.destroy()

        for idx in (1, 2, 3):
            row_f = ctk.CTkFrame(self.samples_container, fg_color="transparent")
            row_f.pack(fill="x", padx=8, pady=3)

            lbl_tag = ctk.CTkLabel(
                row_f,
                text=f"Sample {idx}:",
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=theme.ACCENT_PRIMARY,
                width=65,
                anchor="w"
            )
            lbl_tag.pack(side="left")

            lbl_icon = ctk.CTkLabel(
                row_f,
                text="🎬 ",
                font=(theme.FONT_FAMILY, 10),
                text_color=theme.TEXT_MAIN
            )
            lbl_icon.pack(side="left")

            parts = self._generate_sample_filename_parts(file_pattern, idx)
            for text_part, color in parts:
                lbl_part = ctk.CTkLabel(
                    row_f,
                    text=text_part,
                    font=(theme.FONT_FAMILY, 11, "bold"),
                    text_color=color,
                    anchor="w"
                )
                lbl_part.pack(side="left", padx=0)

        # -------------------------------------------------------------
        # 2. Update File Explanation Breakdown Container
        # -------------------------------------------------------------
        for child in self.explanation_container.winfo_children():
            child.destroy()

        explanations = self._get_token_explanations(file_pattern)
        for title_text, detail_text, color in explanations:
            item_f = ctk.CTkFrame(self.explanation_container, fg_color="transparent")
            item_f.pack(fill="x", padx=8, pady=2)

            lbl_t = ctk.CTkLabel(
                item_f,
                text=title_text,
                font=(theme.FONT_FAMILY, 10, "bold"),
                text_color=color,
                anchor="w"
            )
            lbl_t.pack(anchor="w")

            lbl_d = ctk.CTkLabel(
                item_f,
                text=f"    ↳ {detail_text}",
                font=(theme.FONT_FAMILY, 9),
                text_color=theme.TEXT_MUTED,
                anchor="w"
            )
            lbl_d.pack(anchor="w")

        # -------------------------------------------------------------
        # 3. Update Folder Structure Tree Preview & Dynamic Length
        # -------------------------------------------------------------
        for item in self.tree_folder_preview.get_children():
            self.tree_folder_preview.delete(item)

        # Determine Output destination root display name
        if self.destinations:
            actual_dest_path = self.destinations[0]
            output_folder_name = os.path.basename(actual_dest_path.rstrip("/\\")) or actual_dest_path
            dest_display = f"💽 Output ({output_folder_name})"
            self.lbl_dest_status.configure(
                text=f"🟢 Output thực tế: {actual_dest_path}",
                text_color=theme.ACCENT_SUCCESS if hasattr(theme, "ACCENT_SUCCESS") else "#4CAF50"
            )
        else:
            output_folder_name = "RAID_DESTINATION_01"
            dest_display = f"💽 {output_folder_name} (Ví dụ)"
            self.lbl_dest_status.configure(
                text="🟡 Chưa chọn Output (Đang hiển thị tên ổ đĩa mẫu)",
                text_color=theme.TEXT_DIM
            )

        # Replace template tokens for folder evaluation
        context = {
            "Destination": dest_display,
            "Camera": "A",
            "Roll": "001",
            "Date": format_date(datetime.now(), self._get_selected_date_format()),
            "Project": self.entry_project_name.get().strip() or "FilmProject",
            "Clip": "001",
            "UID": "BB"
        }

        eval_folder = folder_pattern
        for k, v in context.items():
            eval_folder = eval_folder.replace(f"{{{k}}}", v).replace(f"{{{k}:1}}", v[:1]).replace(f"{{{k}:3}}", v)

        # Normalize path splits
        pattern_parts = [p for p in folder_pattern.replace("\\", "/").split("/") if p.strip()]
        eval_parts = [p for p in eval_folder.replace("\\", "/").split("/") if p.strip()]

        if not eval_parts:
            eval_parts = [dest_display, "Footage", "A", "Roll_001"]
            pattern_parts = ["{Destination}", "Footage", "{Camera}", "Roll_{Roll}"]

        # Calculate dynamic height required by treeview according to total items (folder levels + sample files)
        total_tree_rows = len(eval_parts) + len(sample_files)
        tree_height = max(5, min(14, total_tree_rows))
        self.tree_folder_preview.configure(height=tree_height)

        # Calculate total path length in characters for sample file inside output folder structure
        sample_path_str = "/".join(eval_parts) + "/" + (sample_files[0] if sample_files else "")
        path_char_len = len(sample_path_str)
        folder_depth = len(eval_parts)

        # Update title with dynamic path length and folder depth info
        if hasattr(self, "lbl_folder_hdr_title"):
            self.lbl_folder_hdr_title.configure(
                text=f"📁 Cấu Trúc Folder Output ({folder_depth} cấp | Độ dài: {path_char_len} ký tự):"
            )

        # Populate Treeview hierarchy with color tags
        parent = ""
        for i, part in enumerate(eval_parts):
            pat_str = pattern_parts[i] if i < len(pattern_parts) else ""

            if i == 0 or "{Destination}" in pat_str or part.startswith("💽"):
                tag_name = "Destination"
                label_text = part
            elif "{Camera}" in pat_str:
                tag_name = "Camera"
                label_text = f"📁 {part}"
            elif "{Roll}" in pat_str:
                tag_name = "Roll"
                label_text = f"📁 {part}"
            elif "{Date}" in pat_str:
                tag_name = "Date"
                label_text = f"📁 {part}"
            elif "{Project}" in pat_str:
                tag_name = "Project"
                label_text = f"📁 {part}"
            elif "{Clip}" in pat_str:
                tag_name = "Clip"
                label_text = f"📁 {part}"
            elif "{UID}" in pat_str:
                tag_name = "UID"
                label_text = f"📁 {part}"
            else:
                tag_name = "StaticFolder"
                label_text = f"📁 {part}"

            node_id = self.tree_folder_preview.insert(parent, "end", text=f" {label_text}", open=True, tags=(tag_name,))
            parent = node_id

        # Insert 3 sample files into the deepest folder node with SampleFile tag
        for fname in sample_files:
            self.tree_folder_preview.insert(parent, "end", text=f"  🎬 {fname}", tags=("SampleFile",))

        self._bind_mouse_wheel()

    def get_config(self) -> dict:
        buf_str = self.combo_buffer.get().replace("MB", "").strip()
        buf_mb = int(buf_str) if buf_str.isdigit() else 64

        raw_exts = self.entry_blacklist.get().strip()
        ext_list = [e.strip() for e in raw_exts.split(",") if e.strip()] if raw_exts else []

        return {
            "name": self.entry_preset_name.get().strip(),
            "description": self.entry_preset_desc.get().strip(),
            "project_name": self.entry_project_name.get().strip() or "Film Project",
            "naming_rule": self.entry_naming.get().strip(),
            "folder_template": self.entry_folder.get().strip(),
            "date_format": self._get_selected_date_format(),
            "hash_algorithm": self.combo_hash.get(),
            "log_format": self.combo_log.get(),
            "buffer_size_mb": buf_mb,
            "file_extension_blacklist": ext_list,
            "suppress_output_reports": bool(self.switch_suppress_reports.get())
        }

    def apply_preset(self, preset_dict: dict):
        if "name" in preset_dict:
            self.entry_preset_name.delete(0, "end")
            self.entry_preset_name.insert(0, preset_dict["name"])
        if "description" in preset_dict:
            self.entry_preset_desc.delete(0, "end")
            self.entry_preset_desc.insert(0, preset_dict.get("description", ""))
        else:
            self.entry_preset_desc.delete(0, "end")
        if "project_name" in preset_dict:
            self.entry_project_name.delete(0, "end")
            self.entry_project_name.insert(0, preset_dict["project_name"])
        else:
            self.entry_project_name.delete(0, "end")
            self.entry_project_name.insert(0, "Film Project")
        if "naming_rule" in preset_dict:
            self.entry_naming.delete(0, "end")
            self.entry_naming.insert(0, preset_dict["naming_rule"])
        if "folder_template" in preset_dict:
            self.entry_folder.delete(0, "end")
            self.entry_folder.insert(0, preset_dict["folder_template"])
        if "date_format" in preset_dict:
            self.set_date_format(preset_dict["date_format"])
        if "hash_algorithm" in preset_dict:
            self.combo_hash.set(preset_dict["hash_algorithm"])
        if "log_format" in preset_dict:
            self.combo_log.set(preset_dict["log_format"])
        if "buffer_size_mb" in preset_dict:
            self.combo_buffer.set(f"{preset_dict['buffer_size_mb']}MB")
        if "file_extension_blacklist" in preset_dict:
            ext_list = preset_dict["file_extension_blacklist"]
            if isinstance(ext_list, list):
                self.entry_blacklist.delete(0, "end")
                self.entry_blacklist.insert(0, ", ".join(ext_list))
        else:
            self.entry_blacklist.delete(0, "end")
        if "suppress_output_reports" in preset_dict:
            self.switch_suppress_reports.select() if preset_dict["suppress_output_reports"] else self.switch_suppress_reports.deselect()
        else:
            self.switch_suppress_reports.deselect()
        self._on_input_changed()

    def _load_presets_to_combo(self, select_name: str = None, apply_to_ui: bool = True):
        """Reload list of presets from preset_manager into dropdown."""
        presets = self.preset_manager.list_presets()
        if not presets:
            self.combo_presets.configure(values=["(Không có preset)"])
            self.combo_presets.set("(Không có preset)")
            self.current_loaded_preset_name = None
        else:
            self.combo_presets.configure(values=presets)
            target = select_name if select_name in presets else presets[0]
            self.combo_presets.set(target)
            self.current_loaded_preset_name = target
            if apply_to_ui:
                self._on_preset_dropdown_selected(target)

    def _on_preset_dropdown_selected(self, preset_name: str):
        if not preset_name or preset_name == "(Không có preset)":
            return
        preset_dict = self.preset_manager.load_preset(preset_name)
        if preset_dict:
            self.current_loaded_preset_name = preset_name
            self.apply_preset(preset_dict)
            if self.on_config_changed:
                self.on_config_changed()

    def _on_save_preset_clicked(self):
        """Save current configuration to the preset specified in entry_preset_name (overwriting or renaming)."""
        name = self.entry_preset_name.get().strip()
        if not name:
            name = "Untitled Preset"

        config = self.get_config()
        config["name"] = name

        if self.preset_manager.save_preset(config, old_name=self.current_loaded_preset_name):
            self.current_loaded_preset_name = name
            self._load_presets_to_combo(select_name=name, apply_to_ui=False)
        else:
            from tkinter import messagebox
            messagebox.showerror("Lỗi Lưu Preset", f"Không thể lưu preset '{name}'. Vui lòng kiểm tra quyền truy cập thư mục presets.")

    def _on_save_as_new_preset_clicked(self):
        """Open dialog to prompt for a new preset name."""
        existing_names = self.preset_manager.list_presets()
        SavePresetDialog(self, on_save_callback=self._save_new_preset_confirmed, existing_names=existing_names)

    def _save_new_preset_confirmed(self, name: str):
        config = self.get_config()
        config["name"] = name

        if self.preset_manager.save_preset(config):
            self.current_loaded_preset_name = name
            self._load_presets_to_combo(select_name=name, apply_to_ui=False)

    def _on_delete_preset_clicked(self):
        """Open delete confirmation dialog for currently selected preset."""
        preset_name = self.combo_presets.get()
        if not preset_name or preset_name == "(Không có preset)":
            return
        DeletePresetDialog(self, preset_name=preset_name, on_delete_callback=self._delete_preset_confirmed)

    def _delete_preset_confirmed(self, name: str):
        if self.preset_manager.delete_preset(name):
            self.current_loaded_preset_name = None
            self._load_presets_to_combo()

    def _on_import_preset_clicked(self):
        """Import preset from an external JSON file."""
        file_path = filedialog.askopenfilename(
            title="Nhập Preset Cấu Hình",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            imported = self.preset_manager.import_preset(file_path)
            if imported and "name" in imported:
                self.current_loaded_preset_name = imported["name"]
                self._load_presets_to_combo(select_name=imported["name"])
                self.apply_preset(imported)

    def _on_export_preset_clicked(self):
        """Export current preset to an external JSON file."""
        preset_name = self.combo_presets.get()
        if not preset_name or preset_name in ("(Tùy chỉnh)", "(Không có preset)"):
            preset_name = self.entry_preset_name.get().strip() or "Custom_Preset"

        file_path = filedialog.asksaveasfilename(
            title="Xuất Preset Cấu Hình",
            initialfile=f"{preset_name}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            config = self.get_config()
            config["name"] = preset_name
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to export preset to {file_path}: {e}")



