"""
Logger Core Module
Ghi log ứng dụng xoay vòng (RotatingFileHandler) vào %APPDATA%\\MediaStudio\\logs\\app.log.
Hỗ trợ chức năng 'Xuất log để báo lỗi' ra file zip hoặc thư mục người dùng chọn.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import sys
import logging
import zipfile
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from core.system import get_logs_dir


_logger: Optional[logging.Logger] = None


def setup_logger() -> logging.Logger:
    """Khởi tạo logger ứng dụng chuẩn mực."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("MediaStudio")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Định dạng log
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Rotating File Handler (5 MB mỗi file, giữ lại 3 backup)
    log_file = get_logs_dir() / "app.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _logger = logger
    return _logger


def get_logger() -> logging.Logger:
    """Lấy thể hiện của logger."""
    if _logger is None:
        return setup_logger()
    return _logger


def setup_crash_handler():
    """Gắn móc sys.excepthook để bắt toàn bộ crash/unhandled exceptions và ghi vào log."""
    logger = get_logger()

    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "CRITICAL APP CRASH (Unhandled Exception):",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_unhandled_exception


def export_logs(dest_zip_path: str) -> bool:
    """
    Xuất toàn bộ file log thành 1 file ZIP để người dùng gửi báo lỗi.
    dest_zip_path: Đường dẫn file .zip đầu ra (vd: C:\\Users\\...\\Desktop\\mediastudio_logs.zip)
    """
    logs_dir = get_logs_dir()
    try:
        dest_p = Path(dest_zip_path)
        dest_p.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(dest_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for log_file in logs_dir.glob("*.log*"):
                if log_file.is_file():
                    zipf.write(log_file, arcname=log_file.name)
        return True
    except Exception as e:
        get_logger().error(f"Lỗi khi xuất log ra ZIP: {e}")
        return False

