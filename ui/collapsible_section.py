import customtkinter as ctk
import ui.theme as theme


class CollapsibleSection(ctk.CTkFrame):
    """
    Ultra-compact VS Code style collapsible accordion section header.
    Features 26px slim header with '▾' / '▸' toggle arrows and tight content margins.
    """

    def __init__(self, master, title: str, is_open: bool = True, on_toggle_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, border_width=0, **kwargs)

        self.title_text = title
        self.is_open = is_open
        self.on_toggle_callback = on_toggle_callback

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # Slim Header Bar (VS Code Explorer Section Header style)
        self.header_frame = ctk.CTkFrame(self, fg_color=theme.PANEL_BG, corner_radius=4, height=26)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(2, 2))
        self.header_frame.grid_columnconfigure(0, weight=1)

        arrow = "▾" if self.is_open else "▸"
        self.btn_toggle = ctk.CTkButton(
            self.header_frame,
            text=f"{arrow}  {self.title_text.upper()}",
            font=(theme.FONT_FAMILY, 11, "bold"),
            fg_color="transparent",
            hover_color=theme.CARD_BG,
            text_color=theme.TEXT_MAIN,
            anchor="w",
            height=26,
            command=self.toggle
        )
        self.btn_toggle.grid(row=0, column=0, sticky="ew", padx=4, pady=0)

        # Content Frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        if self.is_open:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=(2, 4))
            self.content_frame.grid_columnconfigure(0, weight=1)
            self.content_frame.grid_rowconfigure(0, weight=1)

    def toggle(self):
        self.is_open = not self.is_open
        arrow = "▾" if self.is_open else "▸"
        self.btn_toggle.configure(text=f"{arrow}  {self.title_text.upper()}")

        if self.is_open:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=(2, 4))
            self.content_frame.grid_columnconfigure(0, weight=1)
            self.content_frame.grid_rowconfigure(0, weight=1)
        else:
            self.content_frame.grid_forget()

        if self.on_toggle_callback:
            self.on_toggle_callback()
