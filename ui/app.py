import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import os
import time
import threading
import webbrowser
from typing import Optional

import ui.theme as theme
from ui.sidebar_panel import ShotPutSidebar
from ui.progress_panel import ShotPutProgressPanel
from ui.job_flow_panel import JobFlowPanel
from ui.file_table import FileStatusTable
from ui.config_panel import ConfigPanel
from ui.preset_dialog import SavePresetDialog, DeletePresetDialog
from ui.alert_dialog import ChecksumAlertDialog
from ui.media_preview_widget import MediaPreviewWidget, is_media_file, get_media_category

from core.token_parser import TokenParser
from core.directory_builder import DirectoryBuilder
from core.copy_engine import CopyEngine
from core.preset_manager import PresetManager
from core.report_generator import ReportGenerator
from core.metadata_reader import MetadataReader
from core.sound_player import SoundPlayer


class DITCopyProApp(ctk.CTk):
    """
    Main Application GUI for Sector54 DIT Copy Pro — ShotPut Pro Edition.
    Features dark slate cinematography aesthetic, resizable sidebar splitter,
    visual Job Flow canvas, dual-phase progress cards, and dedicated tabs.
    """

    def __init__(self):
        super().__init__()

        # Setup Window
        self.title("Sector54 DIT Copy Pro — Software Sao Chép & Xác Thực Điện Ảnh (ShotPut Edition)")
        self.geometry("1280x880")
        self.minsize(1024, 720)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=theme.BG_DARK)

        # Core Managers & Engines
        self.preset_manager = PresetManager()
        self.sound_player = SoundPlayer()
        self.current_copy_engine: Optional[CopyEngine] = None
        self.is_copying = False
        self._has_played_sound = False
        self.open_preview_tabs = {}  # filepath -> (tab_title, preview_widget)

        self._init_paned_style()
        self._build_ui()

        # Set compact VS Code Explorer initial sidebar width (300px) and progress panel height (280px)
        self.after(200, self._set_initial_sash_pos)
        self.bind("<FocusIn>", self._on_window_focus_in)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_window_focus_in(self, event=None):
        if hasattr(self, "sidebar"):
            try:
                self.sidebar.tree_input.refresh_tree_live()
                self.sidebar.tree_output.refresh_tree_live()
            except Exception:
                pass

    def _set_initial_sash_pos(self):
        try:
            self.paned_window.sashpos(0, 300)
        except Exception:
            pass
        try:
            self.right_paned.sashpos(0, 280)
        except Exception:
            pass
        try:
            if hasattr(self, "progress_panel") and hasattr(self.progress_panel, "paned"):
                self.progress_panel.paned.sashpos(0, 480)
        except Exception:
            pass

    def _init_paned_style(self):
        """Configure dark theme style for ttk.PanedWindow splitter handle."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "TPanedwindow",
            background=theme.BG_DARK
        )
        style.configure(
            "Sash",
            sashthickness=5,
            sashpad=0,
            sashrelief="flat",
            background=theme.CARD_BORDER
        )

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)     # Header fixed
        self.grid_rowconfigure(1, weight=1)     # Main Workspace (PanedWindow) takes all remaining space

        # -------------------------------------------------------------
        # 1. Top Header Bar (ShotPut Pro Style)
        # -------------------------------------------------------------
        header_frame = ctk.CTkFrame(self, fg_color=theme.PANEL_BG, corner_radius=0, height=54, border_width=1, border_color=theme.CARD_BORDER)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)

        # App Logo & Title & Author Credit
        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="w", padx=(15, 10), pady=10)

        logo_lbl = ctk.CTkLabel(
            logo_frame,
            text="🎬 Sector54 DIT Copy Pro",
            font=(theme.FONT_FAMILY, 16, "bold"),
            text_color=theme.TEXT_MAIN
        )
        logo_lbl.pack(side="left", padx=(0, 10))

        credit_lbl = ctk.CTkLabel(
            logo_frame,
            text="| Made by ",
            font=(theme.FONT_FAMILY, 13),
            text_color=theme.TEXT_MUTED
        )
        credit_lbl.pack(side="left")

        author_link = ctk.CTkLabel(
            logo_frame,
            text="Tuns",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.ACCENT_PRIMARY,
            cursor="hand2"
        )
        author_link.pack(side="left")
        author_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Tunslee-Brian"))

        # Top Right Actions & Buttons
        actions_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=2, sticky="e", padx=15, pady=10)

        self.btn_cancel = ctk.CTkButton(
            actions_frame,
            text="HỦY QUÁ TRÌNH",
            font=(theme.FONT_FAMILY, 12, "bold"),
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MUTED,
            height=34,
            width=120,
            state="disabled",
            command=self._cancel_copy
        )
        self.btn_cancel.pack(side="left", padx=(0, 8))

        self.btn_verify_only = ctk.CTkButton(
            actions_frame,
            text="🔍 XÁC THỰC LẠI",
            font=(theme.FONT_FAMILY, 12, "bold"),
            fg_color=theme.ACCENT_VERIFY,
            hover_color="#5b4bc4",
            height=34,
            width=135,
            command=self._start_verify_only
        )
        self.btn_verify_only.pack(side="left", padx=(0, 8))

        self.btn_clear_job = ctk.CTkButton(
            actions_frame,
            text="🧹 LÀM MỚI TÁC VỤ",
            font=(theme.FONT_FAMILY, 12, "bold"),
            fg_color=theme.CARD_BG,
            hover_color=theme.CARD_BORDER,
            text_color=theme.TEXT_MAIN,
            height=34,
            width=135,
            command=self._clear_job_session
        )
        self.btn_clear_job.pack(side="left", padx=(0, 8))

        self.btn_start = ctk.CTkButton(
            actions_frame,
            text="▶ BẮT ĐẦU SAO CHÉP",
            font=(theme.FONT_FAMILY, 13, "bold"),
            fg_color=theme.ACCENT_PRIMARY,
            hover_color=theme.ACCENT_PRIMARY_HOVER,
            height=34,
            width=160,
            command=self._start_copy
        )
        self.btn_start.pack(side="left")

        # -------------------------------------------------------------
        # 2. Main Resizable PanedWindow (Splitter Handle)
        # -------------------------------------------------------------
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Left Resizable Pane: Sidebar (Input/Output Pickers & Compact VS Code Trees)
        self.sidebar = ShotPutSidebar(
            self.paned_window,
            on_source_changed=self._on_source_changed,
            on_destinations_changed=self._on_destinations_changed,
            on_media_file_select=self._on_sidebar_media_file_selected,
            width=300
        )
        self.paned_window.add(self.sidebar, weight=0)

        # Right Resizable Pane: Vertical PanedWindow (Top Cards + Bottom Tabview)
        self.right_paned = ttk.PanedWindow(self.paned_window, orient=tk.VERTICAL)
        self.paned_window.add(self.right_paned, weight=1)

        # Top Progress Panel (ShotPut Dual Cards)
        self.progress_panel = ShotPutProgressPanel(self.right_paned)
        self.right_paned.add(self.progress_panel, weight=0)

        # Bottom Section Container (Seamless workspace without outer dark borders)
        self.bottom_section = ctk.CTkFrame(self.right_paned, fg_color=theme.PANEL_BG, corner_radius=0)
        self.bottom_section.grid_columnconfigure(0, weight=1)
        self.bottom_section.grid_rowconfigure(0, weight=0)  # Header tab bar fixed
        self.bottom_section.grid_rowconfigure(1, weight=1)  # Tab content takes remaining space
        self.right_paned.add(self.bottom_section, weight=1)

        # Tab Bar Header Frame (Seamlessly placed inside the bottom section)
        self.tab_header_frame = ctk.CTkFrame(self.bottom_section, fg_color=theme.CARD_BG, corner_radius=0, height=36)
        self.tab_header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.tab_header_frame.pack_propagate(False)

        self.tab_segmented_button = ctk.CTkSegmentedButton(
            self.tab_header_frame,
            values=[
                "Job Flow Diagram",
                "Danh Sách File (Input/Output Status)",
                "Cấu Hình (Config Settings)",
                "Xem Trước (File Preview)"
            ],
            fg_color=theme.PANEL_BG,
            selected_color=theme.ACCENT_PRIMARY,
            selected_hover_color=theme.ACCENT_PRIMARY_HOVER,
            unselected_color=theme.CARD_BG,
            unselected_hover_color=theme.CARD_BORDER,
            font=(theme.FONT_FAMILY, 11, "bold"),
            command=self._on_segmented_tab_changed
        )
        self.tab_segmented_button.pack(side="left", padx=8, pady=4)

        # Content Area Container
        self.tab_content_container = ctk.CTkFrame(self.bottom_section, fg_color="transparent", corner_radius=0)
        self.tab_content_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.tab_content_container.grid_columnconfigure(0, weight=1)
        self.tab_content_container.grid_rowconfigure(0, weight=1)

        # Tab 1: Job Flow Diagram
        self.tab_jobflow_frame = ctk.CTkFrame(self.tab_content_container, fg_color="transparent", corner_radius=0)
        self.tab_jobflow_frame.grid_columnconfigure(0, weight=1)
        self.tab_jobflow_frame.grid_rowconfigure(0, weight=1)
        self.job_flow_panel = JobFlowPanel(self.tab_jobflow_frame)
        self.job_flow_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Tab 2: File Status Table (Input / Output file status)
        self.tab_files_frame = ctk.CTkFrame(self.tab_content_container, fg_color="transparent", corner_radius=0)
        self.tab_files_frame.grid_columnconfigure(0, weight=1)
        self.tab_files_frame.grid_rowconfigure(0, weight=1)
        self.file_table = FileStatusTable(self.tab_files_frame)
        self.file_table.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Tab 3: Dedicated Config Panel (Integrated Preset Management)
        self.tab_config_frame = ctk.CTkFrame(self.tab_content_container, fg_color="transparent", corner_radius=0)
        self.tab_config_frame.grid_columnconfigure(0, weight=1)
        self.tab_config_frame.grid_rowconfigure(0, weight=1)
        self.config_panel = ConfigPanel(
            self.tab_config_frame,
            preset_manager=self.preset_manager,
            on_config_changed_callback=self._on_config_changed
        )
        self.config_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Tab 4: Fixed Single Media Preview Panel
        self.tab_preview_frame = ctk.CTkFrame(self.tab_content_container, fg_color="transparent", corner_radius=0)
        self.tab_preview_frame.grid_columnconfigure(0, weight=1)
        self.tab_preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_panel = MediaPreviewWidget(self.tab_preview_frame)
        self.preview_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Initial Tab Selection
        self.tab_segmented_button.set("Job Flow Diagram")
        self._switch_tab_view("Job Flow Diagram")

    def _on_config_changed(self):
        self._refresh_file_list()


    def _on_source_changed(self, source_path: str):
        self._update_job_flow()
        self._refresh_file_list()

    def _on_destinations_changed(self, dests: list[str]):
        self._update_job_flow()
        self._refresh_file_list()
        if hasattr(self, "config_panel"):
            self.config_panel.set_destinations(dests)

    def _update_job_flow(self):
        if not hasattr(self, "sidebar") or not hasattr(self, "job_flow_panel"):
            return
        src = self.sidebar.get_source_path()
        dests = self.sidebar.get_destinations()
        self.job_flow_panel.set_data(src, dests)

    def _refresh_file_list(self):
        if not hasattr(self, "sidebar") or not hasattr(self, "file_table") or not hasattr(self, "progress_panel") or not hasattr(self, "config_panel"):
            return

        src = self.sidebar.get_source_path()
        dests = self.sidebar.get_destinations()
        config = self.config_panel.get_config()

        if not src or not os.path.exists(src):
            self.file_table.populate_files([])
            self.progress_panel.reset()
            return

        token_parser = TokenParser(config["naming_rule"])
        dir_builder = DirectoryBuilder(config["folder_template"])

        engine = CopyEngine(
            source_dir=src,
            destinations=dests,
            token_parser=token_parser,
            directory_builder=dir_builder,
            hash_algorithm=config["hash_algorithm"],
            buffer_size_mb=config["buffer_size_mb"]
        )

        file_list = engine.scan_source()
        self.file_table.populate_files(file_list)

        job_name = os.path.basename(src.rstrip("/\\")) or src
        total_bytes = sum(f["size"] for f in file_list)
        folder_count = getattr(engine, "folder_count", 0)
        self.progress_panel.set_job_info(job_name, total_bytes, len(file_list), folder_count)

    def _start_copy(self):
        src = self.sidebar.get_source_path()
        dests = self.sidebar.get_destinations()
        config = self.config_panel.get_config()

        if not src or not os.path.exists(src):
            self._show_feedback("Vui lòng chọn thư mục nguồn!", theme.ACCENT_DANGER)
            return

        if not dests:
            self._show_feedback("Vui lòng chọn ít nhất 1 thư mục đích!", theme.ACCENT_DANGER)
            return

        token_parser = TokenParser(config["naming_rule"], date_format=config.get("date_format", "YYMMDD"))
        dir_builder = DirectoryBuilder(config["folder_template"])

        self.current_copy_engine = CopyEngine(
            source_dir=src,
            destinations=dests,
            token_parser=token_parser,
            directory_builder=dir_builder,
            hash_algorithm=config["hash_algorithm"],
            buffer_size_mb=config["buffer_size_mb"]
        )

        file_list = self.current_copy_engine.scan_source()

        # Pre-check free disk space on all destination drives
        space_info = self.current_copy_engine.check_free_space()
        insufficient_dests = [d for d, info in space_info.items() if not info["sufficient"]]
        if insufficient_dests:
            from tkinter import messagebox
            req_str = ReportGenerator.format_size(self.current_copy_engine.total_bytes)
            msg = f"CẢNH BÁO: Dung lượng còn trống không đủ để chứa dữ liệu nguồn ({req_str}):\n\n"
            for d in insufficient_dests:
                free_b = space_info[d]["free_bytes"]
                free_str = ReportGenerator.format_size(free_b) if free_b >= 0 else "N/A"
                msg += f" • {d}: Còn trống {free_str}\n"
            msg += "\nBạn có chắc chắn vẫn muốn tiếp tục sao chép không?"
            if not messagebox.askyesno("Cảnh Báo Dung Lượng Ổ Đĩa", msg, icon="warning"):
                return

        self.is_copying = True
        self._has_played_sound = False

        self.btn_start.configure(state="disabled", fg_color=theme.CARD_BG)
        self.btn_verify_only.configure(state="disabled", fg_color=theme.CARD_BG)
        self.btn_cancel.configure(state="normal", fg_color=theme.ACCENT_DANGER, hover_color=theme.ACCENT_DANGER_HOVER, text_color="#ffffff")

        self.file_table.populate_files(file_list)

        job_name = os.path.basename(src.rstrip("/\\")) or src
        folder_count = getattr(self.current_copy_engine, "folder_count", 0)
        self.progress_panel.reset()
        self.progress_panel.set_job_info(job_name, self.current_copy_engine.total_bytes, len(file_list), folder_count)

        # Run copy session in background thread
        threading.Thread(target=lambda: self._run_session_thread("copy"), daemon=True).start()

    def _start_verify_only(self):
        src = self.sidebar.get_source_path()
        dests = self.sidebar.get_destinations()
        config = self.config_panel.get_config()

        if not src or not os.path.exists(src):
            self._show_feedback("Vui lòng chọn thư mục nguồn!", theme.ACCENT_DANGER)
            return

        if not dests:
            self._show_feedback("Vui lòng chọn ít nhất 1 thư mục đích!", theme.ACCENT_DANGER)
            return

        self.is_copying = True
        self._has_played_sound = False

        self.btn_start.configure(state="disabled", fg_color=theme.CARD_BG)
        self.btn_verify_only.configure(state="disabled", fg_color=theme.CARD_BG)
        self.btn_cancel.configure(state="normal", fg_color=theme.ACCENT_DANGER, hover_color=theme.ACCENT_DANGER_HOVER, text_color="#ffffff")

        token_parser = TokenParser(config["naming_rule"], date_format=config.get("date_format", "YYMMDD"))
        dir_builder = DirectoryBuilder(config["folder_template"])

        self.current_copy_engine = CopyEngine(
            source_dir=src,
            destinations=dests,
            token_parser=token_parser,
            directory_builder=dir_builder,
            hash_algorithm=config["hash_algorithm"],
            buffer_size_mb=config["buffer_size_mb"]
        )

        file_list = self.current_copy_engine.scan_source()
        self.file_table.populate_files(file_list)

        job_name = os.path.basename(src.rstrip("/\\")) or src
        folder_count = getattr(self.current_copy_engine, "folder_count", 0)
        self.progress_panel.reset()
        self.progress_panel.set_job_info(f"Verify: {job_name}", self.current_copy_engine.total_bytes, len(file_list), folder_count)

        # Run verify session in background thread
        threading.Thread(target=lambda: self._run_session_thread("verify_only"), daemon=True).start()

    def _run_session_thread(self, session_type: str = "copy"):

        def on_file_start(file_info):
            self.after(0, lambda: self.file_table.update_file_status(file_info))

        last_ui_update_time = 0.0
        last_tree_update_time = 0.0

        def on_file_progress(file_info, file_bytes_read, speed, eta):
            nonlocal last_ui_update_time
            now = time.time()
            if now - last_ui_update_time >= 0.05 or file_bytes_read >= file_info["size"]:
                last_ui_update_time = now
                fname = file_info["filename"]
                fsize = file_info["size"]
                self.after(0, lambda fn=fname, fr=file_bytes_read, fs=fsize, sp=speed, et=eta: self.progress_panel.update_file_progress(
                    fn, fr, fs, sp, et
                ))
                if self.current_copy_engine:
                    cb = self.current_copy_engine.copied_bytes
                    tb = self.current_copy_engine.total_bytes
                    vc = sum(1 for f in self.current_copy_engine.file_list if f["status"] == "VERIFIED")
                    tc = len(self.current_copy_engine.file_list)
                    self.after(0, lambda c_b=cb, t_b=tb, v_c=vc, t_c=tc: self.progress_panel.update_total_progress(
                        c_b, t_b, v_c, t_c
                    ))

        def on_file_complete(file_info):
            nonlocal last_tree_update_time
            self.after(0, lambda: self.file_table.update_file_status(file_info))
            if self.current_copy_engine:
                self.after(0, lambda: self.progress_panel.update_total_progress(
                    self.current_copy_engine.copied_bytes,
                    self.current_copy_engine.total_bytes,
                    sum(1 for f in self.current_copy_engine.file_list if f["status"] == "VERIFIED"),
                    len(self.current_copy_engine.file_list)
                ))
                now = time.time()
                if now - last_tree_update_time >= 0.3:
                    last_tree_update_time = now
                    self.after(0, lambda: self.sidebar.update_sidebar_tree_status(
                        self.current_copy_engine.file_list,
                        getattr(self.current_copy_engine, "extra_files", []),
                        expand_output=True
                    ))

        def on_session_complete(summary):
            self.after(0, lambda: self._handle_session_complete(summary))

        if session_type == "verify_only":
            self.current_copy_engine.run_verify_only_session(
                on_file_start=on_file_start,
                on_file_progress=on_file_progress,
                on_file_complete=on_file_complete,
                on_session_complete=on_session_complete,
                metadata_reader_func=MetadataReader.get_shot_time
            )
        else:
            self.current_copy_engine.run_copy_session(
                on_file_start=on_file_start,
                on_file_progress=on_file_progress,
                on_file_complete=on_file_complete,
                on_session_complete=on_session_complete,
                metadata_reader_func=MetadataReader.get_shot_time
            )

    def _handle_session_complete(self, summary: dict):
        self.is_copying = False
        self.btn_start.configure(state="normal", fg_color=theme.ACCENT_PRIMARY)
        self.btn_verify_only.configure(state="normal", fg_color=theme.ACCENT_VERIFY)
        self.btn_cancel.configure(state="disabled", fg_color=theme.CARD_BG, text_color=theme.TEXT_MUTED)

        if self.current_copy_engine:
            self.progress_panel.update_total_progress(
                self.current_copy_engine.copied_bytes,
                self.current_copy_engine.total_bytes,
                summary.get("verified", 0),
                summary.get("total_files", len(self.current_copy_engine.file_list))
            )
            self.sidebar.update_sidebar_tree_status(
                self.current_copy_engine.file_list,
                summary.get("extra_files", []),
                expand_output=True
            )

        # Prevent duplicate audio playback for the same session
        if self._has_played_sound:
            return
        self._has_played_sound = True

        # Generate TXT & HTML Reports
        src = self.sidebar.get_source_path()
        dests = self.sidebar.get_destinations()
        config = self.config_panel.get_config()

        card_name = os.path.basename(src.rstrip('/\\\\')) or "Card"
        txt_report_path = os.path.join(dests[0], f"DIT_Report_{card_name}.txt")
        html_report_path = os.path.join(dests[0], f"DIT_Report_{card_name}.html")

        ReportGenerator.generate_txt_report(
            project_name="Film Project",
            preset_name=config.get("name", "Custom Preset"),
            source_dir=src,
            destinations=dests,
            hash_algorithm=config["hash_algorithm"],
            file_list=self.current_copy_engine.file_list,
            summary=summary,
            output_filepath=txt_report_path
        )
        ReportGenerator.generate_html_report(
            project_name="Film Project",
            preset_name=config.get("name", "Custom Preset"),
            source_dir=src,
            destinations=dests,
            hash_algorithm=config["hash_algorithm"],
            file_list=self.current_copy_engine.file_list,
            summary=summary,
            output_filepath=html_report_path
        )

        # Populate extra files in file table if present
        extra_files = summary.get("extra_files", [])
        if extra_files:
            self.file_table.populate_extra_files(extra_files)

        failed_files = [f for f in self.current_copy_engine.file_list if f.get("status") == "FAILED"]

        # Check for failures or extra files
        if failed_files or extra_files:
            self.sound_player.play_error()
            ChecksumAlertDialog(self, failed_files=failed_files, extra_files=extra_files)
        else:
            self.sound_player.play_success()

    def _cancel_copy(self):
        if self.current_copy_engine:
            self.current_copy_engine.cancel()

    def _clear_job_session(self):
        """Reset current job session (Source, Destinations, File List, Progress, Previews) to start a clean new project."""
        if self.is_copying:
            return

        # Clear Sidebar (Input & Destinations)
        if hasattr(self, "sidebar"):
            self.sidebar.clear_all()

        # Reset Progress Cards
        if hasattr(self, "progress_panel"):
            self.progress_panel.reset()

        # Clear File Table Rows
        if hasattr(self, "file_table"):
            self.file_table.clear()

        # Reset Job Flow Diagram
        if hasattr(self, "job_flow_panel"):
            self.job_flow_panel.set_data("", [])

        # Clear Preview Panel
        if hasattr(self, "preview_panel"):
            self.preview_panel.clear_preview()

        # Reset Engine state
        self.current_copy_engine = None
        self._has_played_sound = False

    def _show_feedback(self, message: str, color: str = None):
        """Show a temporary feedback message if speed badge exists."""
        if hasattr(self, "lbl_speed_badge") and self.lbl_speed_badge:
            if not color:
                color = theme.ACCENT_WARNING
            self.lbl_speed_badge.configure(text=f" {message} ", fg_color=color)
            self.after(3000, lambda: self.lbl_speed_badge.configure(
                text=" 0.0 MB/s ",
                fg_color=theme.ACCENT_PRIMARY
            ))

    def _on_closing(self):
        """Handle window close event - warn if copying in progress."""
        if self.is_copying:
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Xác nhận thoát",
                "Đang có quá trình sao chép diễn ra. Bạn có chắc chắn muốn thoát?"
            ):
                return
            if self.current_copy_engine:
                self.current_copy_engine.cancel()
        self.destroy()

    def _on_sidebar_media_file_selected(self, filepath: str):
        """Update the permanent 'Xem Trước (File Preview)' tab when a media file is clicked in the sidebar."""
        if not filepath or not os.path.exists(filepath) or not os.path.isfile(filepath):
            return

        abs_path = os.path.abspath(filepath)
        if hasattr(self, "preview_panel"):
            self.preview_panel.load_file(abs_path)
            try:
                self.tab_segmented_button.set("Xem Trước (File Preview)")
                self._switch_tab_view("Xem Trước (File Preview)")
            except Exception:
                pass

    def _on_segmented_tab_changed(self, value: str):
        self._switch_tab_view(value)

    def _switch_tab_view(self, tab_name: str):
        for frame_name in ("tab_jobflow_frame", "tab_files_frame", "tab_config_frame", "tab_preview_frame"):
            if hasattr(self, frame_name):
                getattr(self, frame_name).grid_forget()

        if tab_name == "Job Flow Diagram" and hasattr(self, "tab_jobflow_frame"):
            self.tab_jobflow_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            self._update_job_flow()
        elif tab_name == "Danh Sách File (Input/Output Status)" and hasattr(self, "tab_files_frame"):
            self.tab_files_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        elif tab_name == "Cấu Hình (Config Settings)" and hasattr(self, "tab_config_frame"):
            self.tab_config_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            self.tab_config_frame.update_idletasks()
            if hasattr(self, "config_panel"):
                self.config_panel.refresh_scroll()
        elif tab_name == "Xem Trước (File Preview)" and hasattr(self, "tab_preview_frame"):
            self.tab_preview_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self._on_tab_changed(tab_name)

    def _on_tab_changed(self, tab_name: Optional[str] = None):
        """Clear preview data when switching away from the permanent Preview tab."""
        if tab_name is None and hasattr(self, "tab_segmented_button"):
            try:
                tab_name = self.tab_segmented_button.get()
            except Exception:
                tab_name = ""

        if tab_name != "Xem Trước (File Preview)" and hasattr(self, "preview_panel"):
            self.preview_panel.clear_preview()


