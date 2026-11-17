"""
Single Instance Checker
Đảm bảo chỉ có một phiên bản MediaStudio chạy tại một thời điểm trên máy tính,
tránh xung đột ghi file cấu hình, SQLite database và tài nguyên GPU.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import sys
import os
from pathlib import Path
from core.system import get_appdata_dir
from core.logger import get_logger

_lock_file_handle = None


def acquire_single_instance_lock() -> bool:
    """
    Cố gắng chiếm quyền khóa độc quyền trên file app.lock.
    Trả về True nếu ứng dụng là phiên bản duy nhất đang chạy.
    Trả về False nếu đã có phiên bản khác đang chạy.
    """
    global _lock_file_handle
    lock_path = get_appdata_dir() / "app.lock"

    try:
        _lock_file_handle = open(lock_path, "w")
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

        _lock_file_handle.write(str(os.getpid()))
        _lock_file_handle.flush()
        return True
    except (IOError, OSError):
        get_logger().warning("Phát hiện một phiên bản MediaStudio khác đang chạy. Ngăn chặn khởi động trùng lặp.")
        return False


def release_single_instance_lock():
    """Giải phóng file lock khi ứng dụng thoát."""
    global _lock_file_handle
    if _lock_file_handle:
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(_lock_file_handle, fcntl.LOCK_UN)
            _lock_file_handle.close()
        except Exception:
            pass
        _lock_file_handle = None

