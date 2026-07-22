#!/usr/bin/env python3
"""
DIT Copy Pro — CLI / Terminal Mode
Dành cho môi trường Linux Terminal/SSH hoặc hệ thống chưa cài python3-tk.
"""

import sys
import os
import time
from typing import List

# Ensure project root is in python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.token_parser import TokenParser
from core.directory_builder import DirectoryBuilder
from core.copy_engine import CopyEngine
from core.preset_manager import PresetManager
from core.report_generator import ReportGenerator
from core.metadata_reader import MetadataReader
from core.sound_player import SoundPlayer


def print_banner():
    print("=" * 80)
    print("🎬 DIT COPY PRO — phần mềm sao chép & xác thực điện ảnh (CLI Mode)")
    print("=" * 80)


def format_size(bytes_num: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:3.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"


import argparse


def parse_args():
    cli_parser = argparse.ArgumentParser(
        description="DIT Copy Pro — Phần mềm sao chép & xác thực điện ảnh (CLI Mode)"
    )
    cli_parser.add_argument("-s", "--source", help="Thư mục Thẻ Nguồn (Source)")
    cli_parser.add_argument("-d", "--destinations", nargs="+", help="Danh sách các Thư mục Đích (Destinations)")
    cli_parser.add_argument("-p", "--preset", help="Tên Preset muốn áp dụng")
    cli_parser.add_argument("-a", "--hash-algorithm", choices=["MD5", "XXHash64", "SHA-256", "Size-only"], help="Thuật toán Checksum")
    cli_parser.add_argument("-b", "--buffer-size", type=int, help="Kích thước Buffer Cache (MB)")
    cli_parser.add_argument("positional_args", nargs="*", help="[Source] [Dest1] [Dest2]...")
    return cli_parser.parse_args()


def main():
    print_banner()

    args = parse_args()
    pm = PresetManager()
    presets = pm.list_presets()

    print("\n[Danh Sách Presets Khả Dụng]:")
    for idx, p in enumerate(presets, 1):
        print(f"  {idx}. {p}")

    preset_name = args.preset or (presets[0] if presets else "ARRI ALEXA Standard")
    preset_data = pm.load_preset(preset_name) or {
        "naming_rule": "{Camera:1}{Roll:3}C{Clip:3}_{Date:8}",
        "folder_template": "{Destination}/Footage/{Camera}/Roll_{Roll}/",
        "hash_algorithm": "MD5",
        "buffer_size_mb": 64
    }

    if args.hash_algorithm:
        preset_data["hash_algorithm"] = args.hash_algorithm
    if args.buffer_size:
        preset_data["buffer_size_mb"] = args.buffer_size

    print(f"\nPreset Được Chọn: [{preset_name}]")
    print(f"  - Naming Rule    : {preset_data.get('naming_rule')}")
    print(f"  - Folder Template: {preset_data.get('folder_template')}")
    print(f"  - Hash Algorithm : {preset_data.get('hash_algorithm')}")

    source_dir = args.source
    destinations = args.destinations or []

    if not source_dir and len(args.positional_args) >= 1:
        source_dir = args.positional_args[0]
    if not destinations and len(args.positional_args) >= 2:
        destinations = args.positional_args[1:]

    if not source_dir or not destinations:
        if not source_dir:
            print("\n--- NHẬP THÔNG TIN TÁC VỤ ---")
            source_dir = input("Nhập thư mục Thẻ Nguồn (Source): ").strip()
        if not destinations:
            dests_input = input("Nhập danh sách Thư mục Đích (cách nhau bởi dấu phẩy): ").strip()
            destinations = [d.strip() for d in dests_input.split(",") if d.strip()]

    if not source_dir or not os.path.exists(source_dir):
        print(f"❌ Lỗi: Thư mục nguồn '{source_dir}' không tồn tại!")
        return

    if not destinations:
        print("❌ Lỗi: Bạn phải chỉ định ít nhất 1 thư mục đích!")
        return

    sound_player = SoundPlayer()

    parser = TokenParser(preset_data["naming_rule"], date_format=preset_data.get("date_format", "YYMMDD"))
    builder = DirectoryBuilder(preset_data["folder_template"])

    engine = CopyEngine(
        source_dir=source_dir,
        destinations=destinations,
        token_parser=parser,
        directory_builder=builder,
        hash_algorithm=preset_data.get("hash_algorithm", "MD5"),
        buffer_size_mb=preset_data.get("buffer_size_mb", 64)
    )

    print("\n🔍 Đang quét danh sách file trên thẻ nguồn...")
    files = engine.scan_source()
    print(f"✓ Tìm thấy {len(files)} file ({format_size(engine.total_bytes)})")

    if not files:
        print("Không có file nào để sao chép.")
        return

    print("\n▶ BẮT ĐẦU QUÁ TRÌNH SAO CHÉP & XÁC THỰC MULTI-DESTINATION...\n")

    def on_file_start(file_info):
        print(f"\n[▶ COPYING] {file_info['filename']} ({format_size(file_info['size'])})")

    def on_file_progress(file_info, read_bytes, speed, eta):
        frac = read_bytes / max(1, file_info['size'])
        percent = int(frac * 100)
        speed_mb = speed / (1024 * 1024)
        print(f"\r Progress: [{ '#' * (percent // 5):<20} ] {percent}% | {speed_mb:.1f} MB/s", end="", flush=True)

    def on_file_complete(file_info):
        print()
        if file_info['status'] == "VERIFIED":
            print(f"  └─ [✓ VERIFIED] Hash: {file_info['source_hash'][:16]}... Trùng khớp 100%")
        else:
            print(f"  └─ [✗ FAILED] {file_info.get('error_msg', 'Checksum mismatch!')}")

    summary = engine.run_copy_session(
        on_file_start=on_file_start,
        on_file_progress=on_file_progress,
        on_file_complete=on_file_complete,
        metadata_reader_func=MetadataReader.get_shot_time
    )

    src_name = os.path.basename(source_dir.rstrip("/\\")) or source_dir
    report_path = os.path.join(destinations[0], f"DIT_Report_{src_name}.txt")
    ReportGenerator.generate_txt_report(
        project_name="Film Project",
        preset_name=preset_name,
        source_dir=source_dir,
        destinations=destinations,
        hash_algorithm=preset_data.get("hash_algorithm", "MD5"),
        file_list=engine.file_list,
        summary=summary,
        output_filepath=report_path
    )

    print("\n" + "=" * 80)
    print("📊 TỔNG KẾT TÁC VỤ SAO CHÉP")
    print("=" * 80)
    print(f"  • Tổng số file : {summary['total_files']}")
    print(f"  • Verified     : {summary['verified']} ✓")
    print(f"  • Failed       : {summary['failed']} ✗")
    print(f"  • Dung lượng   : {format_size(summary['total_bytes'])}")
    print(f"  • Báo cáo TXT  : {report_path}")

    if summary["failed"] > 0:
        sound_player.play_error()
        print("\n⚠️ CẢNH BÁO: Phát hiện lỗi checksum! Vui lòng kiểm tra báo cáo và KHÔNG format thẻ nhớ.")
    else:
        sound_player.play_success()
        print("\n🎉 HOÀN THÀNH XÁC THỰC DỮ LIỆU THÀNH CÔNG 100%!")


if __name__ == "__main__":
    main()
