"""
System Core Module
Chứa các tiện ích cấp hệ thống:
- resource_path() tương thích cả dev mode và PyInstaller frozen (_MEIPASS)
- Cờ CREATE_NO_WINDOW chống nháy console Windows
- Quản lý đường dẫn độc lập (%APPDATA%\\MediaStudio\\)
- Tìm kiếm binary ưu tiên: %APPDATA%\\MediaStudio\\bin\\ -> assets/bin/ -> .exe dir -> PATH
- Xử lý CẢ CÂY TIẾN TRÌNH bằng psutil (kill, suspend, resume) chống tiến trình FFmpeg mồ côi
- Kiểm tra dung lượng ổ đĩa khả dụng
- Xử lý đường dẫn Unicode và tên file tiếng Việt
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
import sys
import shutil
import re
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import psutil

# Cờ chống nháy cửa sổ console trên Windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def get_subprocess_kwargs() -> Dict[str, Any]:
    """Trả về tham số an toàn khi gọi subprocess trên Windows."""
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


def get_app_root() -> Path:
    """Lấy thư mục gốc của ứng dụng (hỗ trợ cả dev và PyInstaller frozen)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resource_path(relative_path: str) -> Path:
    """
    Hàm định vị tài nguyên chuẩn:
    - Trong dev: Path(__file__).parent.parent / relative_path
    - Khi đóng gói PyInstaller: sys._MEIPASS / relative_path
    """
    return get_app_root() / relative_path


def get_appdata_dir() -> Path:
    """
    Lấy thư mục lưu trữ cấu hình, lịch sử và cache của ứng dụng:
    Mặc định: %APPDATA%\\MediaStudio\\
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        base_dir = Path(appdata) / "MediaStudio"
    else:
        base_dir = Path.home() / ".mediastudio"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_logs_dir() -> Path:
    """Thư mục lưu trữ log xoay vòng: %APPDATA%\\MediaStudio\\logs\\"""
    p = get_appdata_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_temp_dir() -> Path:
    """Thư mục file tạm an toàn: %APPDATA%\\MediaStudio\\temp\\"""
    p = get_appdata_dir() / "temp"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_custom_bin_dir() -> Path:
    """Thư mục chứa các nhị phân cập nhật động: %APPDATA%\\MediaStudio\\bin\\"""
    p = get_appdata_dir() / "bin"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_binary_path(binary_name: str) -> str:
    """
    Tìm kiếm đường dẫn thực thi của binary (ffmpeg, ffprobe, yt-dlp):
    1. Ưu tiên trong thư mục cập nhật động %APPDATA%\\MediaStudio\\bin\\
    2. Thư mục đóng gói kèm assets/bin/ (sử dụng resource_path)
    3. Thư mục cùng cấp với file .exe đang chạy
    4. Trong biến môi trường PATH hệ thống
    """
    exe_name = f"{binary_name}.exe" if sys.platform == "win32" else binary_name

    # 1. Kiểm tra trong %APPDATA%\MediaStudio\bin\ (bản cập nhật mới nhất)
    appdata_bin = get_custom_bin_dir() / exe_name
    if appdata_bin.exists():
        return str(appdata_bin)

    # 2. Kiểm tra trong assets/bin/ thông qua resource_path()
    bundled_bin = resource_path("assets/bin") / exe_name
    if bundled_bin.exists():
        return str(bundled_bin)

    # 3. Kiểm tra cùng cấp file thực thi
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidate = exe_dir / exe_name
        if candidate.exists():
            return str(candidate)

    # 4. PATH hệ thống
    which_path = shutil.which(binary_name)
    if which_path:
        return which_path

    return binary_name


def kill_process_tree(pid: int):
    """
    Tiêu diệt CẢ CÂY TIẾN TRÌNH con sử dụng psutil để không để lại
    bất kỳ tiến trình FFmpeg / yt-dlp mồ côi (zombie/orphan) nào.
    """
    try:
        from core.logger import get_logger
        logger = get_logger()
    except Exception:
        logger = None

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        parent.kill()
        if logger:
            logger.info(f"Đã tiêu diệt sạch cây tiến trình PID {pid} và {len(children)} tiến trình con.")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    except Exception as e:
        if logger:
            logger.warning(f"Lỗi khi kill_process_tree({pid}): {e}")


def suspend_process_tree(pid: int):
    """Tạm dừng (Pause/Suspend) cả cây tiến trình."""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.suspend()
            except Exception:
                pass
        parent.suspend()
    except Exception:
        pass


def resume_process_tree(pid: int):
    """Tiếp tục (Resume) cả cây tiến trình."""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.resume()
            except Exception:
                pass
        parent.resume()
    except Exception:
        pass
    except Exception as e:
        get_logger().warning(f"Lỗi khi resume_process_tree({pid}): {e}")


def check_disk_space(target_path: str, required_bytes: int = 100 * 1024 * 1024) -> Tuple[bool, int, int]:
    """
    Kiểm tra dung lượng ổ đĩa khả dụng trước khi thực thi tác vụ.
    Trả về: (has_enough: bool, free_bytes: int, total_bytes: int)
    """
    p = Path(target_path).resolve()
    while not p.exists() and p.parent != p:
        p = p.parent

    try:
        usage = shutil.disk_usage(str(p))
        has_enough = usage.free >= required_bytes
        return has_enough, usage.free, usage.total
    except Exception:
        return True, 0, 0


def format_bytes(num_bytes: int) -> str:
    """Định dạng byte thành chuỗi dễ đọc (KB, MB, GB, TB)."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def clean_unicode_filename(filename: str) -> str:
    """
    Chuẩn hóa tên file:
    - Chuyển ký tự tiếng Việt có dấu thành không dấu
    - Thay thế các ký tự cấm trên Windows bằng dấu gạch dưới
    - Giới hạn độ dài để không chạm trần 255 ký tự Windows Path.
    """
    vietnamese_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
    }

    clean = filename
    for vi_char, lat_char in vietnamese_map.items():
        clean = clean.replace(vi_char, lat_char)
        clean = clean.replace(vi_char.upper(), lat_char.upper())

    clean = re.sub(r'[\\/*?:"<>|]', "_", clean)
    clean = clean.replace(" ", "_")
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '', clean)

    if len(clean) > 180:
        clean = clean[:177] + "..."
    return clean or "media_file"
