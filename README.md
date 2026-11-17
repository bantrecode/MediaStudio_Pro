# All-in-One Media Studio 🎬

> **Ứng dụng Windows Desktop Đa Năng Xử Lý Media:** Chuyển đổi & nén dung lượng, Tải video đa nền tảng, Ghép nối video, và Cắt phân đoạn chuyên nghiệp. Hoạt động offline 100%, không yêu cầu quyền Administrator, hỗ trợ tăng tốc GPU và đóng gói chạy độc lập trên mọi máy tính Windows 10/11.

---

## 🌟 Tính Năng Nổi Bật

### 1. 🔄 Chuyển Đổi & Nén Media (Converter & Smart Compressor)
- Hỗ trợ đầy đủ các định dạng: **MOV, MP4, MKV, AVI, MP3, WAV...**
- **Chế độ Remux siêu tốc (`-c copy`):** Chuyển đổi định dạng container chỉ mất 1-2 giây mà giữ nguyên 100% chất lượng gốc.
- **Smart Compress (CRF 18-30):** Nén tối ưu dung lượng mà vẫn giữ độ nét sắc nét.
- **Preset một chạm:**
  - `Zalo / Messenger`: Tự động tính toán bitrate ép dung lượng file dưới **25MB**.
  - `Discord`: Tự động ép dung lượng dưới **10MB**.
  - `TikTok`: Chuẩn khung hình dọc 1080p.
  - `YouTube`: Chuẩn Full HD 1080p.
- **Quét cả thư mục (Batch Mode):** Chuyển đổi hàng chục file cùng lúc với thanh tiến độ thời gian thực.

### 2. ⬇️ Trình Tải Video Đa Năng (Video Downloader)
- **Nhân xử lý:** Tích hợp `yt-dlp` mới nhất, hỗ trợ YouTube, TikTok (không watermark), Facebook, Douyin, Bilibili...
- **Clipboard Monitor:** Tự động bắt link ngay khi sao chép URL.
- **Tùy chọn chất lượng:** Tải video độ phân giải cao (4K, 1080p, 720p) hoặc chỉ tách file âm thanh (MP3 192k, WAV lossless, M4A).
- **Tải Playlist & Hàng loạt:** Dán danh sách link hoặc link playlist tải tự động.
- **Chống tải trùng lặp:** Lưu lịch sử SQLite trong `%APPDATA%`, cảnh báo nếu video đã tải trước đó.
- **Tự động cập nhật:** Có cơ chế tự động tải bản `yt-dlp.exe` mới nhất về máy khi nền tảng thay đổi API.

### 3. 🔗 Ghép & Nối Video (Video Merger)
- **Sắp xếp thứ tự trực quan:** Kéo thả video hoặc dùng nút Lên/Xuống để chỉnh thứ tự ghép nối.
- **Tự động nhận diện tương thích:**
  - Nếu cùng thông số: Tự động dùng **Ghép Nhanh Lossless (`-c copy`)** siêu tốc không hao tổn chất lượng.
  - Nếu khác kích thước/FPS: Dùng **Ghép Chuẩn Hóa qua Filter Complex**.
- **Xử lý lệch khung hình:** Hỗ trợ 3 chế độ: **Letterbox** (thêm viền đen giữ trọn hình), **Crop** (lấp đầy màn hình), **Stretch** (kéo dãn).
- **Lồng nhạc nền (Background Music - BGM):** Trộn âm thanh đa kênh (`amix`), điều chỉnh âm lượng video gốc và nhạc nền (0% - 100%), loop BGM, tùy chọn tắt tiếng video gốc.

### 4. ✂️ Cắt & Phân Đoạn Video (Video Cutter)
- **Trình phát video trực tiếp (QtMultimedia):** Xem trước video mượt mà, hỗ trợ thanh tua SeekBar.
- **Đánh dấu điểm cắt một chạm:** Bấm `📍 [ Đặt Điểm Đầu` hoặc `📍 ] Đặt Điểm Cuối` ngay khi xem video hoặc nhập mốc thời gian chính xác.
- **Chế độ Cắt Nhanh (Stream Copy):** Cắt tức thì không cần mã hóa lại, tự động reset timestamp tránh đen hình đầu video.
- **Chế độ Cắt Chính Xác (Re-encode):** Chuẩn xác 100% từng khung hình (frame-accurate) với tăng tốc GPU.
- **Tự Động Chia Nhỏ (Auto-Split):** Tự động chia video dài thành các phần nhỏ: 60 giây (TikTok/Shorts), 90 giây (Reels), 3 phút, 5 phút...

---

## ⚡ Tối Ưu Hóa Phần Cứng Đa Nền Tảng (Adaptive Strategy)

Ứng dụng tích hợp bộ điều phối thông minh tự động chấm điểm và kích hoạt chế độ phù hợp với từng máy tính:
- **Máy có card đồ họa rời (NVIDIA RTX 3060, NVENC / Intel QSV / AMD AMF):** Tự động kích hoạt GPU acceleration, tốc độ render đạt từ **350 – 600+ FPS**, CPU tiêu thụ < 5%, máy cực mát.
- **Máy tiêu chuẩn (CPU $\ge$ 6 nhân, RAM $\ge$ 8GB):** Sử dụng CPU đa luồng với `libx264 -preset veryfast -threads 0` (nhanh gấp 3-4 lần preset medium cũ).
- **Máy tính yếu / cấu hình văn phòng (CPU $\le$ 4 nhân, RAM $\le$ 8GB):**
  - Tự động chuyển sang `libx264 -preset ultrafast`.
  - **Chống đơ máy:** Giới hạn số luồng FFmpeg bằng `max(1, cpu_cores - 1)` để luôn giữ lại 1 nhân cho Windows, chuột và giao diện ứng dụng không bị treo.

---

## 📁 Cấu Trúc Dự Án

```
MediaStudio_Pro/
├── assets/                  # Tài nguyên tĩnh
│   ├── bin/                 # ffmpeg.exe, ffprobe.exe, yt-dlp.exe đóng gói
│   └── style.qss            # Giao diện Dark Mode QSS hiện đại
├── build/                   # Cấu hình đóng gói & installer
│   ├── app.spec             # File cấu hình PyInstaller (--onedir)
│   ├── build.py             # Script tự động hóa build & tạo Portable ZIP
│   └── installer.iss        # Kịch bản đóng gói Inno Setup
├── core/                    # 100% THUẦN PYTHON, ZERO IMPORT PYSIDE6
│   ├── system.py            # Quản lý đường dẫn, kill cây tiến trình psutil, dung lượng ổ đĩa
│   ├── config.py            # Cấu hình JSON (%APPDATA%\MediaStudio\settings.json)
│   ├── database.py          # SQLite lưu lịch sử & chống tải trùng link
│   ├── gpu.py               # Nhận diện GPU và chiến lược thích ứng máy yếu
│   ├── logger.py            # Ghi log xoay vòng & xuất ZIP báo lỗi
│   ├── single_instance.py   # Khóa mutex chống chạy trùng lặp app
│   ├── ffmpeg_runner.py     # Quản lý tiến trình FFmpeg, bắt % tiến độ qua pipe
│   ├── ytdlp_runner.py      # Quản lý tiến trình yt-dlp CLI
│   ├── converter_engine.py  # Nhân xử lý chuyển đổi & nén media
│   ├── ytdlp_engine.py      # Nhân xử lý tải video
│   ├── merger_engine.py     # Nhân xử lý ghép nối & lồng nhạc nền
│   ├── cutter_engine.py     # Nhân xử lý cắt video & chia nhỏ phân đoạn
│   └── job_queue/           # Hàng đợi đa luồng đa tác vụ
│       ├── job_model.py
│       └── queue_manager.py
├── modules/                 # CÁC PLUGIN THEO MÔ HÌNH BASE_MODULE
│   ├── base_module.py       # Abstract Base Class
│   ├── converter_module.py  # Module Chuyển đổi & Nén
│   ├── downloader_module.py # Module Tải Video
│   ├── merger_module.py     # Module Ghép Video
│   └── cutter_module.py     # Module Cắt Video
├── ui/                      # GIAO DIỆN NGƯỜI DÙNG PYSIDE6
│   ├── main_window.py       # Cửa sổ chính Shell UI
│   ├── bridge.py            # Cầu nối thread giữa Core và Qt
│   ├── components/          # Sidebar, JobQueuePanel, LogConsole
│   ├── dialogs/             # SettingsDialog, AboutDialog, HelpDialog
│   └── views/               # Giao diện của 4 module
│       ├── converter_widget.py
│       ├── downloader_view.py
│       ├── merger_widget.py
│       └── cutter_widget.py
├── tests/                   # BỘ KIỂM THỬ ĐỘC LẬP PYTEST (45/45 PASSED)
├── dist/                    # SẢN PHẨM PHÁT HÀNH
│   ├── MediaStudio/         # Bản chạy trực tiếp (MediaStudio.exe)
│   └── MediaStudio_Portable.zip # Bản nén Portable gửi sang máy khác (185 MB)
├── main.py                  # Entry Point khởi chạy app
├── HUONG_DAN_CHI_TIET.md    # Cẩm nang hướng dẫn sử dụng chi tiết & FAQ
├── requirements.txt         # Danh sách thư viện Python
```

---

## 🚀 Hướng Dẫn Sử Dụng & Triển Khai

### Cách 1: Sử dụng bản Portable trên máy tính khác (Không cần cài đặt)
1. Tải hoặc copy file **`dist/MediaStudio_Portable.zip`** sang máy tính khác (qua USB, Drive, Zalo...).
2. Nhấp chuột phải vào file zip $\rightarrow$ Chọn **Extract All... (Giải nén)**.
3. Mở thư mục vừa giải nén, nhấp đúp vào file **`MediaStudio.exe`** để chạy ngay.
   *(Không cần cài Python, không cần cài FFmpeg, chạy được trên máy chưa cài gì).*

### Cách 2: Chạy từ mã nguồn (Dành cho nhà phát triển)
```powershell
# 1. Kích hoạt môi trường Python (Python 3.11 - 3.14)
# 2. Cài đặt phụ thuộc
pip install -r requirements.txt

# 3. Chạy unit tests
python -m pytest -v

# 4. Khởi động ứng dụng
python main.py

# 5. Đóng gói ứng dụng thành file exe và file zip
python build/build.py
```

---

## 📋 Kiểm Thử & Nghiệm Thu
Dự án đạt chuẩn kiểm thử tự động **100% (45/45 Unit Tests Passed)** bao quát toàn bộ các module xử lý dữ liệu, kiểm tra dung lượng ổ đĩa, xử lý đường dẫn tiếng Việt Unicode, cơ chế chống tải trùng, thuật toán ghép và cắt video.

