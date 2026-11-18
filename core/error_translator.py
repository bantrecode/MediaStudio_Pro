"""
Error Translator Core Module
Dịch các lỗi phổ biến của FFmpeg và yt-dlp sang thông báo tiếng Việt dễ hiểu,
kèm gợi ý khắc phục cụ thể cho người dùng.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import re
from typing import Optional


# Danh mục các mẫu lỗi phổ biến và bản dịch tiếng Việt tương ứng
FFMPEG_ERROR_PATTERNS = [
    (
        r"No space left on device|disk full",
        "Ổ đĩa lưu trữ đã hết dung lượng trống. Vui lòng dọn dẹp hoặc chọn thư mục lưu trên ổ đĩa khác."
    ),
    (
        r"Permission denied|Access is denied",
        "Không có quyền ghi dữ liệu vào thư mục đầu ra. Vui lòng chọn thư mục khác (ví dụ: Downloads hoặc Desktop) hoặc kiểm tra quyền truy cập."
    ),
    (
        r"Invalid data found when processing input|could not find codec parameters",
        "File nguồn bị lỗi, hư hỏng hoặc không đúng chuẩn định dạng media hợp lệ."
    ),
    (
        r"Unknown encoder '([^']+)'|Cannot find encoder '([^']+)'",
        "Không tìm thấy bộ mã hóa tương thích trên hệ thống. Hãy thử chuyển sang bộ mã hóa CPU (libx264)."
    ),
    (
        r"moov atom not found",
        "File video nguồn chưa được tải xong hoàn chỉnh hoặc cấu trúc file MP4 bị hỏng (thiếu moov atom)."
    ),
    (
        r"Error while opening encoder.*NVENC",
        "Lỗi khởi tạo tăng tốc NVIDIA NVENC. Driver đồ họa có thể quá cũ hoặc GPU đang bận, hãy chuyển sang Auto hoặc CPU."
    ),
    (
        r"Error while opening encoder.*qsv",
        "Lỗi khởi tạo Intel QuickSync (QSV). Hãy kiểm tra driver đồ họa tích hợp Intel hoặc chuyển sang CPU."
    ),
    (
        r"Error while opening encoder.*amf",
        "Lỗi khởi tạo AMD AMF. Hãy cập nhật driver card màn hình AMD hoặc chuyển sang CPU."
    ),
    (
        r"Width or height not divisible by 2",
        "Kích thước khung hình video phải là số chẵn (chia hết cho 2). Ứng dụng sẽ tự động căn chỉnh lại."
    ),
]

YTDLP_ERROR_PATTERNS = [
    (
        r"HTTP Error 403: Forbidden",
        "Máy chủ video từ chối truy cập (403 Forbidden). Liên kết có thể đã hết hạn hoặc máy chủ hạn chế IP. Hãy thử lấy lại link mới."
    ),
    (
        r"HTTP Error 429: Too Many Requests",
        "Máy chủ báo lỗi quá nhiều yêu cầu trong thời gian ngắn (429 Too Many Requests). Vui lòng tạm dừng vài phút trước khi tải tiếp."
    ),
    (
        r"Sign in to confirm you’re not a bot|Sign in to confirm your age",
        "Nền tảng yêu cầu đăng nhập hoặc xác minh không phải bot / giới hạn độ tuổi. Không thể tải trực tiếp không đăng nhập."
    ),
    (
        r"Video unavailable|This video has been removed",
        "Video này không khả dụng, đã bị tác giả xóa hoặc bị đặt ở chế độ riêng tư."
    ),
    (
        r"Private video|members-only",
        "Video này được đặt ở chế độ riêng tư hoặc chỉ dành cho hội viên (Members-only)."
    ),
    (
        r"The playlist does not exist|not a valid playlist",
        "Danh sách phát (Playlist) không tồn tại hoặc đã bị xóa."
    ),
    (
        r"Unsupported URL|is not a valid URL",
        "Đường dẫn URL không được hỗ trợ hoặc định dạng link không hợp lệ."
    ),
    (
        r"Incomplete read|Connection reset|timed out",
        "Mạng gián đoạn hoặc mất kết nối tới máy chủ video trong lúc tải. Hãy kiểm tra kết nối mạng và bấm 'Thử Lại'."
    ),
    (
        r"Requested format is not available",
        "Định dạng hoặc chất lượng bạn chọn không có sẵn cho video này. Hãy chọn 'Cao Nhất Tự Động (Best Quality)'."
    ),
]


def translate_error(raw_error: str, module_id: str = "") -> str:
    """
    Phân tích chuỗi lỗi thô và trả về thông báo lỗi tiếng Việt dễ hiểu.
    Nếu không khớp mẫu nào, trả về câu thông báo mặc định kèm nguyên nhân tóm tắt.
    """
    if not raw_error or not raw_error.strip():
        return "Đã xảy ra lỗi không xác định."

    clean_err = raw_error.strip()

    # 1. Kiểm tra mẫu lỗi yt-dlp
    if module_id.lower() == "downloader" or "yt_dlp" in clean_err.lower() or "youtube" in clean_err.lower():
        for pattern, vn_msg in YTDLP_ERROR_PATTERNS:
            if re.search(pattern, clean_err, re.IGNORECASE):
                return vn_msg

    # 2. Kiểm tra mẫu lỗi FFmpeg
    for pattern, vn_msg in FFMPEG_ERROR_PATTERNS:
        if re.search(pattern, clean_err, re.IGNORECASE):
            return vn_msg

    # 3. Kiểm tra tiếp yt-dlp nếu chưa khớp
    for pattern, vn_msg in YTDLP_ERROR_PATTERNS:
        if re.search(pattern, clean_err, re.IGNORECASE):
            return vn_msg

    # Tóm lược ngắn gọn nếu quá dài
    first_line = clean_err.split("\n")[0]
    if len(first_line) > 120:
        first_line = first_line[:117] + "..."

    return f"Lỗi xử lý: {first_line}. Bạn có thể bấm 'Sao chép log' để xem chi tiết."
