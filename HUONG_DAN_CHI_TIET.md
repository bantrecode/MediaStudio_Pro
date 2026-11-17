# 📖 CẨM NANG HƯỚNG DẪN SỬ DỤNG - ALL-IN-ONE MEDIA STUDIO

Chào mừng bạn đến với **All-in-One Media Studio** – Bộ công cụ xử lý đa phương tiện chuyên nghiệp, chạy độc lập 100% trên Windows (không yêu cầu cài đặt Python, FFmpeg hay các phần mềm phụ trợ từ bên ngoài).

---

## 📑 MỤC LỤC
1. [Khởi Động Nhanh (Quick Start) Trong 3 Bước](#1-khởi-động-nhanh-quick-start-trong-3-bước)
2. [Module 1: Tải Video Đa Nền Tảng (YouTube, TikTok, Facebook...)](#2-module-1-tải-video-đa-nền-tảng-youtube-tiktok-facebook)
3. [Module 2: Cắt Video & Tự Động Chia Đoạn (Auto-Split)](#3-module-2-cắt-video--tự-động-chia-đoạn-auto-split)
4. [Module 3: Ghép & Nối Video Kèm Lồng Nhạc Nền](#4-module-3-ghép--nối-video-kèm-lồng-nhạc-nền)
5. [Module 4: Nén Chuẩn Mạng Xã Hội & Đổi Đuôi Siêu Tốc](#5-module-4-nén-chuẩn-mạng-xã-hội--đổi-đuôi-siêu-tốc)
6. [⚠️ NHỮNG LƯU Ý QUAN TRỌNG CẦN TRÁNH](#6-️-những-lưu-ý-quan-trọng-cần-tránh)
7. [Câu Hỏi Thường Gặp (FAQ)](#7-câu-hỏi-thường-gặp-faq)

---

## 1. Khởi Động Nhanh (Quick Start) Trong 3 Bước

Chỉ với 3 bước đơn giản, bạn có thể thực hiện mọi tác vụ xử lý video:

```
[Bước 1: Chọn Tính Năng] ➔ [Bước 2: Dán Link / Kéo Thả File] ➔ [Bước 3: Nhấn Bắt Đầu & Theo Dõi Hàng Đợi]
```

* **Bước 1: Chọn tính năng** trên thanh Menu bên trái (Sidebar):
  * 📥 **Tải Video:** Tải video từ YouTube, TikTok sạch logo, Facebook Reels, Douyin...
  * ✂️ **Cắt Video:** Cắt đoạn, chia nhỏ clip đăng TikTok/Shorts.
  * 🔗 **Ghép & Nối Video:** Nối nhiều video theo thứ tự, tự bù viền đen, lồng nhạc.
  * 🔄 **Nén & Đổi Đuôi:** Nén video gửi Zalo (<25MB), Discord (<10MB), đổi đuôi MOV sang MP4 trong 2 giây.
* **Bước 2: Thiết lập thông số:**
  * Dán đường link video hoặc kéo thả file video từ máy tính vào cửa sổ.
  * Chọn độ phân giải, thư mục lưu hoặc chế độ nén mong muốn.
* **Bước 3: Bắt đầu:**
  * Nhấn nút **"Bắt Đầu"** hoặc **"Thêm vào Hàng Đợi"**.
  * Bảng **Hàng Đợi Tác Vụ** ở nửa dưới cửa sổ sẽ hiển thị thanh tiến độ %, tốc độ xử lý (FPS) và thời gian còn lại. Bạn có thể tạm dừng, hủy hoặc chạy song song nhiều tác vụ.

---

## 2. Module 1: Tải Video Đa Nền Tảng (YouTube, TikTok, Facebook...)

### 2.1. Nền tảng hỗ trợ
* **YouTube:** Hỗ trợ mọi độ phân giải từ 480p, 720p, 1080p Full HD đến 2K, 4K 60fps; hỗ trợ tải trọn bộ Playlist; tự động tải phụ đề tiếng Việt / tiếng Anh (`.srt`).
* **TikTok & Douyin:** **Tự động trích xuất luồng video gốc KHÔNG CÓ LOGO (No-Watermark)** chìm trên video. Hỗ trợ cả link rút gọn (`vt.tiktok.com/...`) và link máy tính (`tiktok.com/@user/video/...`).
* **Facebook:** Hỗ trợ tải Facebook Watch, Video bài viết và Facebook Reels ở chất lượng cao nhất.
* **Các nền tảng khác:** Instagram Reels, Twitter/X, Bilibili, Vimeo, Soundcloud...

### 2.2. Các chế độ tải
1. **Tải đơn link:** Dán link vào ô ➔ Nhấn *Lấy Thông Tin* để xem trước tiêu đề, thời lượng và thumbnail ➔ Chọn độ phân giải ➔ Bấm *Tải Xuống*.
2. **Tự động bắt link từ Clipboard (Copy):** Khi bật cờ `⚡ Bắt link Clipboard`, bất cứ khi nào bạn sao chép (Ctrl+C) một link video trên trình duyệt, ứng dụng sẽ tự động dán và lấy thông tin ngay lập tức.
3. **Tải hàng loạt (Batch Mode):** Chuyển sang tab *Tải Hàng Loạt*, dán nhiều đường link (mỗi link 1 dòng) ➔ Nhấn *Tải Hàng Loạt*. Toàn bộ sẽ được xếp vào Hàng đợi tự động xử lý lần lượt.
4. **Tách lấy âm thanh MP3:** Chọn tùy chọn `Chỉ tải âm thanh (MP3 / M4A / WAV)` để tải nhạc, podcast với chất lượng âm thanh 192kbps - 320kbps.

---

## 3. Module 2: Cắt Video & Tự Động Chia Đoạn (Auto-Split)

### 3.1. Phân biệt 2 chế độ cắt
* **⚡ Chế độ Cắt Nhanh (Stream Copy `-c copy`):**
  * **Tốc độ:** Hoàn thành chỉ trong **1 đến 2 giây**, bất kể video dài hay ngắn.
  * **Chất lượng:** Giữ nguyên 100% chất lượng gốc, không suy hao pixel.
  * **Phù hợp:** Cắt bớt phần đầu/đuôi của video lớn mà không cần nén lại.
* **🎯 Chế độ Cắt Chuẩn Xác (Re-encode):**
  * **Độ chính xác:** Cắt chính xác tới từng khung hình (Frame-accurate / từng mili-giây).
  * **Tận dụng Card đồ họa (GPU):** Tự động kích hoạt NVIDIA RTX NVENC để render với tốc độ 300 - 600 FPS mà không làm đơ máy.
  * **Phù hợp:** Khi cần cắt ghép chính xác làm phim, làm clip ngắn.

### 3.2. Tính năng Cắt Tự Động Cho TikTok / Reels (Auto-Split)
* Bạn có 1 video dài 30 phút hoặc 1 tiếng?
* Chuyển sang tab **"Tự Động Cắt (Auto-Split)"** ➔ Chọn độ dài đoạn muốn chia (ví dụ: *60 giây, 90 giây, 3 phút, 5 phút*).
* Tùy chọn *Gối đầu thời gian (Overlap)*: 2 - 3 giây giúp đoạn sau nhắc lại đoạn trước mượt mà.
* Nhấn **Tạo Danh Sách Phân Đoạn** ➔ Toàn bộ các đoạn cắt sẽ được tạo và xuất ra thư mục đích tự động.

---

## 4. Module 3: Ghép & Nối Video Kèm Lồng Nhạc Nền

### 4.1. Tự động kiểm tra tương thích & Ghép thông minh
* Kéo thả nhiều video vào danh sách. Bạn có thể dùng nút **Lên (▲)**, **Xuống (▼)** để đổi thứ tự nối.
* **Ghép Siêu Tốc (Copy Mode):** Nếu các video đầu vào có cùng kích thước (ví dụ đều là 1920x1080, 30fps), ứng dụng tự động dùng cơ chế Concat Demuxer để ghép xong trong vài giây.
* **Tự Động Cân Chỉnh Viền Đen (Letterbox):** Nếu các clip lệch nhau (ví dụ video quay ngang 16:9 ghép với video quay dọc 9:16), ứng dụng tự động thêm viền đen cân đối để hình ảnh không bị méo hoặc kéo giãn.

### 4.2. Lồng nhạc nền (Background Music - BGM)
* Tích chọn **Lồng Nhạc Nền** ➔ Chọn file nhạc MP3 yêu thích.
* **Tự động lặp lại (Loop BGM):** Nếu video dài hơn bài nhạc, nhạc nền sẽ tự động phát lặp lại cho đến hết video.
* **Điều chỉnh âm lượng 2 nguồn:**
  * Kéo thanh *Âm lượng gốc* (ví dụ: 100% tiếng người nói).
  * Kéo thanh *Âm lượng nhạc nền* (ví dụ: 20% - 30% để nhạc êm dịu làm nền).

---

## 5. Module 4: Nén Chuẩn Mạng Xã Hội & Đổi Đuôi Siêu Tốc

### 5.1. Nén nhanh gửi mạng xã hội
* **💬 Nén cho Zalo (< 25MB):** Zalo chặn file video trên 25MB. Tính năng này tự động đo độ dài video và tính toán bitrate chính xác để video nén luôn nhỏ hơn 24MB mà vẫn rõ nét nhất có thể.
* **🎮 Nén cho Discord (< 10MB):** Dành riêng cho người dùng Discord tiêu chuẩn.
* **📧 Nén gửi Email / Web (< 50MB):** Tối ưu để đính kèm thư điện tử.

### 5.2. Remux Siêu Tốc (MOV sang MP4)
* Video quay từ iPhone/iPad thường ở dạng `.mov` rất nặng và khó xem trên một số thiết bị Android/Windows cũ.
* Tính năng Remux chỉ trích xuất luồng H.264/AAC và đóng lại thành đuôi `.mp4` trong **2 giây**, không mất chất lượng.

---

## 6. ⚠️ NHỮNG LƯU Ý QUAN TRỌNG CẦN TRÁNH

> [!CAUTION]
> **1. Tránh dán dồn dập hàng loạt link trong thời gian quá ngắn (Tránh bị chặn IP / Bot Detection):**
> * YouTube và các nền tảng mạng xã hội có hệ thống phát hiện bot tự động. Nếu dán và kích hoạt tải 30 - 50 link liên tục chỉ trong 2-3 giây từ cùng một IP máy tính, máy chủ có thể tạm thời phản hồi mã lỗi `HTTP 429 Too Many Requests` hoặc yêu cầu giải captcha.
> * **Cách phòng tránh:** Hãy để ứng dụng tải theo hàng đợi tự nhiên; nếu lỡ bị YouTube tạm chặn, hãy tạm ngưng 10 - 15 phút hoặc chuyển sang kết nối mạng 4G/Proxy để tiếp tục.

> [!WARNING]
> **2. Video Riêng Tư / Video Trong Group Facebook Kín:**
> * Công cụ hỗ trợ tải các video được chia sẻ ở chế độ **Công Khai (Public)**.
> * Các video bị khóa chế độ riêng tư (Chỉ bạn bè / Private / Group Facebook kín) không thể tải trực tiếp qua link công khai nếu không có phiên đăng nhập xác thực.

> [!NOTE]
> **3. Hiện tượng giật/đứng hình nhẹ 0.5s đầu khi Cắt Nhanh (Stream Copy):**
> * Cơ chế Stream Copy (`-c copy`) không nén lại dữ liệu, nên nó chỉ có thể bắt đầu cắt tại khung hình mốc (Keyframe / I-frame). Nếu điểm bạn chọn không rơi đúng Keyframe, trình phát video có thể bị đơ 0.5s đầu để chờ nạp đủ dữ liệu.
> * **Giải pháp:** Nếu bạn yêu cầu video phải mượt mà tuyệt đối từ khung hình đầu tiên, hãy chọn chế độ **"Mã hóa lại (Re-encode)"**.

> [!IMPORTANT]
> **4. Kiểm tra dung lượng ổ đĩa trống:**
> * Khi tải video 4K hoặc ghép các video có độ dài từ 30 phút trở lên, các file tạm thời và file kết quả có thể cần từ 2GB đến 10GB dung lượng. Hãy luôn đảm bảo ổ đĩa lưu (ổ C hoặc ổ đích) còn tối thiểu **5GB trống** để quá trình xử lý không bị đứt đoạn.

> [!NOTE]
> **5. Quy tắc bản quyền:**
> * Chỉ sử dụng ứng dụng để lưu trữ, sao lưu các tài liệu, bài giảng hoặc video mà bạn có quyền hợp pháp. Tôn trọng công sức của các nhà sáng tạo nội dung.

---

## 7. Câu Hỏi Thường Gặp (FAQ)

* **Q: Video TikTok tải về có bị mờ hoặc dính logo TikTok nhảy qua lại không?**
  * *A: Hoàn toàn không! Ứng dụng tự động lấy đường dẫn stream gốc từ máy chủ CDN của TikTok, giữ nguyên độ phân giải gốc và hoàn toàn sạch logo (No-Watermark).*
* **Q: Ứng dụng có làm máy tính bị đơ hoặc giật lag khi đang render video không?**
  * *A: Ứng dụng được trang bị cơ chế tự động thích ứng phần cứng (Hardware Adaptive Strategy). Nếu máy bạn có card đồ họa NVIDIA (ví dụ RTX 3060), GPU sẽ đảm nhận 95% khối lượng công việc; nếu máy tính yếu (dưới 4 nhân CPU), ứng dụng sẽ tự động chừa lại 1 nhân CPU cho hệ điều hành Windows, giúp chuột và các tác vụ khác vẫn hoạt động mượt mà.*
* **Q: Muốn chuyển ứng dụng sang máy tính khác sử dụng thì làm thế nào?**
  * *A: Bạn chỉ cần chép file `MediaStudio_Portable.zip` (hoặc thư mục `dist\MediaStudio\`) sang máy tính khác, giải nén và mở file `MediaStudio.exe` lên là dùng được ngay, không cần cài đặt thêm bất kỳ thứ gì!*

---
*Bản quyền phát triển © 2026 Media Studio Team. Mọi thắc mắc và đóng góp xin gửi về trang dự án.*

