import sys
import os

# Ensure project root is in python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def main():
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
