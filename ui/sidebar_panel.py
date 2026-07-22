import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import os
import ui.theme as theme
from ui.collapsible_section import CollapsibleSection
from ui.tree_preview_widget import TreePreviewWidget


class ShotPutSidebar(ctk.CTkFrame):
    """
    Ultra-compact VS Code style Left Sidebar Panel.
    Features 3 equal-area resizable Collapsible Accordion Sections:
    1. INPUT (SOURCE) - Limited to 1 path
    2. OUTPUT (DESTINATIONS) - Unlimited paths, each displayed as an expandable file tree
    3. ALL DRIVES - Explorer for drives/folders

    Drag & Drop supported from ALL DRIVES into INPUT / OUTPUT.
    Right-click context menu on items to Delete / Remove / Set.
    """

    def __init__(self, master, on_source_changed=None, on_destinations_changed=None, on_media_file_select=None, **kwargs):
        super().__init__(master, fg_color=theme.PANEL_BG, corner_radius=0, **kwargs)

        self.on_source_changed = on_source_changed
        self.on_destinations_changed = on_destinations_changed
        self.on_media_file_select = on_media_file_select

        self.source_path = ""
        self.destinations = []
        self._drag_data = {"active": False, "path": ""}

        self._build_ui()
        self._load_initial_trees()

    def _handle_node_select(self, path: str):
        if path and os.path.isfile(path) and self.on_media_file_select:
            self.on_media_file_select(path)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Resizable vertical container for sidebar sections (no scrolling)
        self.vpaned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.vpaned.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # -------------------------------------------------------------
        # Section 1: INPUT (SOURCE)
        # -------------------------------------------------------------
        self.sec_input = CollapsibleSection(
            self.vpaned, title="INPUT (SOURCE)", is_open=True,
            on_toggle_callback=self._handle_section_toggled
        )
        self.vpaned.add(self.sec_input, weight=1)

        self.tree_input = TreePreviewWidget(
            self.sec_input.content_frame,
            height_rows=4,
            on_node_select_callback=self._handle_node_select,
            on_right_click_callback=self._on_input_right_click
        )
        self.tree_input.pack(fill="both", expand=True)
        self.tree_input.load_directory_tree("", placeholder="  (Kéo thả thư mục Nguồn vào đây)")

        # -------------------------------------------------------------
        # Section 2: OUTPUT (DESTINATIONS)
        # -------------------------------------------------------------
        self.sec_output = CollapsibleSection(
            self.vpaned, title="OUTPUT (DESTINATIONS)", is_open=True,
            on_toggle_callback=self._handle_section_toggled
        )
        self.vpaned.add(self.sec_output, weight=1)

        self.tree_output = TreePreviewWidget(
            self.sec_output.content_frame,
            height_rows=4,
            on_node_select_callback=self._handle_node_select,
            on_right_click_callback=self._on_output_right_click
        )
        self.tree_output.pack(fill="both", expand=True)
        self.tree_output.load_multiple_paths_tree([], placeholder="  (Kéo thả thư mục Đích vào đây)")

        # -------------------------------------------------------------
        # Section 3: ALL DRIVES
        # -------------------------------------------------------------
        self.sec_drives = CollapsibleSection(
            self.vpaned, title="ALL DRIVES", is_open=True,
            on_toggle_callback=self._handle_section_toggled
        )
        self.vpaned.add(self.sec_drives, weight=1)

        self.tree_drives = TreePreviewWidget(
            self.sec_drives.content_frame,
            height_rows=5,
            on_node_select_callback=self._handle_node_select,
            on_right_click_callback=self._on_drives_right_click
        )
        self.tree_drives.pack(fill="both", expand=True, pady=(0, 2))

        # Bind Drag & Drop mouse events on tree_drives
        drives_tv = self.tree_drives.tree
        drives_tv.bind("<ButtonPress-1>", self._on_drag_start, add="+")
        drives_tv.bind("<B1-Motion>", self._on_drag_motion, add="+")
        drives_tv.bind("<ButtonRelease-1>", self._on_drag_release, add="+")

        # Bind sash movement & window resize events to clamp collapsed pane sizes
        self.vpaned.bind("<B1-Motion>", self._clamp_sashes, add="+")
        self.vpaned.bind("<ButtonRelease-1>", self._clamp_sashes, add="+")
        self.bind("<Configure>", lambda e: self.after(20, self._clamp_sashes), add="+")

    # -----------------------------------------------------------------
    # Drag & Drop Handlers
    # -----------------------------------------------------------------
    def _on_drag_start(self, event):
        path = self.tree_drives.get_path_at_event(event)
        if path and os.path.exists(path):
            self._drag_data = {"active": True, "path": path}
        else:
            self._drag_data = {"active": False, "path": ""}

    def _on_drag_motion(self, event):
        if not self._drag_data["active"]:
            return

        x_root, y_root = event.x_root, event.y_root
        if self._is_inside(self.sec_input, x_root, y_root) or self._is_inside(self.sec_output, x_root, y_root):
            try:
                self.config(cursor="hand2")
            except Exception:
                pass
        else:
            try:
                self.config(cursor="")
            except Exception:
                pass

    def _on_drag_release(self, event):
        try:
            self.config(cursor="")
        except Exception:
            pass

        if not self._drag_data["active"]:
            return

        path = self._drag_data["path"]
        x_root, y_root = event.x_root, event.y_root

        if self._is_inside(self.sec_input, x_root, y_root):
            self.set_source_path(path)
        elif self._is_inside(self.sec_output, x_root, y_root):
            self.add_destination_path(path)

        self._drag_data = {"active": False, "path": ""}

    def _is_inside(self, widget, x_root, y_root) -> bool:
        try:
            wx = widget.winfo_rootx()
            wy = widget.winfo_rooty()
            ww = widget.winfo_width()
            wh = widget.winfo_height()
            return (wx <= x_root <= wx + ww) and (wy <= y_root <= wy + wh)
        except Exception:
            return False

    # -----------------------------------------------------------------
    # Right-Click Context Menus & File Operations
    # -----------------------------------------------------------------
    def _on_input_right_click(self, event, item_id, path):
        menu = tk.Menu(self, tearoff=0, bg=theme.CARD_BG, fg=theme.TEXT_MAIN, activebackground=theme.ACCENT_PRIMARY)

        if self.source_path:
            menu.add_command(label="❌ Bỏ chọn Nguồn khỏi ứng dụng", command=self.clear_source_path)

        if path and os.path.exists(path):
            if self.source_path:
                menu.add_separator()
            menu.add_command(label="📂 Mở trong trình duyệt file", command=lambda: self._action_open_in_explorer(path))
            menu.add_command(label="📋 Sao chép đường dẫn", command=lambda: self._action_copy_path(path))
            menu.add_command(label="📁 Tạo Thư mục mới...", command=lambda: self._action_new_folder(path))
            menu.add_command(label="✏️ Đổi tên...", command=lambda: self._action_rename(path))
            menu.add_command(label="🗑️ Xóa vĩnh viễn khỏi ổ đĩa", command=lambda: self._action_delete(path))

        if menu.index("end") is not None:
            menu.tk_popup(event.x_root, event.y_root)

    def _on_output_right_click(self, event, item_id, path):
        menu = tk.Menu(self, tearoff=0, bg=theme.CARD_BG, fg=theme.TEXT_MAIN, activebackground=theme.ACCENT_PRIMARY)

        root_path = self.tree_output.get_root_path_for_item(item_id) if item_id else ""

        if root_path and root_path in self.destinations:
            folder_name = os.path.basename(root_path.rstrip("/\\")) or root_path
            menu.add_command(
                label=f"❌ Bỏ chọn Đích: {folder_name}",
                command=lambda p=root_path: self.remove_destination_path(p)
            )

        if self.destinations:
            menu.add_command(label="❌ Bỏ chọn Tất Cả Đích", command=self.clear_destinations)

        if path and os.path.exists(path):
            menu.add_separator()
            menu.add_command(label="📂 Mở trong trình duyệt file", command=lambda: self._action_open_in_explorer(path))
            menu.add_command(label="📋 Sao chép đường dẫn", command=lambda: self._action_copy_path(path))
            menu.add_command(label="📁 Tạo Thư mục mới...", command=lambda: self._action_new_folder(path))
            menu.add_command(label="✏️ Đổi tên...", command=lambda: self._action_rename(path))
            menu.add_command(label="🗑️ Xóa vĩnh viễn khỏi ổ đĩa", command=lambda: self._action_delete(path))

        if menu.index("end") is not None:
            menu.tk_popup(event.x_root, event.y_root)

    def _on_drives_right_click(self, event, item_id, path):
        if not path or not os.path.exists(path):
            return

        name = os.path.basename(path.rstrip("/\\")) or path

        menu = tk.Menu(self, tearoff=0, bg=theme.CARD_BG, fg=theme.TEXT_MAIN, activebackground=theme.ACCENT_PRIMARY)
        menu.add_command(
            label=f"📥 Đặt làm Nguồn: {name}",
            command=lambda p=path: self.set_source_path(p)
        )
        menu.add_command(
            label=f"📤 Thêm vào Đích: {name}",
            command=lambda p=path: self.add_destination_path(p)
        )
        menu.add_separator()
        menu.add_command(label="📂 Mở trong trình duyệt file", command=lambda: self._action_open_in_explorer(path))
        menu.add_command(label="📋 Sao chép đường dẫn", command=lambda: self._action_copy_path(path))
        menu.add_command(label="📁 Tạo Thư mục mới...", command=lambda: self._action_new_folder(path))
        menu.add_command(label="✏️ Đổi tên...", command=lambda: self._action_rename(path))
        menu.add_command(label="🗑️ Xóa vĩnh viễn khỏi ổ đĩa", command=lambda: self._action_delete(path))

        menu.tk_popup(event.x_root, event.y_root)

    # -----------------------------------------------------------------
    # File Management Action Logic
    # -----------------------------------------------------------------
    def _action_open_in_explorer(self, target_path: str):
        if not target_path or not os.path.exists(target_path):
            return
        target_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)

        import sys
        import subprocess
        try:
            if sys.platform == "win32":
                os.startfile(target_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target_dir])
            else:
                subprocess.Popen(["xdg-open", target_dir])
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Lỗi", f"Không thể mở trình duyệt file: {e}")

    def _action_copy_path(self, target_path: str):
        if target_path:
            self.clipboard_clear()
            self.clipboard_append(target_path)
            self.update()

    def _action_new_folder(self, target_path: str):
        if not target_path or not os.path.exists(target_path):
            return
        target_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)

        dialog = ctk.CTkInputDialog(text="Nhập tên thư mục mới:", title="Tạo Thư Mục Mới")
        folder_name = dialog.get_input()
        if folder_name and folder_name.strip():
            new_folder_path = os.path.join(target_dir, folder_name.strip())
            try:
                os.makedirs(new_folder_path, exist_ok=True)
                self._refresh_all_trees()
            except Exception as e:
                tk.messagebox.showerror("Lỗi", f"Không thể tạo thư mục: {e}")

    def _action_rename(self, target_path: str):
        if not target_path or not os.path.exists(target_path):
            return
        old_name = os.path.basename(target_path.rstrip("/\\")) or target_path

        dialog = ctk.CTkInputDialog(text=f"Nhập tên mới cho '{old_name}':", title="Đổi Tên")
        new_name = dialog.get_input()
        if new_name and new_name.strip() and new_name.strip() != old_name:
            parent_dir = os.path.dirname(target_path.rstrip("/\\"))
            new_path = os.path.join(parent_dir, new_name.strip())
            try:
                open_input = self.tree_input.get_expanded_paths()
                open_output = self.tree_output.get_expanded_paths()

                os.rename(target_path, new_path)
                if target_path == self.source_path:
                    self.set_source_path(new_path)
                if target_path in self.destinations:
                    idx = self.destinations.index(target_path)
                    self.destinations[idx] = new_path

                updated_input = {p.replace(target_path, new_path) if p.startswith(target_path) else p for p in open_input}
                updated_output = {p.replace(target_path, new_path) if p.startswith(target_path) else p for p in open_output}

                self._refresh_all_trees(preserve_input_open=updated_input, preserve_output_open=updated_output)
            except Exception as e:
                tk.messagebox.showerror("Lỗi", f"Không thể đổi tên: {e}")

    def _action_delete(self, target_path: str):
        if not target_path or not os.path.exists(target_path):
            return
        name = os.path.basename(target_path.rstrip("/\\")) or target_path

        from tkinter import messagebox
        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn XÓA vĩnh viễn '{name}' khỏi ổ đĩa không?\n\nĐường dẫn: {target_path}",
            icon="warning"
        )
        if confirm:
            try:
                import shutil
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)

                if target_path == self.source_path:
                    self.clear_source_path()
                if target_path in self.destinations:
                    self.remove_destination_path(target_path)

                self._refresh_all_trees()
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Lỗi", f"Không thể xóa tệp/thư mục: {e}")

    def _refresh_all_trees(self, preserve_input_open: set = None, preserve_output_open: set = None):
        open_in = preserve_input_open if preserve_input_open is not None else self.tree_input.get_expanded_paths()
        open_out = preserve_output_open if preserve_output_open is not None else self.tree_output.get_expanded_paths()

        if self.source_path and os.path.exists(self.source_path):
            self.tree_input.load_directory_tree(self.source_path)
            self.tree_input.restore_expanded_paths(open_in)
        elif self.source_path:
            self.clear_source_path()

        if self.destinations:
            self.destinations = [d for d in self.destinations if os.path.exists(d)]
            self.tree_output.load_multiple_paths_tree(self.destinations, placeholder="  (Kéo thả thư mục Đích vào đây)")
            self.tree_output.restore_expanded_paths(open_out)

        self._load_initial_trees()

    def update_sidebar_tree_status(self, file_list: list, extra_files: list = None, expand_output: bool = False):
        """
        Updates sidebar trees with Cyan (copying), Red (failed/missing), Yellow (extra), or Green (verified) tags.
        """
        self.tree_input.refresh_tree_live()
        self.tree_output.refresh_tree_live()

        if expand_output:
            self.tree_output.expand_all_nodes()

        status_dict = {}
        for f in file_list:
            status = f.get("status", "QUEUED")
            if "source_path" in f:
                status_dict[os.path.normpath(f["source_path"])] = status
            for dst in f.get("dest_paths", []):
                if status == "FAILED" and not os.path.exists(dst):
                    status_dict[os.path.normpath(dst)] = "MISSING"
                else:
                    status_dict[os.path.normpath(dst)] = status

        if extra_files:
            for ef in extra_files:
                if "dest_path" in ef:
                    status_dict[os.path.normpath(ef["dest_path"])] = "EXTRA"

        self.tree_input.update_node_statuses(status_dict)
        self.tree_output.update_node_statuses(status_dict)

    # -----------------------------------------------------------------
    # Public Data Management Methods
    # -----------------------------------------------------------------
    def get_source_path(self) -> str:
        return self.source_path

    def set_source_path(self, path: str):
        if path and os.path.exists(path):
            self.source_path = os.path.abspath(path)
            self.tree_input.load_directory_tree(self.source_path)
            if self.on_source_changed:
                self.on_source_changed(self.source_path)

    def clear_source_path(self):
        self.source_path = ""
        self.tree_input.load_directory_tree("", placeholder="  (Kéo thả thư mục Nguồn vào đây)")
        if self.on_source_changed:
            self.on_source_changed("")

    def get_destinations(self) -> list[str]:
        return list(self.destinations)

    def add_destination_path(self, path: str):
        if path and os.path.exists(path):
            abs_path = os.path.abspath(path)
            if abs_path not in self.destinations:
                self.destinations.append(abs_path)
                self.tree_output.load_multiple_paths_tree(self.destinations)
                if self.on_destinations_changed:
                    self.on_destinations_changed(self.get_destinations())

    def remove_destination_path(self, path: str):
        abs_path = os.path.abspath(path)
        if abs_path in self.destinations:
            self.destinations.remove(abs_path)
            self.tree_output.load_multiple_paths_tree(self.destinations, placeholder="  (Kéo thả thư mục Đích vào đây)")
            if self.on_destinations_changed:
                self.on_destinations_changed(self.get_destinations())

    def clear_destinations(self):
        self.destinations.clear()
        self.tree_output.load_multiple_paths_tree([], placeholder="  (Kéo thả thư mục Đích vào đây)")
        if self.on_destinations_changed:
            self.on_destinations_changed([])

    def clear_all(self):
        """Clear both input source path and all output destination paths."""
        self.clear_source_path()
        self.clear_destinations()


    # -----------------------------------------------------------------
    # Layout Clamping & Section Handling
    # -----------------------------------------------------------------
    def _handle_section_toggled(self):
        self.after(10, self._rebalance_sections)

    def _clamp_sashes(self, event=None):
        """Clamp sash positions so collapsed sections stay fixed at header height (~30px) without black gaps or overlaps."""
        total_h = self.vpaned.winfo_height()
        if total_h < 100:
            return

        HEADER_H = 30.0

        try:
            y0 = float(self.vpaned.sashpos(0))
            y1 = float(self.vpaned.sashpos(1))
        except Exception:
            return

        sec0_open = self.sec_input.is_open
        sec1_open = self.sec_output.is_open
        sec2_open = self.sec_drives.is_open

        # Clamp Section 0
        if not sec0_open:
            y0 = HEADER_H
        else:
            y0 = max(HEADER_H, y0)

        # Clamp Section 1 (y1 - y0)
        if not sec1_open:
            if not sec0_open:
                y0 = HEADER_H
                y1 = y0 + HEADER_H
            elif not sec2_open:
                y1 = float(total_h) - HEADER_H
                y0 = y1 - HEADER_H
            else:
                y1 = max(y0 + HEADER_H, min(float(total_h) - HEADER_H, y1))
                y0 = y1 - HEADER_H
        else:
            y0 = min(y0, float(total_h) - 2 * HEADER_H)
            y1 = max(y0 + HEADER_H, min(float(total_h) - HEADER_H, y1))

        # Clamp Section 2
        if not sec2_open:
            y1 = float(total_h) - HEADER_H
            if not sec1_open:
                y0 = y1 - HEADER_H

        try:
            self.vpaned.sashpos(0, int(y0))
            self.vpaned.sashpos(1, int(y1))
        except Exception:
            pass

    def _rebalance_sections(self):
        """Dynamically synchronize section collapse/expand with PanedWindow sash splitters."""
        self.update_idletasks()
        sections = [self.sec_input, self.sec_output, self.sec_drives]

        total_h = self.vpaned.winfo_height()
        if total_h < 100:
            total_h = self.winfo_height()
        if total_h < 100:
            total_h = 600

        header_h = 30
        open_sections = [s for s in sections if s.is_open]
        open_count = len(open_sections)
        collapsed_count = len(sections) - open_count

        avail_h = max(30 * max(1, open_count), total_h - (collapsed_count * header_h))
        height_per_open = avail_h / max(1, open_count)

        curr_y = 0.0
        for i, sec in enumerate(sections):
            if sec.is_open:
                self.vpaned.pane(sec, weight=1)
                curr_y += height_per_open
            else:
                self.vpaned.pane(sec, weight=0)
                curr_y += header_h

            if i < len(sections) - 1:
                try:
                    self.vpaned.sashpos(i, int(curr_y))
                except Exception:
                    pass

    def _load_initial_trees(self):
        """Populate All Drives tree on startup."""
        drives_list = self._detect_all_drives()
        self.tree_drives.load_drives_tree(drives_list)

    def _detect_all_drives(self) -> list[tuple[str, str]]:
        drives = [("Root (/)", "/")]
        home = os.path.expanduser("~")
        drives.append((f"Home ({os.path.basename(home)})", home))

        media_dir = f"/media/{os.environ.get('USER', '')}"
        if os.path.exists(media_dir):
            for d in sorted(os.listdir(media_dir)):
                full_p = os.path.join(media_dir, d)
                if os.path.isdir(full_p):
                    drives.append((f"Volume ({d})", full_p))

        mnt_dir = "/mnt"
        if os.path.exists(mnt_dir):
            for d in sorted(os.listdir(mnt_dir)):
                full_p = os.path.join(mnt_dir, d)
                if os.path.isdir(full_p):
                    drives.append((f"Mount ({d})", full_p))

        return drives
