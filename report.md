# BÁO CÁO THIẾT KẾ CHI TIẾT & YÊU CẦU NGHIỆP VỤ: PHẦN MỀM DIT COPY PRO

## 1. Mục Tiêu Thiết Kế Bản Nâng Cấp
Để khắc phục hạn chế của việc thiết kế cứng (hard-coded) cho một dự án duy nhất, phần mềm cần được cấu trúc lại nhằm đáp ứng các tiêu chuẩn sản xuất linh hoạt hơn. Mục tiêu của thiết kế mới bao gồm:
*   **Vận hành đa dạng dự án:** Cho phép người dùng tự định nghĩa quy tắc đặt tên file (Naming Convention) và cấu trúc thư mục (Folder Directory) phù hợp với từng thiết bị ghi hình (ARRI, RED, Sony, Canon, DJI...).
*   **Bảo vệ dữ liệu tối đa:** Đa dạng hóa các phương thức xác thực và tăng tốc độ xử lý khi làm việc với lượng dữ liệu lớn (Big Data).
*   **Tối giản hóa thao tác (UX):** Thiết kế giao diện trực quan hỗ trợ chế độ tối (Dark Mode) cho phòng dựng, giảm thiểu tối đa các bước thiết lập lặp đi lặp lại thông qua hệ thống lưu trữ cấu hình (Presets).

---

## 2. Thông Số Chức Năng Nâng Cao (Tính Tùy Biến Sâu)

### 2.1. Hệ thống Phân tích Quy tắc Đặt tên Linh hoạt (Token-based Naming Parser)
Thay vì cố định định dạng `A005001`, phần mềm cung cấp một bộ lọc nhận diện sử dụng cấu trúc Token hoặc Regular Expression (Regex). Người dùng có thể tùy biến cách phần mềm "đọc" tên file gốc từ thẻ nhớ.

Các Token chuẩn được định nghĩa sẵn bao gồm:
*   `{Camera}`: Ký tự định danh máy quay (Ví dụ: A, B, C, CAM_A).
*   `{Roll}`: Số thứ tự thẻ/cuộn băng (Ví dụ: 001, 002, 005).
*   `{Clip}`: Số thứ tự phân đoạn clip (Ví dụ: 001, 002).
*   `{Date}`: Ngày tháng ghi hình (Định dạng DDMMYYYY hoặc YYYYMMDD).
*   `{Project}`: Tên dự án hiện tại.

**Ví dụ thiết lập:**
*   *Cấu hình dự án 1:* Tên file `A005012.mp4` -> Quy tắc: `{Camera:1}{Roll:3}{Clip:3}`
*   *Cấu hình dự án 2 (Cinema):* Tên file `A001C002_25072026.MXF` -> Quy tắc: `{Camera:1}{Roll:3}C{Clip:3}_{Date:8}`

### 2.2. Hệ thống Tự Động Tạo Thư Mục Động (Dynamic Directory Template)
Sau khi nhận diện được các Token từ tên file, phần mềm cho phép người dùng tự thiết lập cây thư mục lưu trữ tại ổ cứng đích theo mong muốn bằng cách ghép các Token lại với nhau.

**Ví dụ về các mẫu cấu trúc thư mục (Template Path):**
*   *Mẫu 1 (Theo Camera trước):* `{Destination}/Footage/{Camera}/Roll_{Roll}/`
    *   Kết quả xuất ra: `D:/RAID_01/Footage/A/Roll_005/A005001.mp4`
*   *Mẫu 2 (Theo Ngày trước):* `{Destination}/{Date}/{Project}/CAM_{Camera}/`
    *   Kết quả xuất ra: `D:/RAID_01/25072026/MyProject/CAM_A/A001C002_25072026.MXF`

### 2.3. Tùy Chọn Thuật Toán Xác Thực (Verification Algorithms)
Để tối ưu hóa giữa độ an toàn dữ liệu và tốc độ xử lý tùy thuộc vào tốc độ của ổ cứng/thẻ nhớ đầu vào, phần mềm cung cấp các tùy chọn thuật toán kiểm tra:
*   **MD5:** Tiêu chuẩn xác thực phổ biến nhất trong điện ảnh, độ an toàn cao.
*   **XXHash64 / XXH3:** Thuật toán băm tốc độ cực nhanh, tận dụng tối đa băng thông của ổ cứng NVMe và hệ thống RAID, giảm thiểu nghẽn cổ chai CPU.
*   **SHA-256:** Bảo mật ở mức tối đa (dành cho các dự án yêu cầu khắt khe từ các hãng sản xuất lớn).
*   **Chỉ kiểm tra Dung lượng (Size-only):** Chỉ so sánh dung lượng byte để sao chép nhanh, bỏ qua bước băm hash (không khuyến nghị cho DIT chuyên nghiệp nhưng phù hợp khi cần xử lý gấp).

### 2.4. Trình Quản Lý Cấu Hình Dự Án (Presets Management)
*   Người dùng có thể lưu toàn bộ thiết lập gồm: Quy tắc đặt tên file, Cấu trúc thư mục đích, Thuật toán xác thực, và Định dạng báo cáo thành một **Preset** (Ví dụ: *"Arri Alexa Mini LF - 4K"*, *"Sony FX6 - Standard"*, *"GoPro 11 - Documentaries"*).
*   Cho các dự án tiếp theo, người dùng chỉ cần chọn Preset phù hợp từ menu thả xuống mà không cần thiết lập lại từ đầu.

---

## 3. Thiết Kế Trực Quan Giao Diện & Trải Nghiệm (UI/UX)

Để đảm bảo hiệu quả làm việc ngoài hiện trường (nhiều ánh sáng mạnh hoặc tối, áp lực thời gian, mệt mỏi), giao diện được thiết kế theo các tiêu chí: **Tập trung cao độ**, **Tương phản rõ nét**, và **Hạn chế nhấp chuột**.

### 3.1. Phác Thảo Bố Cục Giao Diện Trực Quan (Wireframe)

```text
+---------------------------------------------------------------------------------+
|  [DIT COPY PRO]                               Preset: [ ARRI ALEXA Standard v ] |
+---------------------------------------------------------------------------------+
|  [1] CHỌN THẺ NHỚ NGUỒN (SOURCE)                                                |
|  +---------------------------------------------------------------------------+  |
|  | [ G:/DCIM/A001C001_25072026/                                ] [ Duyệt... ] |  |
|  +---------------------------------------------------------------------------+  |
|  [2] CHỌN THƯ MỤC LƯU TRỮ (DESTINATION)                                         |
|  +---------------------------------------------------------------------------+  |
|  | [ D:/RAID_01/Footage/Day_01/                                ] [ Duyệt... ] |  |
|  +---------------------------------------------------------------------------+  |
|                                                                                 |
|  [3] THÔNG SỐ CẤU HÌNH NHANH (QUYẾT ĐỊNH QUY TẮC)                                |
|  - Cấu trúc File:   {Camera:1}{Roll:3}C{Clip:3}_{Date:8}                         |
|  - Cấu trúc Folder: {Destination}/{Camera}/Roll_{Roll}/                         |
|  - Xác thực bằng:   [ MD5  v ] | Định dạng Log: [ TXT v ]                      |
|                                                                                 |
|  [4] TIẾN TRÌNH THỰC THI                                                        |
|  Đang xử lý file: A001C001_002.MXF (51.76 GB)                                   |
|  [██████████████████████████████████░░░░░] 78% | 420 MB/s (Còn lại: 1p 15s)    |
|  Tiến trình tổng thể (Thẻ A001C001):                                            |
|  [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░] 30% | Đã xong 2/15 Files             |
|                                                                                 |
|  [5] BẢNG THEO DÕI TRẠNG THÁI FILE THỜI GIAN THỰC                               |
|  +---------------------------------------------------------------------------+  |
|  | [✓ VERIFIED]  A001C001_001.MXF (48.13 GB) - MD5: a1c8e6f5... - Trùng khớp |  |
|  | [▶ COPYING ]  A001C001_002.MXF (51.76 GB) - Đang ghi dữ liệu...           |  |
|  | [░ QUEUED  ]  A001C001_003.MXF (42.81 GB) - Đang chờ xử lý...             |  |
|  +---------------------------------------------------------------------------+  |
|                                                                                 |
|  [ HỦY QUÁ TRÌNH ]                                         [ BẮT ĐẦU SAO CHÉP ] |
+---------------------------------------------------------------------------------+
```

### 3.2. Điểm Nhấn Trải Nghiệm Người Dùng (UX Highlights)
*   **Kéo và thả (Drag and Drop):** Hỗ trợ kéo thả trực tiếp thư mục Thẻ nhớ từ Finder/Explorer vào vùng chọn Source, và kéo thư mục Ổ cứng vào vùng Destination.
*   **Hệ thống Chỉ số Màu trực quan (Color-Coded Status):**
    *   `Màu Xanh lá (Green)` cho trạng thái **VERIFIED ✓** (Tâm lý an tâm cho kỹ thuật viên).
    *   `Màu Đỏ (Red)` cho trạng thái **FAILED ✗** hoặc cảnh báo lỗi hệ thống, ổ cứng bị ngắt kết nối đột ngột.
    *   `Màu Vàng (Yellow)` cho trạng thái đang thực thi (Copying/Hashing).
*   **Hộp thoại Cảnh báo Lớn (Big Alert Dialog):** Khi phát hiện sai lệch MD5 (Lỗi Corrupt), phần mềm sẽ hiện pop-up toàn màn hình kèm âm báo cảnh báo đặc trưng, ngăn chặn việc vô tình format thẻ nhớ lỗi khi chưa khắc phục xong.
*   **Hỗ trợ chạy ngầm và thông báo:** Có âm thanh thông báo riêng biệt khi hoàn thành việc sao chép thẻ (Âm thanh "Thành công" nhẹ nhàng và âm thanh "Thất bại" dồn dập).

---

## 4. Yêu Cầu Phi Chức Năng & Hiệu Năng

*   **Hiệu năng đọc/ghi song song:** Tối ưu hóa bộ nhớ đệm (buffer memory) khi đọc dữ liệu từ thẻ nhớ tốc độ cao (như CFexpress, SD UHS-II) để tránh thắt nút cổ chai.
*   **Tính liên tục (Resilience):** Trong trường hợp lỗi giữa chừng, phần mềm phải ghi nhận những file nào đã hoàn tất xác thực, cho phép tiếp tục sao chép (Resume) các file còn lại thay vì phải chạy lại từ đầu toàn bộ thẻ.
*   **Trích xuất siêu dữ liệu thời gian:**
    *   Hệ thống đọc dữ liệu metadata của file hệ thống (Date Created / Date Modified) hoặc đọc sâu hơn vào metadata của file video (.MXF, .MP4, .MOV, .R3D) để lấy thông tin Giờ bấm máy (Timecode/Creation Time) phục vụ cho việc ghi nhận lịch trình sản xuất.

---

## 5. Định Dạng Báo Cáo Đầu Ra Mẫu (Tích Hợp Metadata Thời Gian)

Dưới đây là thiết kế chi tiết cho báo cáo được nâng cấp, bổ sung các thông tin về **Thời gian ghi hình (Shot Time)** và **Loại thuật toán sử dụng (Algorithm Type)**:

```text
===========================================================================
                               DIT COPY REPORT
===========================================================================

Project Name: [Tên Dự Án]
Preset Used : ARRI ALEXA Standard
Date/Time   : 2026-07-21 17:30:00 (Thời gian thực hiện tác vụ)

Source Card : A001C001_25072026 (Đường dẫn: G:/DCIM/A001C001_25072026/)
Destination : RAID_01/Footage/Day01/ (Đường dẫn: D:/RAID_01/Footage/Day01/)
Verification: MD5 (Multi-threaded)

-----------------------------------------------------------------------------------------------------------------------
Filename               Size        Shot Date/Time       Source MD5                       Destination MD5                  Status
-----------------------------------------------------------------------------------------------------------------------

A001C001_001.MXF       48.13 GB    2026-07-21 09:15:32  a1c8e6f53d6c9b1f8c4a21d87d9e7b42 a1c8e6f53d6c9b1f8c4a21d87d9e7b42 VERIFIED ✓
A001C001_002.MXF       51.76 GB    2026-07-21 09:45:10  5f9d1a437be839bcb8d8124b3ec40fa1 5f9d1a437be839bcb8d8124b3ec40fa1 VERIFIED ✓
A001C001_003.MXF       42.81 GB    2026-07-21 10:20:05  d8fa44c72ce87c95f9e2db92d0c3b6aa d8fa44c72ce87c95f9e2db92d0c3b6aa VERIFIED ✓
A001C001_015.MXF       47.83 GB    2026-07-21 11:58:44  4f92c8ab16d73e5fc8b91a6d20ee74a1 7e34b19fd53a8cb64c1fe2a5d4c901be FAILED ✗

-----------------------------------------------------------------------------------------------------------------------
Summary
-----------------------------------------------------------------------------------------------------------------------

Total Files       : 15
Verified          : 14
Failed            : 1
Total Size        : 736.89 GB
Time Elapsed      : 00:32:15 (Tốc độ trung bình: ~380 MB/s)

WARNING:
Checksum mismatch detected. One or more files are corrupted!

Failed File:
A001C001_015.MXF

Shot Date/Time  : 2026-07-21 11:58:44
Source MD5      : 4f92c8ab16d73e5fc8b91a6d20ee74a1
Destination MD5 : 7e34b19fd53a8cb64c1fe2a5d4c901be

Result:
The destination file does NOT match the source.
File may be corrupted, truncated, or incomplete.

Recommendation: 
DO NOT format the camera card. Clean the ports, check the cable, and re-copy this file manually or restart the process for this file.
===========================================================================
```