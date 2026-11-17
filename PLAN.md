# KẾ HOẠCH & KIẾN TRÚC ALL-IN-ONE MEDIA STUDIO (BẢN CHUẨN DOANH NGHIỆP)

## 1. RÀNG BUỘC KỸ THUẬT CỐT LÕI
- **Nền tảng:** Windows 10/11 64-bit, Python 3.11/3.12 (venv).
- **GUI:** **PySide6 (Qt 6)**.
- **Tách biệt Core & GUI:** Thư mục `core/` 100% thuần Python, **tuyệt đối không import PySide6**, test độc lập bằng `pytest` và tái sử dụng cho CLI.
- **Quyền hạn & Lưu trữ:** Chạy dưới quyền Standard User. Cấu hình (`settings.json`, schema v1), SQLite (`history.db`, user_version 1), log xoay vòng (`logs/app.log`), lock file (`app.lock`) và file tạm (`temp/`) lưu tại `%APPDATA%\MediaStudio\`.
- **Subprocess an toàn:**
  - Cờ `CREATE_NO_WINDOW` (`0x08000000` trên Windows) chống nháy console.
  - Đọc luồng `stdout`/`stderr` bằng `encoding="utf-8", errors="replace"` chống vỡ font tiêu đề tiếng Việt.
  - Sử dụng `psutil` để tạm dừng/tiêu diệt **CẢ CÂY TIẾN TRÌNH** (`kill_process_tree`, `suspend_process_tree`, `resume_process_tree`), chống để lại tiến trình FFmpeg/yt-dlp mồ côi (zombie/orphan).
- **Định vị tài nguyên (`resource_path`):** Tự động phân giải đường dẫn giữa môi trường dev và gói PyInstaller (`sys._MEIPASS`). Thư mục nhị phân đóng gói đặt tại `assets/bin/` (`ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`).
- **Chiến lược yt-dlp:** Chạy độc lập `yt-dlp.exe` qua subprocess (thay vì import pip), ưu tiên bản cập nhật tải về tại `%APPDATA%\MediaStudio\bin\yt-dlp.exe`.
- **Single Instance & Crash Handler:** Khóa `app.lock` chống mở trùng lặp và gắn `sys.excepthook` ghi unhandled crash vào log.

---

## 2. LỘ TRÌNH TRIỂN KHAI PHÂN TẦNG [MUST] & [LATER]

### [x] Phase 0: Hạ Tầng Cốt Lõi, Shell UI & Job Queue (ĐÃ HOÀN TẤT)
- [x] Cấu trúc dự án: `core/`, `modules/`, `ui/`, `assets/bin/`, `tests/`.
- [x] `core/system.py`: `resource_path()`, `CREATE_NO_WINDOW`, `check_disk_space()`, `clean_unicode_filename()`, `kill_process_tree()`.
- [x] `core/config.py`: `schema_version = 1`, tự khôi phục khi file hỏng.
- [x] `core/database.py`: SQLite `history.db` (`PRAGMA user_version = 1`), lưu lịch sử job & link chống tải trùng.
- [x] `core/gpu.py`: Dò GPU (NVENC/QSV/AMF), test encode mẫu 0.1s, fallback CPU (libx264/libx265).
- [x] `core/ffmpeg_runner.py`: `-progress pipe:1`, ffprobe đọc duration/metadata, dịch mã lỗi tiếng Việt, dọn file dở dang.
- [x] `core/ytdlp_runner.py`: Subprocess CLI runner với UTF-8, tự cập nhật bản GitHub mới nhất về `%APPDATA%\MediaStudio\bin\`.
- [x] `core/job_queue/`: Dataclass `Job` và `QueueManager` đa luồng (pause/resume/cancel/retry, max_concurrent).
- [x] `core/single_instance.py` & `setup_crash_handler()` trong `core/logger.py`.
- [x] `modules/base_module.py`: Lớp trừu tượng BaseModule + 4 module stubs.
- [x] `ui/`: Main window shell Dark mode, Sidebar động, Job Queue panel, Log dock (Xuất ZIP), Settings & About dialogs.
- [x] `tests/`: Bộ unit test đầy đủ cho `core/` bằng pytest.

---

### [x] Phase 1: Module 4 - Chuyển Đổi & Nén (ĐÃ HOÀN TẤT)
- [x] Triển khai `core/converter_engine.py`:
  - Chuyển đổi định dạng đa dạng: MOV, MP4, MKV, AVI, MP3, WAV.
  - Chế độ **Remux siêu tốc (`-c copy`)** chỉ đổi container.
  - Quét toàn bộ thư mục (Batch Mode) để chuyển đổi hàng chục file cùng lúc.
  - Smart Compress với CRF tùy chỉnh (18 - 30) tối ưu kích thước.
  - **Ước tính dung lượng đầu ra (Estimated Size)** thời gian thực theo CRF và độ phân giải.
  - **Preset một chạm:** TikTok (chuẩn 1080p H.264), YouTube (1080p), Zalo/Messenger (tự tính bitrate ép <25MB), Discord (<10MB).
  - Tích hợp GPU Detector (NVIDIA NVENC, Intel QSV, AMD AMF) và fallback an toàn về CPU.
- [x] Triển khai `ui/views/converter_widget.py` và liên kết vào `ConverterModule(BaseModule)`.
- [x] Tạo bộ unit test độc lập `tests/test_converter_engine.py`.

---

### [x] Phase 1.5: Đóng Gói Thử Nghiệm Sớm (--onedir) & Kiểm Thử Máy Sạch (ĐÃ SẴN SÀNG)
- [x] Soạn file cấu hình `build/app.spec` chế độ `--onedir` (tắt UPX chống false positive AV, đóng gói assets/bin/, gom hidden imports QtMultimedia & psutil).
- [x] Soạn script tự động hóa `build/build.py` (tự dọn dẹp, kiểm tra phụ thuộc, build PyInstaller, verify kết quả).
- [x] Soạn kịch bản Inno Setup `build/installer.iss` (bộ cài đặt Setup.exe chuyên nghiệp chạy dưới quyền Standard User, không đòi hỏi UAC Admin).
- [x] Soạn tài liệu nghiệm thu `build/CHECKLIST_KIEM_THU_MAY_SACH.md` với 10 bài test thực tế trên máy ảo/máy sạch.

---

### [x] Phase 2: Module 1 - Trình Tải Video Đa Năng (ĐÃ HOÀN TẤT)
- [x] Kế thừa và nâng cấp các giải pháp tối ưu từ `Download_video_tu_Youtube/Desktop`:
  - `clean_filename()`: Chuẩn hóa tên file tiếng Việt có dấu và loại bỏ ký tự cấm Windows.
  - Cấu hình bypass JS runtime (Deno/Node), timeout 30s, retries 3 lần.
  - Tự động nhận diện `ffmpeg.exe` liên kết cho yt-dlp ghép audio/video.
- [x] Triển khai nhân xử lý CLI `yt-dlp.exe` độc lập (`core/ytdlp_runner.py`) qua subprocess với cờ `CREATE_NO_WINDOW` và `encoding="utf-8", errors="replace"`.
- [x] **Clipboard Monitor:** Tự động bắt link khi copy (YouTube, TikTok, Facebook, Douyin, Bilibili...).
- [x] Tải chất lượng cao (4K, 1080p, 720p, 480p) gộp MP4 chuẩn hoặc chỉ tách nhạc (MP3, WAV, M4A).
- [x] Tải hàng loạt (Batch Links) và tải toàn bộ Playlist.
- [x] Tự động kiểm tra trùng lặp qua SQLite (`core.database.HistoryDB.is_url_downloaded`), cảnh báo nếu link đã tải.
- [x] Tự động lưu link đã tải thành công vào SQLite history.
- [x] Giới hạn tốc độ tải (`--limit-rate`), tự động tải phụ đề song ngữ (`vi`, `en`).
- [x] Tích hợp dòng Disclaimer miễn trừ trách nhiệm bản quyền.
- [x] Bộ unit test độc lập `tests/test_ytdlp_engine.py`.

---

### [x] Phase 3: Module 3 - Trình Ghép & Nối Video (ĐÃ HOÀN TẤT)
- [x] Kế thừa và nâng cấp từ `Ghep_Video` (v1, v2, v3):
  - [x] Danh sách video trực quan: Kéo thả (Drag & Drop), nút Lên Trên / Xuống Dưới / Xóa.
  - [x] **Kiểm tra tương thích tự động:** So khớp resolution, fps, codec, audio sample rate.
  - [x] **Ghép Nhanh Lossless (`-c copy`):** Concat demuxer siêu tốc không mất chất lượng khi cùng định dạng.
  - [x] **Ghép Chuẩn Hóa qua Filter Complex:** Tự động đồng bộ kích thước (Letterbox viền đen, Crop lấp đầy, Stretch) và tạo audio im lặng cho clip không tiếng.
  - [x] **Lồng nhạc nền (BGM):** Trộn đa kênh `amix`, thanh trượt âm lượng độc lập, loop BGM, mute tiếng gốc.
  - [x] Tăng tốc GPU (NVIDIA NVENC, Intel QSV, AMD AMF) và tự động fallback CPU.
  - [x] 9 bài unit tests độc lập `tests/test_merger_engine.py` (100% Passed).

---

### [x] Phase 4: Module 2 - Trình Cắt Video Trực Quan (ĐÃ HOÀN TẤT)
- [x] Kế thừa và nâng cấp từ `flask-video-cutter`:
  - [x] Trình phát xem trước video tích hợp (`QMediaPlayer` + `QVideoWidget`) kèm thanh tua và thời gian thời gian thực.
  - [x] Đánh dấu mốc Start / End trực tiếp bằng 1 nút bấm hoặc nhập số giờ:phút:giây chính xác.
  - [x] Nút xem thử đoạn cắt (Preview Cut Segment).
  - [x] **Hai chế độ cắt rõ ràng:**
    - [x] *Cắt nhanh (`-c copy`):* Chỉ mất 1-2 giây, có cảnh báo keyframe trực quan và `-avoid_negative_ts make_zero`.
    - [x] *Cắt chính xác (Re-encode):* Chuẩn xác từng khung hình kèm tăng tốc GPU và CRF.
  - [x] **Auto-Split (Tự động chia nhỏ):** Preset 60s (TikTok/Shorts), 90s (Reels), 3 phút, 5 phút, hoặc tùy chỉnh. Tự động sinh danh sách phân đoạn Phần 1, Phần 2...
  - [x] 7 bài unit tests độc lập `tests/test_cutter_engine.py` (100% Passed).

---

### [x] Phase 5: Đóng Gói Hoàn Chỉnh & Tối Ưu Hóa Đa Nền Tảng (ĐÃ HOÀN TẤT)
- [x] Sửa lỗi kiểm thử probe card đồ họa (tăng kích thước test lên `256x256`), nhận diện chính xác 100% **NVIDIA GeForce RTX 3060 (12GB VRAM)**, render ở tốc độ **350 - 600+ FPS**.
- [x] Xây dựng cơ chế **Thích ứng 3 tầng (3-Tier Adaptive Strategy)** cho máy tính yếu:
  - Máy yếu (CPU <= 4 nhân, RAM < 8GB): Tự động đổi preset sang `ultrafast` và giới hạn `-threads max(1, cpu_cores - 1)` để chống đơ chuột, chống treo máy.
  - Máy tiêu chuẩn: Dùng `libx264 -preset veryfast -threads 0`.
- [x] Kịch bản Inno Setup `build/installer.iss` tạo file `MediaStudio_Setup.exe` chuyên nghiệp.
- [x] Đóng gói hoàn chỉnh PyInstaller `--onedir` tại `dist/MediaStudio/MediaStudio.exe`.
- [x] Tự động nén gói Portable phát hành **`dist/MediaStudio_Portable.zip` (185.4 MB)**.
- [x] Toàn bộ **45/45 Unit Tests** đạt chuẩn (100% Passed).

---

### [ ] Phase 6 (Tùy chọn tương lai): Module 5 - Phụ Đề Tự Động (Whisper AI)
- Tích hợp `faster-whisper` chạy offline, tải model về `%APPDATA%`, xuất `.srt`/`.vtt`.
