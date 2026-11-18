"""
Power & Notification Manager Core Module
Điều khiển nguồn điện máy tính (Tắt máy, Ngủ) và phát âm thanh thông báo.
Hỗ trợ hủy lệnh tắt máy khi người dùng bấm Hủy.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import sys
import subprocess
from core.logger import get_logger


def play_completion_sound():
    """Phát âm thanh thông báo hoàn thành tác vụ trên Windows/Linux."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return
        except Exception:
            pass
    # Fallback ký tự chuông
    print("\a", end="", flush=True)


def shutdown_computer(delay_seconds: int = 60) -> bool:
    """
    Đặt lịch tắt máy tính Windows sau delay_seconds (mặc định 60 giây).
    Hiển thị thông báo đếm ngược của Windows để người dùng có thể can thiệp.
    """
    logger = get_logger()
    logger.warning(f"Đang kích hoạt lệnh tắt máy tính sau {delay_seconds} giây...")
    if sys.platform == "win32":
        try:
            msg = f"MediaStudio Pro đã hoàn tất toàn bộ hàng đợi tác vụ. Máy tính sẽ tắt sau {delay_seconds} giây."
            cmd = ["shutdown.exe", "/s", "/t", str(delay_seconds), "/c", msg]
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thực thi shutdown.exe: {e}")
            return False
    return False


def cancel_shutdown() -> bool:
    """Hủy lệnh tắt máy tính đang đếm ngược."""
    logger = get_logger()
    if sys.platform == "win32":
        try:
            cmd = ["shutdown.exe", "/a"]
            subprocess.run(cmd, check=True)
            logger.info("Đã hủy lệnh tắt máy tính thành công.")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi hủy lệnh tắt máy: {e}")
            return False
    return False


def sleep_computer() -> bool:
    """Đưa máy tính vào chế độ Ngủ (Sleep/Suspend)."""
    logger = get_logger()
    logger.info("Đang đưa máy tính vào chế độ Ngủ (Sleep)...")
    if sys.platform == "win32":
        try:
            # Gọi API Windows chuyển sang Sleep
            cmd = ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
            subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đưa máy vào chế độ ngủ: {e}")
            return False
    return False
