"""
Internationalization (i18n) Core Module
Quản lý đa ngôn ngữ (Tiếng Việt / English), cung cấp từ điển dịch thuật,
hàm tr() dùng chung cho toàn bộ ứng dụng và hỗ trợ gắn QTranslator.
TUYỆT ĐỐI KHÔNG BẮT BUỘC IMPORT PYSIDE6 Ở TẦNG CORE (Lazy import khi dùng với Qt).
"""

from typing import Dict, Optional

# Từ điển ánh xạ chuỗi giao diện (Context-aware translations)
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # Menu & Sidebar
    "Converter": {"vi": "Chuyển Đổi Định Dạng", "en": "Media Converter"},
    "Downloader": {"vi": "Tải Video Đa Nền Tảng", "en": "Video Downloader"},
    "Merger": {"vi": "Ghép Nối Video", "en": "Video Merger"},
    "Cutter": {"vi": "Cắt & Tách Phân Đoạn", "en": "Video Cutter"},
    "Settings": {"vi": "Cài Đặt Hệ Thống", "en": "System Settings"},
    "Help": {"vi": "Hướng Dẫn Sử Dụng", "en": "User Guide"},
    "About": {"vi": "Giới Thiệu & Bản Quyền", "en": "About & License"},

    # Job Queue & Statuses
    "Job Queue": {"vi": "Hàng Đợi Tác Vụ", "en": "Job Queue"},
    "System Logs": {"vi": "Nhật Ký Hệ Thống", "en": "System Logs"},
    "PENDING": {"vi": "Đang chờ", "en": "Pending"},
    "RUNNING": {"vi": "Đang chạy", "en": "Running"},
    "PAUSED": {"vi": "Tạm dừng", "en": "Paused"},
    "COMPLETED": {"vi": "Hoàn thành", "en": "Completed"},
    "FAILED": {"vi": "Thất bại", "en": "Failed"},
    "CANCELLED": {"vi": "Đã hủy", "en": "Cancelled"},
    "Speed": {"vi": "Tốc độ", "en": "Speed"},
    "ETA": {"vi": "Còn lại", "en": "ETA"},
    "Remaining Time": {"vi": "Thời gian còn lại", "en": "Remaining Time"},
    "Est. Size": {"vi": "Dung lượng ước tính", "en": "Estimated Size"},

    # Actions & Buttons
    "Start": {"vi": "Bắt Đầu", "en": "Start"},
    "Pause": {"vi": "Tạm Dừng", "en": "Pause"},
    "Resume": {"vi": "Tiếp Tục", "en": "Resume"},
    "Retry": {"vi": "Thử Lại", "en": "Retry"},
    "Cancel": {"vi": "Hủy Bỏ", "en": "Cancel"},
    "Clear Finished": {"vi": "Dọn Tác Vụ Xong", "en": "Clear Finished"},
    "Copy Log": {"vi": "Sao Chép Log", "en": "Copy Log"},
    "Save": {"vi": "Lưu Cài Đặt", "en": "Save Settings"},
    "Close": {"vi": "Đóng", "en": "Close"},
    "Browse": {"vi": "Chọn...", "en": "Browse..."},
    "Add Files": {"vi": "Thêm File", "en": "Add Files"},

    # Settings Tabs
    "General": {"vi": "Chung & Tác Vụ", "en": "General & Tasks"},
    "Appearance": {"vi": "Giao Diện", "en": "Appearance"},
    "Watch Folder": {"vi": "Thư Mục Theo Dõi", "en": "Watch Folder"},
    "Shortcuts": {"vi": "Phím Tắt", "en": "Shortcuts"},

    # Empty State & Hints
    "No files selected": {"vi": "Chưa có file nào được chọn", "en": "No files selected"},
    "Drop files here": {"vi": "Kéo thả file vào đây hoặc bấm nút bên dưới", "en": "Drag & drop files here or click below"},
}


class I18nManager:
    _instance: Optional["I18nManager"] = None

    def __init__(self):
        self._current_lang = "vi"  # Mặc định tiếng Việt

    @classmethod
    def get_instance(cls) -> "I18nManager":
        if cls._instance is None:
            cls._instance = I18nManager()
        return cls._instance

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang_code: str):
        if lang_code in ["vi", "en"]:
            self._current_lang = lang_code

    def translate(self, text: str, context: str = "") -> str:
        """Dịch văn bản sang ngôn ngữ đang kích hoạt."""
        key = text.strip()
        if key in TRANSLATIONS:
            lang_dict = TRANSLATIONS[key]
            return lang_dict.get(self._current_lang, text)
        return text


def tr(text: str, context: str = "") -> str:
    """Hàm toàn cục dịch chuỗi giao diện nhanh."""
    return I18nManager.get_instance().translate(text, context)
