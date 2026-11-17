# HƯỚNG DẪN BẢO TRÌ & NGUYÊN TẮC PHÁT TRIỂN (ENTERPRISE RULES)

> [!IMPORTANT]
> **ĐỌC KỸ TRƯỚC KHI THỰC HIỆN BẤT KỲ PHASE NÀO:**
> Dự án được thiết kế theo kiến trúc phân tầng độc lập (Layered Plugin Architecture). Bất kỳ ai chỉnh sửa mã nguồn (kể cả AI Assistant) **BẮT BUỘC** tuân thủ các nguyên tắc vàng sau đây để tránh làm hỏng hệ thống:

---

## 1. NGUYÊN TẮC VÀNG BẢO TRÌ HỆ THỐNG

### Quy tắc 1: Thư mục `core/` tuyệt đối KHÔNG import PySide6
- Thư mục `core/` là logic thuần Python.
- Mọi giao tiếp từ `core/` lên giao diện phải thông qua callbacks hoặc `JobQueueBridge`.
- Điều này cho phép test 100% logic bằng `pytest` mà không cần dựng GUI, đồng thời tái sử dụng được cho CLI sau này.

### Quy tắc 2: Định vị tài nguyên qua `resource_path()` và `assets/bin/`
- Không bao giờ viết cứng đường dẫn (hardcode).
- Thư mục nhị phân đóng gói nội bộ là `assets/bin/` (`ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`).
- Hàm `core.system.get_binary_path()` luôn ưu tiên:
  1. `%APPDATA%\MediaStudio\bin\` (bản cập nhật mới nhất)
  2. `resource_path("assets/bin")` (bản đóng gói sẵn)
  3. Cùng cấp file `.exe`
  4. PATH hệ thống.

### Quy tắc 3: Subprocess an toàn (CREATE_NO_WINDOW + UTF-8 + Process Tree Kill)
- Mọi lệnh gọi `subprocess.Popen` / `subprocess.run` phải truyền cờ `CREATE_NO_WINDOW` (`0x08000000` trên Windows) để không nháy cửa sổ console đen.
- Luôn đặt `encoding="utf-8", errors="replace"` để không bị lỗi font tiếng Việt khi parse tiến độ.
- Khi hủy (Cancel) hoặc tạm dừng (Pause), **phải dùng `psutil` để xử lý CẢ CÂY TIẾN TRÌNH** (`kill_process_tree`, `suspend_process_tree`, `resume_process_tree`), tuyệt đối không để lại tiến trình FFmpeg mồ côi.

### Quy tắc 4: Quản lý phiên bản Schema (Version Migration)
- `settings.json` có trường `"schema_version": 1`. Khi nâng cấp, bổ sung migration trong `ConfigManager.load()`.
- SQLite `history.db` sử dụng `PRAGMA user_version = 1`. Khi thay đổi cấu trúc bảng, kiểm tra và nâng cấp version tương ứng.

---

## 2. QUY TRÌNH THÊM MODULE MỚI (BASE_MODULE PLUGIN)

Mọi công cụ mới kế thừa từ `modules.base_module.BaseModule`:
1. Khai báo thuộc tính: `module_id`, `display_name`, `icon`, `description`.
2. Hàm `create_widget(parent, bridge)`: Trả về giao diện người dùng PySide6.
3. Hàm `validate_params(params)`: Kiểm tra tính hợp lệ trước khi đẩy vào Job Queue.
4. Hàm `execute_job(job, progress_cb, log_cb, cancel_event, pause_event)`: Hàm nghiệp vụ thuần túy chạy trong thread nền của Queue.

---

## 3. LỆNH CHẠY, KIỂM THỬ & ĐÓNG GÓI

1. Chạy unit tests:
   ```powershell
   python -m pytest -v
   ```
2. Khởi động ứng dụng từ mã nguồn:
   ```powershell
   python main.py
   ```
3. Đóng gói ứng dụng thành file thực thi và file nén Portable:
   ```powershell
   python build/build.py
   ```

---

## 4. HƯỚNG DẪN TRIỂN KHAI SANG MÁY TÍNH KHÁC (PORTABLE DEPLOYMENT)

Ứng dụng được thiết kế hoàn toàn độc lập, không yêu cầu cài Python, không cần cài FFmpeg, và chạy được dưới quyền người dùng thông thường (Standard User, không cần Administrator).

### Cách mang sang máy khác:
1. Lấy file **`dist/MediaStudio_Portable.zip`** (khoảng 185 MB) copy sang máy tính khác qua USB, Zalo, Google Drive...
2. Nhấp chuột phải vào file zip $\rightarrow$ Chọn **Extract All... (Giải nén)**.
3. Mở thư mục vừa giải nén, nhấp đúp vào file **`MediaStudio.exe`** để sử dụng ngay.

---

## 5. HƯỚNG DẪN SỬ DỤNG 4 MODULE CHÍNH

### 🔄 Module 1: Chuyển Đổi & Nén Media
- **Chọn file / Quét thư mục:** Kéo thả video hoặc bấm chọn thư mục để convert hàng loạt (Batch Mode).
- **Remux siêu tốc (`-c copy`):** Dùng khi chỉ muốn đổi đuôi file (ví dụ: `.mov` sang `.mp4`) mà giữ nguyên 100% chất lượng gốc chỉ trong 1-2 giây.
- **Smart Compress & Presets:**
  - Kéo thanh trượt CRF (18 - 30) để nén video tùy theo nhu cầu.
  - Chọn các preset một chạm: **Zalo < 25MB**, **Discord < 10MB**, **TikTok (1080p)**, **YouTube**.
- Bấm **Bắt đầu chuyển đổi** để đưa vào Hàng Đợi (Job Queue).

### ⬇️ Module 2: Tải Video Đa Năng
- **Tự bắt link Clipboard:** Khi bạn sao chép link YouTube, TikTok, Facebook... ứng dụng sẽ tự động điền link và phân tích thông tin.
- **Tùy chọn chất lượng:** Chọn tải Video độ nét cao (4K, 1080p, 720p) hoặc chỉ tách nhạc (MP3, WAV, M4A).
- **Tải Playlist & Hàng loạt:** Dán danh sách link hoặc link playlist để tải liên tục.
- **Chống tải trùng:** Ứng dụng tự động kiểm tra SQLite history để cảnh báo nếu bạn đã từng tải link này.

### 🔗 Module 3: Ghép & Nối Video
- **Sắp xếp linh hoạt:** Kéo thả video vào bảng, dùng nút **⬆️ Lên Trên** / **⬇️ Xuống Dưới** để chỉnh thứ tự ghép.
- **Ghép Nhanh vs Ghép Chuẩn Hóa:**
  - Nếu các video cùng kích thước và FPS: Ứng dụng tự dùng **Ghép Nhanh Copy** (siêu tốc, không mất chất lượng).
  - Nếu khác kích thước: Chọn kiểu tỉ lệ **Letterbox (viền đen giữ trọn hình)**, **Crop (lấp đầy màn hình)** hoặc **Stretch**.
- **Lồng nhạc nền (BGM):** Bật checkbox BGM, chọn file nhạc, chỉnh âm lượng nhạc nền và âm lượng video gốc, bật loop BGM.

### ✂️ Module 4: Cắt & Phân Đoạn Video
- **Trình phát xem trước:** Bấm phát, tua video trực tiếp trên giao diện.
- **Đánh dấu điểm cắt tức thì:** Khi đang xem, bấm `📍 [ Đặt Điểm Đầu` (Start) hoặc `📍 ] Đặt Điểm Cuối` (End) để bắt mốc thời gian.
- **Chế độ Cắt Nhanh (Stream Copy):** Cắt tức thì không hao tổn chất lượng (có cảnh báo keyframe).
- **Chế độ Tự Động Chia Nhỏ (Auto-Split):** Chọn preset 60 giây (Shorts/TikTok), 90 giây (Reels), 3 phút, hoặc tùy chỉnh để tự động chia video dài thành các phần nhỏ (Phần 1, Phần 2...).

---

## 6. CƠ CHẾ NHẬN DIỆN PHẦN CỨNG & THÍCH ỨNG (HARDWARE ADAPTIVE STRATEGY)

Ứng dụng tích hợp bộ điều phối phần cứng tự động `GPUDetector.get_hardware_profile()`:
- **Trên máy có card đồ họa rời (NVIDIA RTX 3060, NVENC / Intel QSV / AMD AMF):** Tự động kích hoạt GPU acceleration, tốc độ render đạt **350 - 600+ FPS**, CPU tiêu thụ < 5%, máy cực mát.
- **Trên máy tiêu chuẩn (CPU $\ge$ 6 nhân, RAM $\ge$ 8GB):** Dùng CPU đa luồng với `libx264 -preset veryfast` (nhanh gấp 4 lần preset medium cũ).
- **Trên máy tính yếu / máy văn phòng (CPU $\le$ 4 nhân, RAM $\le$ 8GB):**
  - Tự động chuyển sang `libx264 -preset ultrafast`.
  - **Chống đơ máy:** Giới hạn số luồng FFmpeg bằng `max(1, cpu_cores - 1)` để luôn giữ lại 1 nhân cho Windows, chuột, bàn phím và giao diện ứng dụng không bị đóng băng.

---

## 7. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

| Hiện tượng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| Lỗi `Failed to load Python DLL ...\build\app\_internal\...` | Chạy nhầm file exe tạm trong thư mục `build\app\` | Mở đúng file `dist\MediaStudio\MediaStudio.exe` hoặc giải nén từ `MediaStudio_Portable.zip`. |
| Video tải về từ YouTube bị lỗi cipher / sign-in | YouTube vừa cập nhật cơ chế bảo vệ | Vào tab **Tải Video**, ứng dụng tự động kiểm tra và tải bản `yt-dlp.exe` mới nhất về `%APPDATA%\MediaStudio\bin\`. |
| Cắt nhanh Stream Copy bị lệch mốc thời gian vài phần mười giây | Điểm cắt không trúng I-frame (Keyframe) | Chuyển sang chế độ **Cắt Chính Xác (Re-encode)** để chuẩn xác 100% từng khung hình. |
| Ghép video bị báo lỗi hoặc thời gian render quá lâu | Các video khác nhau về độ phân giải hoặc codec | Bật tăng tốc GPU trong bảng cài đặt hoặc chọn preset Letterbox 720p/1080p để app tự đồng bộ. |
