#!/usr/bin/env python3
"""
DIT Copy Pro — Automated Portable App Builder (Windows & Linux)
Packages DIT Copy Pro into a single-file portable executable and creates
the standalone Portable Folder distribution containing the binary, finish.mp3, and presets/.
"""

import sys
import os
import shutil
import subprocess


def main():
    print("=" * 80)
    print("📦 DIT COPY PRO — AUTOMATED PORTABLE APP BUILDER")
    print("=" * 80)

    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Detect Platform & Executable Extension
    is_win = sys.platform.startswith("win")
    exe_name = "DIT_Copy_Pro.exe" if is_win else "DIT_Copy_Pro"
    separator = ";" if is_win else ":"

    print(f"📌 Platform: {'Windows' if is_win else 'Linux / Unix'}")
    print(f"📌 Project Root: {project_root}")

    # Check PyInstaller availability
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n❌ PyInstaller chưa được cài đặt!")
        print("👉 Vui lòng cài đặt PyInstaller bằng lệnh:")
        print("   $ pip install pyinstaller")
        return

    # PyInstaller Build Command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "DIT_Copy_Pro",
        "--clean",
        f"--add-data=finish.mp3{separator}.",
        f"--add-data=presets{separator}presets",
        "main.py"
    ]
    if is_win:
        cmd.insert(4, "--noconsole")

    print("\n🔨 Đang tiến hành biên dịch ứng dụng với PyInstaller...")
    print(f"   Lệnh: {' '.join(cmd)}")
    
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("\n❌ Lỗi trong quá trình biên dịch PyInstaller!")
        return

    # Create Standalone Portable Folder
    dist_dir = os.path.join(project_root, "dist")
    built_exe = os.path.join(dist_dir, exe_name)

    if not os.path.exists(built_exe):
        print(f"\n❌ Không tìm thấy file thực thi sau khi build: {built_exe}")
        return

    portable_folder = os.path.join(project_root, "DIT_Copy_Pro_Portable")
    if os.path.exists(portable_folder):
        shutil.rmtree(portable_folder)
    os.makedirs(portable_folder, exist_ok=True)

    # Copy Executable to Portable Folder
    dest_exe = os.path.join(portable_folder, exe_name)
    shutil.copy2(built_exe, dest_exe)

    # Copy finish.mp3 to Portable Folder
    src_mp3 = os.path.join(project_root, "finish.mp3")
    if os.path.exists(src_mp3):
        shutil.copy2(src_mp3, os.path.join(portable_folder, "finish.mp3"))

    # Copy presets/ directory to Portable Folder
    src_presets = os.path.join(project_root, "presets")
    if os.path.exists(src_presets):
        shutil.copytree(src_presets, os.path.join(portable_folder, "presets"), dirs_exist_ok=True)

    print("\n" + "=" * 80)
    print("🎉 TẠO THƯ MỤC PORTABLE THÀNH CÔNG!")
    print("=" * 80)
    print(f"📁 Đường dẫn Portable Folder: {portable_folder}")
    print("📂 Cấu trúc danh mục Portable đã hoàn thiện:")
    print(f"   ├── 📄 {exe_name}")
    print("   ├── 🎵 finish.mp3")
    print("   └── 📁 presets/")

    # Make binary executable on Linux
    if not is_win:
        try:
            os.chmod(dest_exe, 0o755)
        except Exception:
            pass


if __name__ == "__main__":
    main()
