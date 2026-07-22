import customtkinter as ctk
import ui.theme as theme

class ChecksumAlertDialog(ctk.CTkToplevel):
    """
    Big Alert Dialog popped up when checksum mismatch, missing files, or extra files are detected.
    Prevents accidental formatting of corrupted camera card and warns about orphan extra files.
    """

    def __init__(self, parent, failed_file_info: dict = None, extra_files: list = None, failed_files: list = None):
        super().__init__(parent)
        self.failed_file_info = failed_file_info or {}
        self.failed_files = failed_files or ([failed_file_info] if failed_file_info else [])
        self.extra_files = extra_files or []

        has_failed = len(self.failed_files) > 0
        has_extra = len(self.extra_files) > 0

        if has_failed and has_extra:
            title_text = "⚠️ CẢNH BÁO: PHÁT HIỆN LỖI XÁC THỰC VÀ FILE THỪA!"
            bg_color = "#1f0a0a"
            header_color = theme.ACCENT_DANGER
        elif has_failed:
            title_text = "⚠️ CẢNH BÁO NGUY HẠI: PHÁT HIỆN LỖI CORRUPT DỮ LIỆU!"
            bg_color = "#1f0a0a"
            header_color = theme.ACCENT_DANGER
        else:
            title_text = "⚠️ CẢNH BÁO: PHÁT HIỆN FILE THỪA Ở THƯ MỤC ĐÍCH!"
            bg_color = "#1a160a"
            header_color = theme.ACCENT_WARNING

        self.title(title_text)
        self.header_color = header_color
        self.geometry("720x520")
        self.resizable(False, False)
        self.configure(fg_color=bg_color)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        has_failed = len(self.failed_files) > 0
        has_extra = len(self.extra_files) > 0

        # Header banner
        header = ctk.CTkFrame(self, fg_color=self.header_color, corner_radius=0, height=70)
        header.pack(fill="x")

        hdr_text = "⚠️ CẢNH BÁO TÍNH TOÀN VẸN DỮ LIỆU DIT"
        if has_failed and has_extra:
            hdr_text = "⚠️ CẢNH BÁO: PHÁT HIỆN LỖI SAI LỆCH VÀ FILE THỪA!"
        elif has_failed:
            hdr_text = "⚠️ CẢNH BÁO LỖI XÁC THỰC CHECKSUM (CORRUPTED / MISSING)"
        elif has_extra:
            hdr_text = "⚠️ CẢNH BÁO PHÁT HIỆN FILE THỪA (EXTRA / ORPHAN FILES)"

        lbl_header = ctk.CTkLabel(
            header,
            text=hdr_text,
            font=(theme.FONT_FAMILY, 15, "bold"),
            text_color="#ffffff"
        )
        lbl_header.pack(pady=20)

        # Body Frame
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=25, pady=20)

        if has_failed:
            msg = (
                "Hệ thống phát hiện sai lệch checksum hoặc thiếu file giữa thẻ nguồn và ổ đích!\n"
                "File có thể đã bị lỗi truyền tải, ngắt kết nối đột ngột hoặc hỏng sector."
            )
        else:
            msg = (
                "Hệ thống phát hiện các file thừa xuất hiện trong thư mục Đích mà KHÔNG có trên thẻ Nguồn!\n"
                "Vui lòng kiểm tra lại để tránh nhầm lẫn dữ liệu rác từ các phiên chép cũ."
            )

        lbl_msg = ctk.CTkLabel(
            body,
            text=msg,
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.TEXT_MAIN,
            justify="left"
        )
        lbl_msg.pack(anchor="w", pady=(0, 10))

        # Details box
        details_box = ctk.CTkTextbox(
            body,
            fg_color="#120505" if has_failed else "#141208",
            text_color="#ff8888" if has_failed else "#ffcc66",
            font=("Courier", 11),
            height=220
        )
        details_box.pack(fill="x", pady=5)

        info_lines = []

        if has_failed:
            info_lines.append("❌ DANH SÁCH FILE LỖI / THIẾU (FAILED / MISSING FILES):")
            for ff in self.failed_files:
                fname = ff.get("filename", "N/A")
                src_h = ff.get("source_hash", "N/A")
                dst_hashes = ff.get("dest_hashes", {})
                info_lines.append(f"  • File: {fname}")
                info_lines.append(f"    Shot Time: {ff.get('shot_time', 'N/A')}")
                info_lines.append(f"    Source Hash: {src_h}")
                for dst, dh in dst_hashes.items():
                    info_lines.append(f"    - Dest ({dst}): {dh}")
                info_lines.append("")

        if has_extra:
            info_lines.append("⚠️ DANH SÁCH FILE THỪA Ổ ĐÍCH (EXTRA / ORPHAN FILES):")
            for ef in self.extra_files:
                ef_name = ef.get("filename", "")
                ef_path = ef.get("dest_path", "")
                ef_mb = ef.get("size", 0) / (1024 * 1024)
                info_lines.append(f"  • Extra File: {ef_name} ({ef_mb:.2f} MB)")
                info_lines.append(f"    Đường dẫn: {ef_path}")
                info_lines.append("")

        info_lines.append("=" * 60)
        info_lines.append("KHUYẾN NGHỊ DIT:")
        if has_failed:
            info_lines.append("1. TUYỆT ĐỐI KHÔNG FORMAT THẺ NHỚ NÀY!")
            info_lines.append("2. Vệ sinh cổng đọc thẻ, kiểm tra cáp kết nối.")
            info_lines.append("3. Sao chép lại thủ công file lỗi này trước khi rút thẻ.")
        if has_extra:
            info_lines.append("• Kiểm tra và dọn dẹp các file thừa không thuộc dự án hiện tại.")

        details_box.insert("1.0", "\n".join(info_lines))
        details_box.configure(state="disabled")

        # Action Button
        btn_text = "[ ĐÃ HIỂU - TÔI SẼ KHÔNG FORMAT THẺ NHỚ ]" if has_failed else "[ ĐÃ HIỂU - TÔI SẼ KIỂM TRA LẠI THƯ MỤC ĐÍCH ]"
        btn_bg = theme.ACCENT_DANGER if has_failed else theme.ACCENT_WARNING
        btn_hover = theme.ACCENT_DANGER_HOVER if has_failed else theme.ACCENT_WARNING_HOVER

        btn_acknowledge = ctk.CTkButton(
            body,
            text=btn_text,
            font=(theme.FONT_FAMILY, 13, "bold"),
            fg_color=btn_bg,
            hover_color=btn_hover,
            height=44,
            command=self.destroy
        )
        btn_acknowledge.pack(fill="x", pady=(12, 0))
