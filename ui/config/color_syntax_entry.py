import re
import tkinter as tk
import customtkinter as ctk
import ui.theme as theme
from core.logger_config import logger

class ColorSyntaxEntry(ctk.CTkFrame):
    """
    Single-line Input Widget with real-time Syntax Highlighting for Tokens
    matching the visual token color palette.
    """
    TOKEN_COLOR_MAP = {
        "Camera": "#42A5F5",
        "Roll": "#AB47BC",
        "Clip": "#FFA726",
        "UID": "#EC407A",
        "Date": "#66BB6A",
        "Project": "#26C6DA",
        "Destination": "#7986CB"
    }

    def __init__(self, master, height=34, locked_prefix: str = None, **kwargs):
        super().__init__(
            master,
            fg_color=theme.CARD_BG,
            border_color=theme.CARD_BORDER,
            border_width=1,
            corner_radius=6,
            height=height,
            **kwargs
        )

        self.locked_prefix = locked_prefix
        self.grid_propagate(False)
        self.pack_propagate(False)

        self.text_widget = tk.Text(
            self,
            height=1,
            wrap="none",
            bg=theme.CARD_BG,
            fg="#FFFFFF",
            insertbackground=theme.TEXT_MAIN,
            selectbackground=theme.ACCENT_PRIMARY,
            selectforeground="#FFFFFF",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            font=(theme.FONT_FAMILY, 11, "bold")
        )
        self.text_widget.pack(fill="both", expand=True, padx=8, pady=6)

        self._init_tags()

        self.text_widget.bind("<KeyPress>", self._on_key_press)
        self.text_widget.bind("<KeyRelease>", self._on_key_release)
        self.text_widget.bind("<Return>", lambda e: "break")
        self.text_widget.bind("<Tab>", lambda e: "break")

        self.change_callbacks = []

    def _init_tags(self):
        for t_name, color in self.TOKEN_COLOR_MAP.items():
            self.text_widget.tag_config(f"tok_{t_name}", foreground=color, font=(theme.FONT_FAMILY, 11, "bold"))
        self.text_widget.tag_config("tok_static", foreground="#90A4AE", font=(theme.FONT_FAMILY, 11))
        self.text_widget.tag_config("tok_unknown", foreground="#FFB74D", font=(theme.FONT_FAMILY, 11, "bold"))

    def _on_key_press(self, event):
        if not self.locked_prefix:
            return

        prefix_len = len(self.locked_prefix)

        if event.keysym in ("BackSpace", "Delete"):
            try:
                sel_start = self.text_widget.index(tk.SEL_FIRST)
                sel_start_col = int(sel_start.split(".")[1])
                if sel_start_col < prefix_len:
                    return "break"
            except tk.TclError:
                pass

            try:
                cursor_col = int(self.text_widget.index(tk.INSERT).split(".")[1])
                if event.keysym == "BackSpace" and cursor_col <= prefix_len:
                    return "break"
                if event.keysym == "Delete" and cursor_col < prefix_len:
                    return "break"
            except Exception as e:
                logger.debug(f"Cursor prefix check exception: {e}")
                pass

    def _enforce_locked_prefix(self):
        if not self.locked_prefix:
            return

        content = self.text_widget.get("1.0", "end-1c").replace("\n", "").replace("\r", "")
        if not content.startswith(self.locked_prefix):
            clean_rest = content.replace(self.locked_prefix, "")
            if clean_rest and not clean_rest.startswith("/"):
                clean_rest = "/" + clean_rest
            new_content = self.locked_prefix + clean_rest

            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", new_content)

            prefix_len = len(self.locked_prefix)
            try:
                self.text_widget.mark_set(tk.INSERT, f"1.0 + {prefix_len} chars")
            except Exception as e:
                logger.debug(f"Mark set exception: {e}")
                pass
        else:
            # Strip any duplicate locked_prefix in the rest of string
            rest = content[len(self.locked_prefix):]
            if self.locked_prefix in rest:
                cleaned_rest = rest.replace(self.locked_prefix, "")
                new_content = self.locked_prefix + cleaned_rest
                self.text_widget.delete("1.0", tk.END)
                self.text_widget.insert("1.0", new_content)

    def highlight_syntax(self):
        content = self.get()
        for t_name in self.TOKEN_COLOR_MAP:
            self.text_widget.tag_remove(f"tok_{t_name}", "1.0", tk.END)
        self.text_widget.tag_remove("tok_static", "1.0", tk.END)
        self.text_widget.tag_remove("tok_unknown", "1.0", tk.END)

        if not content:
            return

        token_regex = re.compile(r'\{([A-Za-z0-9_]+)(?::([A-Za-z0-9_\-]+))?\}')
        last_pos = 0

        for match in token_regex.finditer(content):
            start, end = match.span()
            if start > last_pos:
                s_idx = f"1.0 + {last_pos} chars"
                e_idx = f"1.0 + {start} chars"
                self.text_widget.tag_add("tok_static", s_idx, e_idx)

            token_name = match.group(1)
            t_s_idx = f"1.0 + {start} chars"
            t_e_idx = f"1.0 + {end} chars"

            tag_key = f"tok_{token_name}" if token_name in self.TOKEN_COLOR_MAP else "tok_unknown"
            self.text_widget.tag_add(tag_key, t_s_idx, t_e_idx)
            last_pos = end

        if last_pos < len(content):
            s_idx = f"1.0 + {last_pos} chars"
            e_idx = f"1.0 + {len(content)} chars"
            self.text_widget.tag_add("tok_static", s_idx, e_idx)

    def _on_key_release(self, event):
        self._enforce_locked_prefix()
        self.highlight_syntax()
        for cb in self.change_callbacks:
            cb()

    def get(self) -> str:
        self._enforce_locked_prefix()
        return self.text_widget.get("1.0", "end-1c").replace("\n", "").replace("\r", "")

    def _convert_index(self, index):
        if index is None:
            return None
        if index == "end" or index == tk.END:
            return tk.END
        try:
            val = int(index)
            return f"1.{val}"
        except (ValueError, TypeError):
            return index

    def insert(self, index, text: str):
        if index == 0 or index == "0":
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", text)
        else:
            converted = self._convert_index(index)
            self.text_widget.insert(converted, text)
        self._enforce_locked_prefix()
        self.highlight_syntax()

    def delete(self, start, end=None):
        start_conv = self._convert_index(start)
        end_conv = self._convert_index(end) if end is not None else None
        
        if end_conv is None:
            self.text_widget.delete(start_conv)
        else:
            self.text_widget.delete(start_conv, end_conv)
        self._enforce_locked_prefix()
        self.highlight_syntax()

    def bind_change(self, callback):
        self.change_callbacks.append(callback)
