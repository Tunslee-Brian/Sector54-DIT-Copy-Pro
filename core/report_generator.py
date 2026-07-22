import os
from datetime import datetime
from typing import List, Dict

class ReportGenerator:
    """
    Generates official DIT Copy Reports matching Section 5 in report.md.
    """

    @staticmethod
    def format_size(bytes_num: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_num) < 1024.0:
                return f"{bytes_num:3.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} PB"

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

        # Write to output file if path provided
        if output_filepath:
            output_dir = os.path.dirname(os.path.abspath(output_filepath))
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return content
