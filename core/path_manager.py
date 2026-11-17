"""
Path Manager Module
Quản lý các đường dẫn tài nguyên, thư mục dữ liệu, và định vị công cụ FFmpeg/FFprobe.
Tương thích hoàn toàn khi chạy từ source code Python hoặc khi đã đóng gói thành file .exe (PyInstaller).
"""

import os
import sys
import shutil
from pathlib import Path


class PathManager:
    _app_dir = None
    _user_data_dir = None
    _temp_dir = None
    _cached_ffmpeg = None
    _cached_ffprobe = None

    @classmethod
    def get_app_dir(cls) -> Path:
        """
        Lấy đường dẫn thư mục gốc của ứng dụng.
        Hỗ trợ cả môi trường dev và PyInstaller frozen (_MEIPASS).
        """
        if cls._app_dir is None:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Ứng dụng đang chạy từ file .exe được đóng gói bởi PyInstaller
                cls._app_dir = Path(sys._MEIPASS)
            else:
                # Ứng dụng đang chạy từ file nguồn Python
                cls._app_dir = Path(__file__).resolve().parent.parent
        return cls._app_dir

    @classmethod
    def get_executable_dir(cls) -> Path:
        """
        Lấy thư mục chứa file thực thi (.exe) thực sự trên ổ cứng.
        Khác với _MEIPASS (vốn là thư mục tạm của PyInstaller).
        """
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
        return cls.get_app_dir()

    @classmethod
    def get_user_data_dir(cls) -> Path:
        """
        Lấy thư mục dữ liệu người dùng tại %APPDATA%/MediaStudioPro
        Đảm bảo không cần quyền Administrator để ghi file.
        """
        if cls._user_data_dir is None:
            appdata = os.environ.get('APPDATA')
            if appdata:
                base_dir = Path(appdata) / "MediaStudioPro"
            else:
                # Dự phòng nếu không tìm thấy APPDATA
                base_dir = Path.home() / ".mediastudiopro"
            base_dir.mkdir(parents=True, exist_ok=True)
            cls._user_data_dir = base_dir
        return cls._user_data_dir

    @classmethod
    def get_temp_dir(cls) -> Path:
        """Lấy thư mục lưu trữ file tạm."""
        if cls._temp_dir is None:
            temp_path = cls.get_user_data_dir() / "temp"
            temp_path.mkdir(parents=True, exist_ok=True)
            cls._temp_dir = temp_path
        return cls._temp_dir

    @classmethod
    def get_logs_dir(cls) -> Path:
        """Lấy thư mục lưu trữ file log."""
        logs_path = cls.get_user_data_dir() / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """
        Định vị file thực thi ffmpeg.exe:
        1. Ưu tiên thư mục bin/ bên trong gói ứng dụng (_MEIPASS/bin hoặc app_dir/bin)
        2. Thư mục cùng cấp với file .exe (nếu người dùng copy ffmpeg.exe để cạnh app)
        3. Trong biến môi trường PATH của Windows
        """
        if cls._cached_ffmpeg and os.path.exists(cls._cached_ffmpeg):
            return cls._cached_ffmpeg

        exe_name = "ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg"
        
        # 1. Kiểm tra trong bundle/bin
        bundled_bin = cls.get_app_dir() / "bin" / exe_name
        if bundled_bin.exists():
            cls._cached_ffmpeg = str(bundled_bin)
            return cls._cached_ffmpeg

        # 2. Kiểm tra cùng cấp file .exe
        local_bin = cls.get_executable_dir() / exe_name
        if local_bin.exists():
            cls._cached_ffmpeg = str(local_bin)
            return cls._cached_ffmpeg

        # 3. Kiểm tra biến môi trường PATH
        which_path = shutil.which("ffmpeg")
        if which_path:
            cls._cached_ffmpeg = which_path
            return cls._cached_ffmpeg

        # Mặc định trả về "ffmpeg" để hệ thống tự tìm
        return "ffmpeg"

    @classmethod
    def get_ffprobe_path(cls) -> str:
        """
        Định vị file thực thi ffprobe.exe tương tự như ffmpeg.
        """
        if cls._cached_ffprobe and os.path.exists(cls._cached_ffprobe):
            return cls._cached_ffprobe

        exe_name = "ffprobe.exe" if sys.platform.startswith("win") else "ffprobe"

        bundled_bin = cls.get_app_dir() / "bin" / exe_name
        if bundled_bin.exists():
            cls._cached_ffprobe = str(bundled_bin)
            return cls._cached_ffprobe

        local_bin = cls.get_executable_dir() / exe_name
        if local_bin.exists():
            cls._cached_ffprobe = str(local_bin)
            return cls._cached_ffprobe

        which_path = shutil.which("ffprobe")
        if which_path:
            cls._cached_ffprobe = which_path
            return cls._cached_ffprobe

        return "ffprobe"

    @classmethod
    def get_asset_path(cls, relative_path: str) -> str:
        """Lấy đường dẫn tuyệt đối của file tài nguyên (icon, style, image)."""
        return str(cls.get_app_dir() / relative_path)

