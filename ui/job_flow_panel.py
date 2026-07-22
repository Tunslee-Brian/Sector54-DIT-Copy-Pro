import tkinter as tk
import customtkinter as ctk
import platform
import os
import ui.theme as theme


class JobFlowPanel(ctk.CTkFrame):
    """
    ShotPut Pro style Job Flow Diagram Panel.
    Visualizes [Source Folder] -> [Host Machine] -> [Destination Folders].
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=theme.CARD_BG, corner_radius=8, border_width=1, border_color=theme.CARD_BORDER, **kwargs)

        self.source_path = ""
        self.destinations = []

        self._init_host_info()
        self._build_ui()
        self.bind("<Configure>", lambda e: self.after(10, self.draw_flow))

    def _init_host_info(self):
        """Retrieve host machine hardware/OS specs dynamically."""
        self.host_name = platform.node() or "Local Workstation"
        self.sys_info = f"{platform.system()} {platform.release()}"
        self.cpu_cores = os.cpu_count() or 4
        
        # Try retrieving RAM size if available
        self.ram_gb = "16"
        try:
            import psutil
            ram_bytes = psutil.virtual_memory().total
            self.ram_gb = f"{round(ram_bytes / (1024**3))}"
        except Exception:
            pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header bar for Job Flow panel
        header = ctk.CTkFrame(self, fg_color="transparent", height=32)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 0))
        header.grid_columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(
            header,
            text="Job Flow",
            font=(theme.FONT_FAMILY, 14, "bold"),
            text_color=theme.TEXT_MAIN
        )
        lbl_title.grid(row=0, column=0, sticky="w")

        # Main Canvas for drawing connection lines and cards
        self.canvas = tk.Canvas(
            self,
            bg=theme.CARD_BG,
            highlightthickness=0,
            bd=0
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def set_data(self, source_path: str, destinations: list[str]):
        """Update source and destination paths and redraw the diagram."""
        self.source_path = source_path
        self.destinations = destinations
        self.draw_flow()

    def draw_flow(self):
        """Redraw nodes and curved connecting lines."""
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w <= 10 or h <= 10:
            return

        cy = h / 2

        # -------------------------------------------------------------
        # 1. Draw Center Node: Host Workstation (Enlarged)
        # -------------------------------------------------------------
        center_x = w / 2
        card_w, card_h = 220, 135
        left_c = center_x - card_w / 2
        top_c = cy - card_h / 2
        right_c = center_x + card_w / 2
        bot_c = cy + card_h / 2

        # Draw card background
        self._draw_rounded_rect(
            left_c, top_c, right_c, bot_c, radius=10,
            fill=theme.PANEL_BG, outline=theme.CARD_BORDER, width=2
        )

        # Host Icon (Computer representation)
        self.canvas.create_text(
            center_x, top_c + 20,
            text="💻",
            font=(theme.FONT_FAMILY, 20),
            fill=theme.TEXT_MAIN
        )

        # Host Title & Details
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
        # 2. Draw Left Node: Source Folder / Drive (Enlarged)
        # -------------------------------------------------------------
        src_w, src_h = 200, 60
        src_x = max(120, w * 0.18)
        src_y = cy

        src_left = src_x - src_w / 2
        src_top = src_y - src_h / 2
        src_right = src_x + src_w / 2
        src_bot = src_y + src_h / 2

        self._draw_rounded_rect(
            src_left, src_top, src_right, src_bot, radius=8,
            fill=theme.PANEL_BG, outline=theme.ACCENT_PRIMARY if self.source_path else theme.CARD_BORDER, width=2
        )

        src_name = os.path.basename(self.source_path.rstrip("/\\")) if self.source_path else "Chưa chọn Nguồn"
        if len(src_name) > 24:
            src_name = src_name[:22] + ".."

        self.canvas.create_text(
            src_left + 28, src_y,
            text="📁", font=(theme.FONT_FAMILY, 18), fill=theme.TEXT_MAIN
        )
        self.canvas.create_text(
            src_left + 55, src_y - 10,
            text=src_name, font=(theme.FONT_FAMILY, 11, "bold"), fill=theme.TEXT_MAIN, anchor="w"
        )
        self.canvas.create_text(
            src_left + 55, src_y + 10,
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
        # 3. Draw Right Nodes: Destination Folders (Enlarged)
        # -------------------------------------------------------------
        dests = self.destinations if self.destinations else [""]
        num_dests = len(dests)
        
        # Calculate Y spacing for destinations
        spacing = min(80, max(55, (h - 60) / max(1, num_dests)))
        start_y = cy - ((num_dests - 1) * spacing) / 2

        dest_x = min(w - 120, w * 0.82)
        dest_w, dest_h = 200, 60

        for i, dest_path in enumerate(dests):
            dy = start_y + i * spacing
            d_left = dest_x - dest_w / 2
            d_top = dy - dest_h / 2
            d_right = dest_x + dest_w / 2
            d_bot = dy + dest_h / 2

            self._draw_rounded_rect(
                d_left, d_top, d_right, d_bot, radius=8,
                fill=theme.PANEL_BG, outline=theme.ACCENT_REPLICATION if dest_path else theme.CARD_BORDER, width=2
            )

            d_name = os.path.basename(dest_path.rstrip("/\\")) if dest_path else f"Chưa chọn Đích #{i+1}"
            if len(d_name) > 24:
                d_name = d_name[:22] + ".."

            self.canvas.create_text(
                d_left + 28, dy,
                text="💽", font=(theme.FONT_FAMILY, 18), fill=theme.TEXT_MAIN
            )
            self.canvas.create_text(
                d_left + 55, dy - 10,
                text=d_name, font=(theme.FONT_FAMILY, 11, "bold"), fill=theme.TEXT_MAIN, anchor="w"
            )
            self.canvas.create_text(
                d_left + 55, dy + 10,
                text=f"[ Đích #{i+1} ]", font=(theme.FONT_FAMILY, 9), fill=theme.TEXT_MUTED, anchor="w"
            )

            # Connection curve from Host to Destination
            self._draw_bezier(
                right_c, cy,
                d_left, dy,
                color=theme.ACCENT_REPLICATION if dest_path else theme.CARD_BORDER,
                width=2
            )

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
