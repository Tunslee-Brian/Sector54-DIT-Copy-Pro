import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import platform
import os
import ui.theme as theme


class JobFlowPanel(ctk.CTkFrame):
    """
    ShotPut Pro style Job Flow Diagram Panel.
    Visualizes [Source Folder] -> [Host Machine] -> [Destination Folders].
    Click any node to view detailed path info in the sidebar.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER, **kwargs)

        self.source_path = ""
        self.destinations = []
        self._resize_timer_id = None
        self._selected_node = None

        self._init_host_info()
        self._build_ui()

    def _schedule_redraw(self):
        if self._resize_timer_id is not None:
            try:
                self.after_cancel(self._resize_timer_id)
            except Exception:
                pass
        self._resize_timer_id = self.after(35, self._draw_flow_debounced)

    def _draw_flow_debounced(self):
        self._resize_timer_id = None
        self.draw_flow()

    @staticmethod
    def _detect_ram_gb() -> str:
        try:
            import psutil
            ram_bytes = psutil.virtual_memory().total
            return f"{round(ram_bytes / (1024**3))}"
        except Exception:
            pass
        try:
            import sys
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(mem)
                if kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                    return f"{round(mem.ullTotalPhys / (1024**3))}"
            elif sys.platform == "linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return f"{round(kb / (1024**2))}"
            elif sys.platform == "darwin":
                import subprocess
                res = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0 and res.stdout.strip():
                    return f"{round(int(res.stdout.strip()) / (1024**3))}"
        except Exception:
            pass
        return "16"

    def _init_host_info(self):
        """Retrieve host machine hardware/OS specs dynamically."""
        self.host_name = platform.node() or "Local Workstation"

        system = platform.system()
        release = platform.release()
        if system == "Windows" and release == "10":
            try:
                import sys
                if hasattr(sys, "getwindowsversion"):
                    win_ver = sys.getwindowsversion()
                    if win_ver.build >= 22000:
                        release = "11"
            except Exception:
                pass

        self.sys_info = f"{system} {release}"
        self.cpu_cores = os.cpu_count() or 4

        self.ram_gb = self._detect_ram_gb()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent", height=32)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 0))

        lbl_title = ctk.CTkLabel(
            header,
            text="Job Flow",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_title.grid(row=0, column=0, sticky="w")

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        canvas_frame = ctk.CTkFrame(paned, fg_color="transparent")
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=theme.CARD_BG,
            highlightthickness=0,
            bd=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", lambda e: self._schedule_redraw())

        paned.add(canvas_frame, weight=1)

        self._build_sidebar(paned)

    def _build_sidebar(self, paned):
        sidebar = ctk.CTkFrame(paned, fg_color=theme.PANEL_BG, corner_radius=0, border_width=0)
        self.sidebar = sidebar

        title_lbl = ctk.CTkLabel(
            sidebar,
            text="Chi tiết",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=theme.TEXT_MAIN
        )
        title_lbl.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkFrame(sidebar, fg_color=theme.CARD_BORDER, height=1).pack(fill="x", padx=12, pady=(0, 10))

        self.lbl_type = ctk.CTkLabel(
            sidebar,
            text="",
            font=(theme.FONT_FAMILY, 12, "bold"),
            text_color=theme.ACCENT_PRIMARY,
            anchor="w"
        )
        self.lbl_type.pack(fill="x", padx=12, pady=(0, 2))

        self.lbl_icon = ctk.CTkLabel(
            sidebar,
            text="",
            font=(theme.FONT_FAMILY, 28),
            anchor="w"
        )
        self.lbl_icon.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            sidebar,
            text="Đường dẫn đầy đủ:",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.TEXT_MUTED,
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 2))

        self.lbl_full_path = ctk.CTkLabel(
            sidebar,
            text="",
            font=(theme.FONT_FAMILY, 10),
            text_color=theme.TEXT_MAIN,
            anchor="w",
            justify="left",
            wraplength=240
        )
        self.lbl_full_path.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            sidebar,
            text="Thông tin ổ đĩa:",
            font=(theme.FONT_FAMILY, 10, "bold"),
            text_color=theme.TEXT_MUTED,
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 2))

        self.lbl_drive_info = ctk.CTkLabel(
            sidebar,
            text="",
            font=(theme.FONT_FAMILY, 10),
            text_color=theme.TEXT_MAIN,
            anchor="w",
            justify="left",
            wraplength=240
        )
        self.lbl_drive_info.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkFrame(sidebar, fg_color=theme.CARD_BORDER, height=1).pack(fill="x", padx=12, pady=(0, 10))

        self.sidebar_hint = ctk.CTkLabel(
            sidebar,
            text="Nhấp vào node Input hoặc Output\nphía trên để xem chi tiết",
            font=(theme.FONT_FAMILY, 10),
            text_color=theme.TEXT_DIM,
            anchor="w",
            justify="left"
        )
        self.sidebar_hint.pack(fill="x", padx=12, pady=(0, 12))

        paned.add(sidebar, weight=0)

        sidebar.bind("<Configure>", self._on_sidebar_resize)

    def _on_sidebar_resize(self, event=None):
        w = self.sidebar.winfo_width() - 24
        if w > 50:
            self.lbl_full_path.configure(wraplength=w)
            self.lbl_drive_info.configure(wraplength=w)

    def set_data(self, source_path: str, destinations: list[str]):
        """Update source and destination paths and redraw the diagram."""
        self.source_path = source_path
        self.destinations = destinations
        self._selected_node = None
        self._clear_detail()
        self.draw_flow()

    def _clear_detail(self):
        self.lbl_type.configure(text="")
        self.lbl_icon.configure(text="")
        self.lbl_full_path.configure(text="")
        self.lbl_drive_info.configure(text="")
        self.sidebar_hint.configure(text="Nhấp vào node Input hoặc Output\nphía trên để xem chi tiết")

    def _show_detail(self, node_type: str, path: str, index: int = None):
        if not path:
            return
        if node_type == "source":
            self.lbl_type.configure(text="[ INPUT ]  Thư mục nguồn", text_color=theme.ACCENT_PRIMARY)
            self.lbl_icon.configure(text="📁")
            self.sidebar_hint.configure(text="")
        else:
            self.lbl_type.configure(text=f"[ OUTPUT #{index + 1} ]  Thư mục đích", text_color=theme.ACCENT_REPLICATION)
            self.lbl_icon.configure(text="💽")
            self.sidebar_hint.configure(text="")

        self.lbl_full_path.configure(text=path)

        drive_info = self._get_drive_info(path)
        self.lbl_drive_info.configure(text=drive_info)

    @staticmethod
    def _get_drive_info(path: str) -> str:
        try:
            import psutil
            usage = psutil.disk_usage(path)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            used_pct = usage.percent
            return f"Dung lượng: {total_gb:.0f} GB\nCòn trống: {free_gb:.1f} GB\nĐã dùng: {used_pct:.0f}%"
        except Exception:
            try:
                import shutil
                total, used, free = shutil.disk_usage(path)
                free_gb = free / (1024 ** 3)
                total_gb = total / (1024 ** 3)
                return f"Dung lượng: {total_gb:.0f} GB\nCòn trống: {free_gb:.1f} GB"
            except Exception:
                return "Không thể đọc thông tin ổ đĩa"

    def _on_canvas_click(self, event):
        if not self.source_path and not self.destinations:
            return

        src_hit, dest_hit = self._hit_test(event.x, event.y)

        if src_hit:
            if self._selected_node == ("source", None):
                self._selected_node = None
                self._clear_detail()
            else:
                self._selected_node = ("source", None)
                self._show_detail("source", self.source_path)
            self._highlight_selection()
            return

        if dest_hit is not None:
            idx = dest_hit
            if self._selected_node == ("dest", idx):
                self._selected_node = None
                self._clear_detail()
            else:
                self._selected_node = ("dest", idx)
                self._show_detail("dest", self.destinations[idx], idx)
            self._highlight_selection()
            return

        self._selected_node = None
        self._clear_detail()
        self._highlight_selection()

    def _hit_test(self, x, y):
        src_rect = getattr(self, "_src_rect", None)
        if src_rect and src_rect[0] <= x <= src_rect[2] and src_rect[1] <= y <= src_rect[3]:
            return True, None

        dest_rects = getattr(self, "_dest_rects", [])
        for idx, rect in enumerate(dest_rects):
            if rect and rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                return False, idx

        return False, None

    def _highlight_selection(self):
        self.canvas.delete("highlight")

        if self._selected_node is None:
            return

        ntype, idx = self._selected_node
        if ntype == "source":
            rect = getattr(self, "_src_rect", None)
            if rect:
                self.canvas.create_rectangle(
                    rect[0] - 3, rect[1] - 3, rect[2] + 3, rect[3] + 3,
                    outline=theme.ACCENT_PRIMARY, width=3, tags="highlight", dash=(6, 3)
                )
        elif ntype == "dest":
            rects = getattr(self, "_dest_rects", [])
            if 0 <= idx < len(rects):
                rect = rects[idx]
                if rect:
                    self.canvas.create_rectangle(
                        rect[0] - 3, rect[1] - 3, rect[2] + 3, rect[3] + 3,
                        outline=theme.ACCENT_REPLICATION, width=3, tags="highlight", dash=(6, 3)
                    )

    def draw_flow(self):
        """Redraw nodes and curved connecting lines."""
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w <= 10 or h <= 10:
            return

        cy = h / 2

        # -------------------------------------------------------------
        # 1. Draw Center Node: Host Workstation
        # -------------------------------------------------------------
        center_x = w / 2
        card_w, card_h = 220, 135
        left_c = center_x - card_w / 2
        top_c = cy - card_h / 2
        right_c = center_x + card_w / 2
        bot_c = cy + card_h / 2

        self._draw_rounded_rect(
            left_c, top_c, right_c, bot_c, radius=10,
            fill=theme.PANEL_BG, outline=theme.CARD_BORDER, width=2
        )

        self.canvas.create_text(
            center_x, top_c + 20,
            text="💻",
            font=(theme.FONT_FAMILY, 20),
            fill=theme.TEXT_MAIN
        )

        display_host = self.host_name if len(self.host_name) <= 24 else self.host_name[:22] + ".."
        self.canvas.create_text(
            center_x, top_c + 45,
            text=display_host,
            font=(theme.FONT_FAMILY, 12, "bold"),
            fill=theme.TEXT_MAIN
        )
        self.canvas.create_text(
            center_x, top_c + 68,
            text=f"{self.sys_info}",
            font=(theme.FONT_FAMILY, 10),
            fill=theme.TEXT_MUTED
        )
        self.canvas.create_text(
            center_x, top_c + 88,
            text=f"RAM: {self.ram_gb} GB",
            font=(theme.FONT_FAMILY, 10),
            fill=theme.TEXT_MUTED
        )
        self.canvas.create_text(
            center_x, top_c + 108,
            text=f"Cores: {self.cpu_cores}",
            font=(theme.FONT_FAMILY, 10),
            fill=theme.TEXT_MUTED
        )

        # -------------------------------------------------------------
        # 2. Draw Left Node: Source Folder / Drive
        # -------------------------------------------------------------
        src_w, src_h = 220, 85
        src_x = max(130, w * 0.18)
        src_y = cy

        src_left = src_x - src_w / 2
        src_top = src_y - src_h / 2
        src_right = src_x + src_w / 2
        src_bot = src_y + src_h / 2
        self._src_rect = (src_left, src_top, src_right, src_bot)

        src_border = theme.ACCENT_PRIMARY if self.source_path else theme.CARD_BORDER
        self._draw_rounded_rect(
            src_left, src_top, src_right, src_bot, radius=8,
            fill=theme.PANEL_BG, outline=src_border, width=2,
        )

        src_name = os.path.basename(self.source_path.rstrip("/\\")) if self.source_path else "Chưa chọn Nguồn"
        if len(src_name) > 28:
            src_name = src_name[:26] + ".."

        self.canvas.create_text(
            src_left + 28, src_y - 15,
            text="📁", font=(theme.FONT_FAMILY, 18), fill=theme.TEXT_MAIN
        )
        self.canvas.create_text(
            src_left + 55, src_y - 15,
            text=src_name, font=(theme.FONT_FAMILY, 11, "bold"), fill=theme.TEXT_MAIN, anchor="w"
        )

        self.canvas.create_text(
            src_left + 55, src_y + 26,
            text="[ Nguồn Source ]", font=(theme.FONT_FAMILY, 9), fill=theme.TEXT_MUTED, anchor="w"
        )

        # Connection curve from Source to Host
        self._draw_bezier(
            src_right, src_y,
            left_c, cy,
            color=theme.ACCENT_PRIMARY if self.source_path else theme.CARD_BORDER,
            width=2
        )

        # -------------------------------------------------------------
        # 3. Draw Right Nodes: Destination Folders
        # -------------------------------------------------------------
        dests = self.destinations if self.destinations else [""]
        num_dests = len(dests)

        spacing = min(110, max(70, (h - 40) / max(1, num_dests)))
        start_y = cy - ((num_dests - 1) * spacing) / 2

        dest_x = min(w - 130, w * 0.82)
        dest_w, dest_h = 220, 85
        self._dest_rects = []

        for i, dest_path in enumerate(dests):
            dy = start_y + i * spacing
            d_left = dest_x - dest_w / 2
            d_top = dy - dest_h / 2
            d_right = dest_x + dest_w / 2
            d_bot = dy + dest_h / 2
            self._dest_rects.append((d_left, d_top, d_right, d_bot))

            dest_border = theme.ACCENT_REPLICATION if dest_path else theme.CARD_BORDER
            self._draw_rounded_rect(
                d_left, d_top, d_right, d_bot, radius=8,
                fill=theme.PANEL_BG, outline=dest_border, width=2
            )

            d_name = os.path.basename(dest_path.rstrip("/\\")) if dest_path else f"Chưa chọn Đích #{i+1}"
            if len(d_name) > 28:
                d_name = d_name[:26] + ".."

            self.canvas.create_text(
                d_left + 28, dy - 15,
                text="💽", font=(theme.FONT_FAMILY, 18), fill=theme.TEXT_MAIN
            )
            self.canvas.create_text(
                d_left + 55, dy - 15,
                text=d_name, font=(theme.FONT_FAMILY, 11, "bold"), fill=theme.TEXT_MAIN, anchor="w"
            )

            self.canvas.create_text(
                d_left + 55, dy + 26,
                text=f"[ Đích #{i+1} ]", font=(theme.FONT_FAMILY, 9), fill=theme.TEXT_MUTED, anchor="w"
            )

            # Connection curve from Host to Destination
            self._draw_bezier(
                right_c, cy,
                d_left, dy,
                color=theme.ACCENT_REPLICATION if dest_path else theme.CARD_BORDER,
                width=2
            )

        self._highlight_selection()

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=8, **kwargs):
        """Draw a smooth rounded rectangle on tkinter canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_bezier(self, x1, y1, x2, y2, color, width=2):
        """Draw a smooth horizontal S-curve connecting two nodes."""
        cx1 = x1 + (x2 - x1) * 0.5
        cy1 = y1
        cx2 = x1 + (x2 - x1) * 0.5
        cy2 = y2

        self.canvas.create_line(
            x1, y1, cx1, cy1, cx2, cy2, x2, y2,
            smooth=True, fill=color, width=width
        )
