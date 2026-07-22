import os
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import ui.theme as theme


class TreePreviewWidget(ctk.CTkFrame):
    """
    Ultra-compact VS Code style File Tree Preview Widget using ttk.Treeview.
    Displays directories and files with icons (📁, 🎬, 📄, 💽) and supports lazy folder expansion.
    """

    def __init__(self, master, height_rows: int = 5, on_node_select_callback=None, on_right_click_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)

        self.on_node_select = on_node_select_callback
        self.on_right_click_callback = on_right_click_callback
        self.height_rows = height_rows
        self._current_status_dict = {}

        self._init_style()
        self._build_ui()
        self._start_auto_polling()

    def _init_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "VSCode.Treeview",
            background=theme.CARD_BG,
            foreground=theme.TEXT_MAIN,
            fieldbackground=theme.CARD_BG,
            bordercolor=theme.CARD_BG,
            relief="flat",
            borderwidth=0,
            rowheight=20,
            font=(theme.FONT_FAMILY, 9)
        )
        style.configure(
            "VSCode.Treeview.Heading",
            background=theme.PANEL_BG,
            foreground=theme.TEXT_MAIN,
            font=(theme.FONT_FAMILY, 9, "bold")
        )
        style.map(
            "VSCode.Treeview",
            background=[("selected", theme.ACCENT_PRIMARY)],
            foreground=[("selected", "#ffffff")]
        )

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(self, fg_color=theme.CARD_BG, corner_radius=0, border_width=0)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            style="VSCode.Treeview",
            selectmode="browse",
            height=self.height_rows,
            show="tree"
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        # Configure color tags for sidebar tree preview
        self.tree.tag_configure("copying", foreground="#00d2d3")   # Vibrant Cyan Blue
        self.tree.tag_configure("verified", foreground="#34c759")  # Green
        self.tree.tag_configure("failed", foreground="#ff3b30")    # Red
        self.tree.tag_configure("extra", foreground="#ff9500")     # Yellow / Orange

        self.tree.bind("<<TreeviewOpen>>", self._on_tree_expand)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def load_directory_tree(self, root_path: str, placeholder: str = "  (Kéo thả thư mục Nguồn vào đây)"):
        """Populate file/folder tree for a given source directory path."""
        self.clear()
        if not root_path or not os.path.exists(root_path):
            self.tree.insert("", "end", text=placeholder, values=[""])
            return

        root_name = os.path.basename(root_path.rstrip("/\\")) or root_path
        node_id = self.tree.insert("", "end", text=f"📁 {root_name}", open=True, values=[root_path])
        self._populate_subnodes(node_id, root_path)

    def load_multiple_paths_tree(self, paths: list[str], placeholder: str = "  (Kéo thả thư mục Đích vào đây)"):
        """Populate tree for multiple paths (e.g. Destinations) and auto-open them."""
        self.clear()
        if not paths:
            self.tree.insert("", "end", text=placeholder, values=[""])
            return

        for p in paths:
            if p and os.path.exists(p):
                name = os.path.basename(p.rstrip("/\\")) or p
                node_id = self.tree.insert("", "end", text=f"💽 {name}", open=True, values=[p])
                self._populate_subnodes(node_id, p)

    def load_drives_tree(self, drive_list: list[tuple[str, str]]):
        """Populate list of system drives."""
        self.clear()
        for label, p in drive_list:
            if os.path.exists(p):
                node_id = self.tree.insert("", "end", text=f"💽 {label}", open=False, values=[p])
                self.tree.insert(node_id, "end", text="Loading...")

    def _populate_subnodes(self, parent_node, dir_path: str):
        """Read items inside dir_path and add to tree."""
        try:
            entries = sorted(os.listdir(dir_path))
        except Exception:
            return

        for child in list(self.tree.get_children(parent_node)):
            self.tree.delete(child)

        for entry in entries:
            if entry.startswith("."):
                continue

            full_p = os.path.join(dir_path, entry)
            norm_p = os.path.normpath(full_p)
            is_dir = os.path.isdir(full_p)

            ext = os.path.splitext(entry)[1].lower()
            if is_dir:
                icon = "📁"
            elif ext in (".mxf", ".mov", ".mp4", ".ari", ".r3d", ".braw", ".arw", ".cr3"):
                icon = "🎬"
            elif ext in (".jpg", ".png", ".tif", ".dng"):
                icon = "🖼"
            else:
                icon = "📄"

            # Apply stored status tag if present
            node_tag = ()
            if norm_p in self._current_status_dict:
                st = self._current_status_dict[norm_p]
                if st == "COPYING":
                    node_tag = ("copying",)
                elif st in ("FAILED", "MISSING"):
                    node_tag = ("failed",)
                elif st == "EXTRA":
                    node_tag = ("extra",)
                elif st == "VERIFIED":
                    node_tag = ("verified",)

            child_id = self.tree.insert(parent_node, "end", text=f" {icon} {entry}", values=[full_p], tags=node_tag)
            if is_dir:
                self.tree.insert(child_id, "end", text="Loading...")

        if self._current_status_dict:
            self.update_node_statuses(self._current_status_dict)

    def _on_tree_expand(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        vals = self.tree.item(selected, "values")
        if vals and len(vals) > 0:
            target_path = vals[0]
            if target_path and os.path.isdir(target_path):
                self._populate_subnodes(selected, target_path)

    def _on_tree_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return

        vals = self.tree.item(selected, "values")
        if vals and len(vals) > 0 and self.on_node_select:
            self.on_node_select(vals[0])

    def _on_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            vals = self.tree.item(item_id, "values")
            if vals and len(vals) > 0 and vals[0] and self.on_node_select:
                self.on_node_select(vals[0])

    def _on_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
        if self.on_right_click_callback:
            path = self.get_path_at_event(event)
            self.on_right_click_callback(event, item_id, path)

    def get_path_at_event(self, event) -> str:
        item_id = self.tree.identify_row(event.y)
        if item_id:
            vals = self.tree.item(item_id, "values")
            if vals and len(vals) > 0:
                return vals[0]
        return ""

    def get_root_path_for_item(self, item_id: str) -> str:
        """Find the top-level root path associated with an item."""
        curr = item_id
        while curr:
            parent = self.tree.parent(curr)
            if not parent:
                vals = self.tree.item(curr, "values")
                if vals and len(vals) > 0:
                    return vals[0]
                break
            curr = parent
        return ""

    def get_selected_path(self) -> str:
        selected = self.tree.focus()
        if selected:
            vals = self.tree.item(selected, "values")
            if vals and len(vals) > 0:
                return vals[0]
        return ""

    def get_expanded_paths(self) -> set[str]:
        """Returns set of all directory paths currently expanded in tree."""
        open_paths = set()
        def recurse(item_id):
            if self.tree.item(item_id, "open"):
                vals = self.tree.item(item_id, "values")
                if vals and len(vals) > 0 and vals[0]:
                    open_paths.add(vals[0])
            for child in self.tree.get_children(item_id):
                recurse(child)
        for root_item in self.tree.get_children():
            recurse(root_item)
        return open_paths

    def expand_all_nodes(self):
        """Recursively expands all directory nodes down to leaf files."""
        def recurse(item_id):
            vals = self.tree.item(item_id, "values")
            if vals and len(vals) > 0 and vals[0]:
                p = vals[0]
                if os.path.isdir(p):
                    self.tree.item(item_id, open=True)
                    self._populate_subnodes(item_id, p)
            for child in list(self.tree.get_children(item_id)):
                recurse(child)

        for root_item in list(self.tree.get_children()):
            recurse(root_item)

    def restore_expanded_paths(self, open_paths: set[str]):
        """Restores expanded state for all directory paths in open_paths."""
        if not open_paths:
            return
        def recurse(item_id):
            vals = self.tree.item(item_id, "values")
            if vals and len(vals) > 0 and vals[0]:
                p = vals[0]
                if p in open_paths:
                    self.tree.item(item_id, open=True)
                    if os.path.isdir(p):
                        self._populate_subnodes(item_id, p)
            for child in self.tree.get_children(item_id):
                recurse(child)
        for root_item in self.tree.get_children():
            recurse(root_item)

    def rename_item_in_place(self, old_path: str, new_path: str):
        """Updates node text and path in-place without reloading the entire tree."""
        new_name = os.path.basename(new_path.rstrip("/\\"))
        def recurse(item_id):
            vals = self.tree.item(item_id, "values")
            if vals and len(vals) > 0 and vals[0] == old_path:
                ext = os.path.splitext(new_name)[1].lower()
                is_dir = os.path.isdir(new_path)
                if is_dir:
                    icon = "📁"
                elif ext in (".mxf", ".mov", ".mp4", ".ari", ".r3d", ".braw", ".arw", ".cr3"):
                    icon = "🎬"
                elif ext in (".jpg", ".png", ".tif", ".dng"):
                    icon = "🖼"
                else:
                    icon = "📄"
                
                tags = self.tree.item(item_id, "tags")
                self.tree.item(item_id, text=f" {icon} {new_name}", values=[new_path], tags=tags)
                return True
            for child in self.tree.get_children(item_id):
                if recurse(child):
                    return True
            return False

        for root_item in self.tree.get_children():
            recurse(root_item)

    def update_node_statuses(self, status_dict: dict[str, str]):
        """
        status_dict maps normpath -> "COPYING", "VERIFIED", "FAILED", "MISSING", "EXTRA"
        Highlights nodes in Cyan (copying), Red (failed/missing), Yellow (extra), or Green (verified).
        """
        if status_dict:
            self._current_status_dict.update(status_dict)

        def recurse(item_id) -> str:
            vals = self.tree.item(item_id, "values")
            node_status = ""
            if vals and len(vals) > 0 and vals[0]:
                norm_p = os.path.normpath(vals[0])
                if norm_p in self._current_status_dict:
                    node_status = self._current_status_dict[norm_p]

            child_statuses = []
            for child in self.tree.get_children(item_id):
                st = recurse(child)
                if st:
                    child_statuses.append(st)

            if not node_status:
                if "FAILED" in child_statuses or "MISSING" in child_statuses:
                    node_status = "FAILED"
                elif "COPYING" in child_statuses:
                    node_status = "COPYING"
                elif "EXTRA" in child_statuses:
                    node_status = "EXTRA"
                elif child_statuses and all(c == "VERIFIED" for c in child_statuses):
                    node_status = "VERIFIED"

            if node_status == "COPYING":
                self.tree.item(item_id, tags=("copying",))
            elif node_status in ("FAILED", "MISSING"):
                self.tree.item(item_id, tags=("failed",))
            elif node_status == "EXTRA":
                self.tree.item(item_id, tags=("extra",))
            elif node_status == "VERIFIED":
                self.tree.item(item_id, tags=("verified",))

            return node_status

        for root_item in self.tree.get_children():
            recurse(root_item)

    def _start_auto_polling(self):
        """Starts periodic disk auto-sync every 2000ms."""
        self._auto_poll_disk_changes()

    def _auto_poll_disk_changes(self):
        if self.winfo_exists():
            try:
                self.refresh_tree_live()
            except Exception:
                pass
            self.after(2000, self._auto_poll_disk_changes)

    def refresh_tree_live(self):
        """
        Scans disk for changes in loaded directories.
        Adds new files, removes deleted files, updates renamed files,
        preserving open folder states and color tags.
        """
        open_paths = self.get_expanded_paths()

        def update_folder_children(parent_node, dir_path):
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return

            try:
                disk_entries = set(e for e in os.listdir(dir_path) if not e.startswith("."))
            except Exception:
                return

            existing_items = {}
            for child in self.tree.get_children(parent_node):
                vals = self.tree.item(child, "values")
                if vals and len(vals) > 0 and vals[0]:
                    existing_items[vals[0]] = child

            # Delete items no longer on disk
            for p, child_id in list(existing_items.items()):
                if not os.path.exists(p) or os.path.basename(p) not in disk_entries:
                    self.tree.delete(child_id)
                    del existing_items[p]

            # Add new items from disk
            existing_basenames = set(os.path.basename(p) for p in existing_items.keys())
            new_entries = sorted(disk_entries - existing_basenames)

            for entry in new_entries:
                full_p = os.path.join(dir_path, entry)
                is_dir = os.path.isdir(full_p)
                ext = os.path.splitext(entry)[1].lower()
                if is_dir:
                    icon = "📁"
                elif ext in (".mxf", ".mov", ".mp4", ".ari", ".r3d", ".braw", ".arw", ".cr3"):
                    icon = "🎬"
                elif ext in (".jpg", ".png", ".tif", ".dng"):
                    icon = "🖼"
                else:
                    icon = "📄"

                child_id = self.tree.insert(parent_node, "end", text=f" {icon} {entry}", values=[full_p])
                if is_dir:
                    self.tree.insert(child_id, "end", text="Loading...")
                    existing_items[full_p] = child_id

            # Recurse into expanded subfolders
            for p, child_id in list(existing_items.items()):
                if p in open_paths and os.path.isdir(p):
                    self.tree.item(child_id, open=True)
                    update_folder_children(child_id, p)

        for root_item in list(self.tree.get_children()):
            vals = self.tree.item(root_item, "values")
            if vals and len(vals) > 0 and vals[0]:
                root_path = vals[0]
                if os.path.exists(root_path) and os.path.isdir(root_path):
                    update_folder_children(root_item, root_path)


