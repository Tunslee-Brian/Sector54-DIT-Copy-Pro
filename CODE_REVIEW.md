# DIT Copy Pro — Code Review Report

> **Date:** 2026-07-23
> **Scope:** Full codebase analysis (core/, ui/, tests/, main.py)

---

## 🔴 CRITICAL

### 1. `_get_subprocess_kwargs` chưa được import trong `media_preview_widget.py`

- **File:** `ui/media_preview_widget.py:447, 525, 818, 856`
- Hàm `_get_subprocess_kwargs()` được gọi ở 4 chỗ (trong `_init_audio_duration`, `_start_audio_ffplay`, `_load_video_metadata_and_poster`) nhưng không được import.
- Hàm này được định nghĩa trong `ui/preview/preview_helpers.py` và chỉ được import trong `ui/preview/video_decoder.py`.
- `ui/preview/__init__.py` không re-export hàm này.
- Hậu quả: `NameError: name '_get_subprocess_kwargs' is not defined` khi audio/video preview được kích hoạt.

### 2. Progress bar bị cap sai trong `run_verify_only_session`

- **File:** `core/copy_engine.py:348-357, 404-407`
- `total_work_bytes` được tính riêng cho verify-only mode:
  - Với Size-only: `total_work_bytes = self.total_bytes`
  - Với hash algorithms khác: `total_work_bytes = file_size + sum(file_size for each existing destination)` — có thể gấp N+1 lần `self.total_bytes`.
- Callback `on_file_progress` dùng `min(self.total_bytes, self.copied_bytes)` làm denominator (line 407), nhưng `copied_bytes` được increment cả trong `src_callback` và `dst_verify_callback` với tổng lên tới `total_work_bytes`.
- Hậu quả: progress không đạt 100% trong phase verify, ETA/speed sai lệch.

### 3. `folder_count` không được khởi tạo trong `CopyEngine.__init__`

- **File:** `core/copy_engine.py:38-83`
- `folder_count` chỉ được set trong `scan_source()` (line 202 cho `os.walk`, line 158 cho single file).
- `app.py:361` dùng `getattr(engine, "folder_count", 0)` để phòng hộ, nhưng nếu có code path nào access `engine.folder_count` trước khi `scan_source()` chạy, sẽ raise `AttributeError`.
- Không được khai báo trong `__init__` cùng với các attribute khác (`file_list`, `total_bytes`, `copied_bytes`, ...).

### 4. Thread race trên `self.proc` trong `InAppVideoDecoder`

- **File:** `ui/preview/video_decoder.py:59, 90-104`
- Decoder thread loop (line 59-82) gọi `self.proc.poll()` và `self.proc.stdout.read(frame_size)` trong khi main thread có thể gọi `stop()` (line 90-104) đặt `self.proc = None`.
- Race condition cụ thể: thread kiểm tra `self.proc.poll()` ở line 59, nhưng ngay sau đó `stop()` chạy và set `self.proc = None`, rồi thread tiếp tục vào line 65 và crash với `AttributeError: 'NoneType' object has no attribute 'stdout'`.
- Check `self.is_running` không đủ để ngăn race vì `stop()` set cả `self.is_running = False` và `self.proc = None` không atomic.

---

## 🟠 MODERATE

### 5. Speed/ETA tính sai do shared mutable state giữa copy và verify

- **File:** `core/copy_engine.py:536-538, 665-683`
- `bytes_since_last_calc` và `last_calc_time` là `nonlocal` variables được share giữa main copy loop và verify callback `dst_callback`.
- Trong `_copy_single_file`, verify chạy sau copy xong, nhưng `dst_callback` vẫn dùng chung `bytes_since_last_calc` với main loop. Khi verify chạy parallel qua `ThreadPoolExecutor`, nhiều luồng cùng ghi vào cùng một variable không có lock, gây dirty read/write.
- Kết quả: speed và ETA trên progress panel nhảy loạn trong phase verification.

### 6. `ColorSyntaxEntry.delete()` chỉ handle đúng `start=0`

- **File:** `ui/config/color_syntax_entry.py:176-184`
- `delete(self, start, end=None)` chỉ convert `start == 0 or start == "0"` thành `"1.0"`. Các giá trị `start` khác được truyền thẳng vào `self.text_widget.delete()`.
- Tkinter Text widget interpret index `1` là line 1, character 0 — tương đương xoá từ đầu dòng 1 (toàn bộ text), khác với behavior của Entry.delete(1).
- Hiện tại codebase chỉ gọi `delete(0, "end")` nên chưa gặp bug.

### 7. ReportGenerator hardcode project name "Film Project"

- **File:** `ui/app.py:568-569`
- Cả `generate_txt_report` và `generate_html_report` đều được gọi với `project_name="Film Project"`.
- Không có UI field để người dùng nhập/cấu hình project name.
- Tất cả report đều hiển thị "Film Project" bất kể dự án thực tế là gì.

### 8. Session save silently swallows all exceptions

- **File:** `core/copy_engine.py:762`
- `except Exception: pass` — mọi lỗi ghi session file (quyền, disk full, corrupt JSON) đều bị im lặng bỏ qua.
- Không có `logger.warning` hay `logger.error` call.
- Người dùng không biết session state có được lưu thành công hay không.

### 9. `_show_add_output_menu` không phải menu

- **File:** `ui/sidebar_panel.py:469-470`
- `_show_add_output_menu` mở thẳng `_browse_output_folder()`, không show menu.
- `_show_add_input_menu` lại show menu với 2 option (Folder / File).
- Bất nhất về UX và naming: tên hàm gợi ý menu nhưng behavior khác.

### 10. `check_free_space` có thể false negative

- **File:** `core/copy_engine.py:94-106`
- Destination path có thể là non-existent nested path (e.g., `/mnt/RAID/Footage/A/Roll_001` chưa tồn tại). Code traverse up để tìm existing parent.
- Nếu không tìm thấy parent nào tồn tại, fallback về `/`.
- Disk usage check sai nếu dest ở mount khác với `/`.
- Không phân biệt được lỗi "path không tồn tại" với "permission denied" — cả hai đều set `free = -1`.

---

## 🟡 MINOR / EDGE CASES

### 11. Empty directories không được cleanup sau khi copy fail

- **File:** `core/copy_engine.py:715-722`
- `_cleanup_partial_files` xoá partially written files nhưng không xoá thư mục cha rỗng do `ensure_directory_exists` tạo ra.
- Tích luỹ thư mục rỗng trong destination sau nhiều lần cancel/fail.

### 12. Unused imports

- **File:** `ui/source_panel.py:1` (`ctk`), `ui/destination_panel.py:1` (`ctk`), nhiều file khác
- Import `customtkinter as ctk` nhưng không dùng (chỉ dùng `filedialog` từ tkinter).
- Import `os`, `sys`, `time` trong nhiều file không dùng đến.

### 13. Drive polling không dừng khi window đóng

- **File:** `ui/sidebar_panel.py:579-593`
- `_start_drive_polling` dùng `self.after(5000, poll)` tạo infinite loop.
- Không có cơ chế stop polling khi widget bị destroy hoặc window đóng.
- Gây lãng phí tài nguyên và potential error sau khi destroy.

### 14. Video poster temp file leak

- **File:** `ui/media_preview_widget.py:848-861`
- `NamedTemporaryFile` tạo temp file, lưu path vào `tmp_thumb_path`, nhưng nếu `Image.open()` hoặc `img.copy()` throw exception, `os.remove(tmp_thumb_path)` không được gọi.
- Temp file rò rỉ trong `/tmp/` hoặc `TMPDIR`.

### 15. `update_node_statuses` không xoá status cũ

- **File:** `ui/tree_preview_widget.py:346-347`
- `self._current_status_dict.update(status_dict)` merge dict mới vào dict cũ.
- Nếu một path không còn trong `status_dict` mới, status tag của nó vẫn còn (không bị xoá khi gọi lại với dict nhỏ hơn).

### 16. Pygame import ở module level không optional

- **File:** `ui/media_preview_widget.py:12`
- `import pygame` ở module level khiến toàn bộ file fail nếu pygame không được cài.
- Các method khác (`SoundPlayer`, `_has_mixer`) dùng conditional import an toàn hơn.

### 17. `check_free_space` không handle permission errors rõ ràng

- **File:** `core/copy_engine.py:104`
- `except Exception: free = -1` — PermissionError và các lỗi khác đều dẫn đến `free = -1`.
- UI message hiển thị "Còn trống N/A" thay vì "Không thể kiểm tra".

### 18. Token sanitization trong DirectoryBuilder

- **File:** `core/directory_builder.py:22-24`
- `while ".." in val_str: val_str = val_str.replace("..", "")` — có thể bypass với `....` (4 dấu chấm) → sau khi replace còn `..`. Tuy nhiên, `os.path.commonpath` check ở line 42 bắt được path traversal thực tế, nên nguy cơ thấp.

### 19. Source path symlink không được resolve nhất quán

- **File:** `core/copy_engine.py:49`
- `os.path.abspath` resolve symlink cho source_dir, nhưng `set_source_path` trong sidebar không resolve symlink.
- Có thể dẫn đến duplicate path check sai (source vs destination comparison).

### 20. Thiếu project name config field trong UI

- **File:** toàn bộ UI (`config_panel.py`, `app.py`)
- Không có entry field để nhập project name.
- `config_panel.get_config()` không trả về project name.
- Report generator hardcode "Film Project".

### 21. `_adjust_image_zoom` không giữ trạng thái fit

- **File:** `ui/media_preview_widget.py:337-341`
- Khi `_zoom_factor == 1.0` (fit mode), lần zoom đầu tiên set `_zoom_factor = 1.0 * factor`.
- Lần zoom tiếp theo nhân tiếp, không có baseline là fit factor thực tế.
- Fit window button reset về 1.0 nhưng không re-calculate fit ratio.

### 22. `_clamp_sashes` dùng `HEADER_H = 30.0` cứng

- **File:** `ui/sidebar_panel.py:494`
- Header height là 30px hardcode, không dựa vào actual widget height.
- Nếu font/theme thay đổi (e.g., system DPI scaling), header có thể cao hơn 30px, gây overlap.

### 23. Tests thiếu edge case coverage

- **File:** `tests/test_core.py` và các test files khác
- Không test:
  - Unicode/non-ASCII filename
  - Path traversal attack
  - Empty source directory
  - Permission denied (source/destination không readable/writable)
  - Concurrent access / rapid cancel
  - File đang mở bởi process khác
  - Network timeout khi copy qua mạng
  - Disk full condition

### 24. `_rebalance_sections` gán weight không cần thiết

- **File:** `ui/sidebar_panel.py:563-565`
- Vòng lặp gọi `self.vpaned.pane(sec, weight=1)` cho mọi section đang mở và `weight=0` cho collapsed.
- PanedWindow weight thực sự chỉ cần set một lần; set lại mỗi lần rebalance gây layout calculation không cần thiết.

---

## ⚠️ LƯU Ý BẢO MẬT

### 25. Path traversal check case-sensitivity

- **File:** `core/directory_builder.py:42`
- `os.path.commonpath([dest_clean, abs_target]) != dest_clean` không case-insensitive.
- Trên Windows/macOS (HFS+ case-insensitive), path traversal check có thể bị bypass với khác case.
- `dest_clean = /Users/User/Project` và `abs_target = /USERS/USER/PROJECT/../../etc` sẽ bypass check.

### 26. HTML Report XSS

- **File:** `core/report_generator.py:234-438` (toàn bộ HTML template)
- Các biến user-controlled (`project_name`, `preset_name`, `source_dir`, destinations, `filename`, `shot_time`, `source_hash`, `dest_path`, ...) được inject trực tiếp vào HTML string qua f-string.
- Không có HTML escaping (`html.escape()` hoặc `&lt;` replacement).
- Nếu filename hoặc project name chứa `<script>`, XSS có thể xảy ra khi report được mở trong browser.
