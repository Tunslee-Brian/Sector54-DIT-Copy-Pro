import sys
import os

# Ensure project root is in python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # Monkey-patch CustomTkinter string widget scrolling crash (common on Python 3.14/Tkinter)
    try:
        import customtkinter as ctk
        orig_check_scroll = ctk.CTkScrollableFrame._check_if_valid_scroll
        def patched_check_scroll(self, widget):
            if isinstance(widget, str):
                try:
                    widget = self.nametowidget(widget)
                except Exception:
                    return False
            return orig_check_scroll(self, widget)
        ctk.CTkScrollableFrame._check_if_valid_scroll = patched_check_scroll
    except Exception:
        pass

    try:
        from ui.app import DITCopyProApp
        app = DITCopyProApp()
        app.mainloop()
    except (ImportError, Exception) as e:
        print("=" * 80)
        print("❌ LỖI: Không thể khởi chạy giao diện GUI (Tkinter/CustomTkinter).")
        print(f"   Chi tiết lỗi: {e}")
        print("=" * 80)
        print("👉 Hướng dẫn khắc phục cho CachyOS / Arch Linux:")
        print("   Hãy cài đặt gói 'tk' bằng lệnh:")
        print("   $ sudo pacman -S tk")
        print("=" * 80)
        sys.exit(1)

if __name__ == "__main__":
    main()
