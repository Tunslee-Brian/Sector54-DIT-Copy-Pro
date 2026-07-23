import os
import html
from datetime import datetime
from typing import List, Dict

class ReportGenerator:
    """
    Generates official DIT Copy Reports matching Section 5 in report.md.
    """

    @staticmethod
    def format_size(bytes_num: int) -> str:
        size = float(bytes_num)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size) < 1024.0:
                return f"{size:3.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @staticmethod
    def format_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @classmethod
    def generate_txt_report(
        cls,
        project_name: str,
        preset_name: str,
        source_dir: str,
        destinations: List[str],
        hash_algorithm: str,
        file_list: List[Dict],
        summary: Dict,
        output_filepath: str
    ) -> str:
        """
        Creates TXT report file and returns report text content.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = []
        lines.append("===========================================================================")
        lines.append("                                DIT COPY REPORT                            ")
        lines.append("===========================================================================")
        lines.append("")
        lines.append(f"Project Name: {project_name}")
        lines.append(f"Preset Used : {preset_name}")
        lines.append(f"Date/Time   : {now_str}")
        lines.append("")
        lines.append(f"Source Card : {os.path.basename(source_dir)} (Path: {source_dir})")

        for idx, dest in enumerate(destinations, 1):
            lines.append(f"Destination {idx}: {os.path.basename(dest)} (Path: {dest})")

        lines.append(f"Verification: {hash_algorithm}")
        lines.append("")
        lines.append("-" * 120)
        lines.append(f"{'Filename':<22} {'Size':<12} {'Shot Date/Time':<20} {'Source Hash':<34} {'Status':<12}")
        lines.append("-" * 120)
        lines.append("")

        failed_files = []

        for f in file_list:
            fname = f.get("filename", "")
            size_str = cls.format_size(f.get("size", 0))
            shot_time = f.get("shot_time", "N/A")
            src_hash = f.get("source_hash", "N/A")
            status = f.get("status", "QUEUED")

            status_icon = "VERIFIED ✓" if status == "VERIFIED" else "FAILED ✗" if status == "FAILED" else status

            lines.append(f"{fname:<22} {size_str:<12} {shot_time:<20} {src_hash:<34} {status_icon:<12}")

            if status == "FAILED":
                failed_files.append(f)

        lines.append("")
        lines.append("-" * 120)
        lines.append("Summary")
        lines.append("-" * 120)
        lines.append("")
        extra_files = summary.get("extra_files", [])
        lines.append(f"Total Files       : {summary.get('total_files', len(file_list))}")
        lines.append(f"Verified          : {summary.get('verified', 0)}")
        lines.append(f"Failed            : {summary.get('failed', 0)}")
        lines.append(f"Extra Files       : {len(extra_files)}")
        lines.append(f"Total Size        : {cls.format_size(summary.get('total_bytes', 0))}")

        elapsed_str = cls.format_time(summary.get('elapsed_seconds', 0))
        speed_str = cls.format_size(int(summary.get('avg_speed_bytes_sec', 0)))
        lines.append(f"Time Elapsed      : {elapsed_str} (Average Speed: ~{speed_str}/s)")
        lines.append("")

        if extra_files:
            lines.append("-" * 120)
            lines.append("Extra / Orphan Files in Destination (File Thừa ở ổ Đích):")
            lines.append("-" * 120)
            lines.append(f"{'Filename':<30} {'Size':<12} {'Destination Path':<70}")
            lines.append("-" * 120)
            for ef in extra_files:
                ef_name = ef.get("filename", "")
                ef_size = cls.format_size(ef.get("size", 0))
                ef_path = ef.get("dest_path", "")
                lines.append(f"{ef_name:<30} {ef_size:<12} {ef_path:<70}")
            lines.append("")

        if failed_files:
            lines.append("WARNING:")
            lines.append("Checksum mismatch detected. One or more files are corrupted!")
            lines.append("")
            for ff in failed_files:
                lines.append(f"Failed File     : {ff.get('filename')}")
                lines.append(f"Shot Date/Time  : {ff.get('shot_time')}")
                lines.append(f"Source Hash     : {ff.get('source_hash')}")
                for dst_path, dst_h in ff.get("dest_hashes", {}).items():
                    lines.append(f"Dest Hash ({os.path.basename(dst_path)}): {dst_h}")
                lines.append("")
            lines.append("Result:")
            lines.append("The destination file does NOT match the source.")
            lines.append("File may be corrupted, truncated, or incomplete.")
            lines.append("")
            lines.append("Recommendation: ")
            lines.append("DO NOT format the camera card. Clean the ports, check the cable, and re-copy this file manually.")
        else:
            lines.append("SUCCESS:")
            lines.append("All files successfully verified and checksum matched.")
            if extra_files:
                lines.append("Notice: Extra files detected in destination directories. Please audit extra files.")
            else:
                lines.append("Camera card can be safely archived.")

        lines.append("===========================================================================")

        content = "\n".join(lines)
        if output_filepath:
            output_dir = os.path.dirname(os.path.abspath(output_filepath))
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return content


    @classmethod
    def generate_html_report(
        cls,
        project_name: str,
        preset_name: str,
        source_dir: str,
        destinations: List[str],
        hash_algorithm: str,
        file_list: List[Dict],
        summary: Dict,
        output_filepath: str
    ) -> str:
        """
        Creates a print-ready, responsive HTML DIT Copy Report and returns HTML string.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        extra_files = summary.get("extra_files", [])
        total_files = summary.get("total_files", len(file_list))
        verified_count = summary.get("verified", 0)
        failed_count = summary.get("failed", 0)
        total_size_str = cls.format_size(summary.get("total_bytes", 0))
        elapsed_str = cls.format_time(summary.get("elapsed_seconds", 0))
        speed_str = cls.format_size(int(summary.get("avg_speed_bytes_sec", 0)))

        eproj = html.escape(project_name)
        epres = html.escape(preset_name)
        esrc = html.escape(source_dir)
        ehash = html.escape(hash_algorithm)

        status_class = "status-pass" if failed_count == 0 else "status-fail"
        status_banner = "PASSED 100%" if failed_count == 0 else "FAILED / CHECKSUM MISMATCH"

        rows_html = []
        for f in file_list:
            fname = html.escape(f.get("filename", ""))
            fsize = cls.format_size(f.get("size", 0))
            stime = html.escape(f.get("shot_time", "N/A"))
            shash = html.escape(f.get("source_hash", "N/A"))
            status = f.get("status", "QUEUED")

            badge_cls = "badge-pass" if status == "VERIFIED" else "badge-fail" if status == "FAILED" else "badge-warn"
            badge_text = "VERIFIED ✓" if status == "VERIFIED" else "FAILED ✗" if status == "FAILED" else html.escape(status)

            rows_html.append(f"""
            <tr>
                <td><code>{fname}</code></td>
                <td>{fsize}</td>
                <td>{stime}</td>
                <td><code class="hash">{shash}</code></td>
                <td><span class="badge {badge_cls}">{badge_text}</span></td>
            </tr>
            """)

        extra_rows_html = []
        for ef in extra_files:
            ef_name = html.escape(ef.get("filename", ""))
            ef_size = cls.format_size(ef.get("size", 0))
            ef_path = html.escape(ef.get("dest_path", ""))
            extra_rows_html.append(f"""
            <tr>
                <td><code>{ef_name}</code></td>
                <td>{ef_size}</td>
                <td><code>{ef_path}</code></td>
            </tr>
            """)

        dest_list_html = "".join([f"<li><code>{html.escape(d)}</code></li>" for d in destinations])

        # Localization dictionary for the report labels (can be expanded for other languages)
        labels = {
            "title": "DIT COPY REPORT",
            "project": "Dự án",
            "preset": "Preset",
            "total_files": "Tổng số Tệp",
            "verified": "Đã Xác Thực",
            "checksum_errors": "Lỗi Checksum",
            "total_size": "Tổng Dung Lượng",
            "time_speed": "Thời Gian & Tốc Độ",
            "report_time": "Thời gian báo cáo",
            "checksum_algorithm": "Thuật toán Checksum",
            "source_dir": "Thẻ Nguồn (Source)",
            "dest_dirs": "Các Thư Mục Đích (Destinations)",
            "checked_files_list": "Danh Sách File Đã Kiểm Tra",
            "filename": "Tên Tập Tin",
            "size": "Kích Thước",
            "shot_time": "Thời Gian Shot",
            "source_hash": "Source Hash",
            "status": "Trạng Thái",
            "extra_files_title": "File Thừa ở Ổ Đích (Extra / Orphan Files)",
            "dest_path": "Đường Dẫn Đích"
        }

        html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DIT Copy Report — {eproj}</title>
    <style>
        :root {{
            --bg-dark: #0f111a;
            --panel-bg: #181b28;
            --card-bg: #212538;
            --text-main: #f0f2f5;
            --text-muted: #8c95a6;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --border-color: #2d3348;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 32px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            letter-spacing: 0.5px;
            color: #ffffff;
        }}
        .status-banner {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            letter-spacing: 1px;
        }}
        .status-pass {{ background-color: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }}
        .status-fail {{ background-color: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid var(--accent-red); }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .metric-card {{
            background: var(--card-bg);
            padding: 16px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        .metric-card .label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; }}
        .metric-card .value {{ font-size: 20px; font-weight: bold; color: var(--text-main); }}

        .info-section {{
            margin-bottom: 28px;
            font-size: 14px;
            line-height: 1.6;
        }}
        .info-section code {{
            background: var(--card-bg);
            padding: 2px 6px;
            border-radius: 4px;
            color: #60a5fa;
            font-family: monospace;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 13px;
        }}
        th, td {{
            text-align: left;
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background: var(--card-bg);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
        }}
        code.hash {{ font-family: monospace; font-size: 12px; color: #a7f3d0; }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
        .badge-pass {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}
        .badge-warn {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }}

        @media print {{
            body {{ background: #ffffff; color: #000000; padding: 0; }}
            .container {{ border: none; box-shadow: none; padding: 0; background: #ffffff; color: #000000; }}
            th {{ background: #f0f0f0; color: #000000; }}
            td {{ border-bottom: 1px solid #ddd; color: #000000; }}
            code {{ background: #f5f5f5; color: #000000; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🎬 {labels["title"]}</h1>
                <div style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">{labels["project"]}: <strong>{eproj}</strong> | {labels["preset"]}: <strong>{epres}</strong></div>
            </div>
            <div class="status-banner {status_class}">{status_banner}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="label">{labels["total_files"]}</div>
                <div class="value">{total_files}</div>
            </div>
            <div class="metric-card">
                <div class="label">{labels["verified"]}</div>
                <div class="value" style="color: var(--accent-green);">{verified_count}</div>
            </div>
            <div class="metric-card">
                <div class="label">{labels["checksum_errors"]}</div>
                <div class="value" style="color: var(--accent-red);">{failed_count}</div>
            </div>
            <div class="metric-card">
                <div class="label">{labels["total_size"]}</div>
                <div class="value">{total_size_str}</div>
            </div>
            <div class="metric-card">
                <div class="label">{labels["time_speed"]}</div>
                <div class="value" style="font-size: 16px;">{elapsed_str} (~{speed_str}/s)</div>
            </div>
        </div>

        <div class="info-section">
            <div><strong>{labels["report_time"]}:</strong> {now_str}</div>
            <div><strong>{labels["checksum_algorithm"]}:</strong> <code>{ehash}</code></div>
            <div><strong>{labels["source_dir"]}:</strong> <code>{esrc}</code></div>
            <div><strong>{labels["dest_dirs"]}:</strong></div>
            <ul style="margin: 4px 0 0 20px; padding: 0;">
                {dest_list_html}
            </ul>
        </div>

        <h2>📄 {labels["checked_files_list"]}</h2>
        <table>
            <thead>
                <tr>
                    <th>{labels["filename"]}</th>
                    <th>{labels["size"]}</th>
                    <th>{labels["shot_time"]}</th>
                    <th>{labels["source_hash"]}</th>
                    <th>{labels["status"]}</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows_html)}
            </tbody>
        </table>

        {f'''
        <h2 style="margin-top: 36px; color: var(--accent-yellow);">⚠️ {labels["extra_files_title"]}</h2>
        <table>
            <thead>
                <tr>
                    <th>{labels["filename"]}</th>
                    <th>{labels["size"]}</th>
                    <th>{labels["dest_path"]}</th>
                </tr>
            </thead>
            <tbody>
                {"".join(extra_rows_html)}
            </tbody>
        </table>
        ''' if extra_files else ''}
    </div>
</body>
</html>
"""
        if output_filepath:
            output_dir = os.path.dirname(os.path.abspath(output_filepath))
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

        return html_content

