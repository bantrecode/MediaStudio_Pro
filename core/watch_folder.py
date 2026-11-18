"""
Watch Folder Core Module
Tự động theo dõi một thư mục được chỉ định:
- Khi người dùng thả file video/audio vào thư mục theo dõi, tự động nhận diện
- Kiểm tra tính ổn định của file (đảm bảo file đã copy xong hoàn chỉnh)
- Tự động tạo Job theo preset đã chọn và đưa vào QueueManager.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Set, Callable, Dict, Any
from core.job_queue.job_model import Job
from core.job_queue.queue_manager import QueueManager
from core.logger import get_logger
from core.config import ConfigManager

SUPPORTED_MEDIA_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm",
    ".ts", ".m4v", ".mp3", ".wav", ".aac", ".m4a", ".flac"
}


class WatchFolderService:
    _instance: Optional["WatchFolderService"] = None

    def __init__(self):
        self.config_mgr = ConfigManager.get_instance()
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._processed_files: Set[str] = set()
        self._file_sizes: Dict[str, int] = {}
        self._lock = threading.Lock()
        self.on_file_detected: Optional[Callable[[str, str], None]] = None  # (file_path, preset)

    @classmethod
    def get_instance(cls) -> "WatchFolderService":
        if cls._instance is None:
            cls._instance = WatchFolderService()
        return cls._instance

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        """Khởi động tiến trình theo dõi thư mục."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._thread.start()
            get_logger().info("Đã khởi chạy dịch vụ Watch Folder.")

    def stop(self):
        """Dừng dịch vụ theo dõi thư mục."""
        with self._lock:
            self._is_running = False
            self._thread = None
            get_logger().info("Đã dừng dịch vụ Watch Folder.")

    def _is_file_ready(self, file_path: Path) -> bool:
        """
        Kiểm tra xem file đã được ghi hoàn tất vào đĩa chưa (tránh trường hợp đang copy dở).
        1. Kích thước file không thay đổi sau 2 chu kỳ kiểm tra
        2. Mở file ở chế độ độc quyền không ném ngoại lệ PermissionError
        """
        str_path = str(file_path)
        try:
            current_size = file_path.stat().st_size
            if current_size == 0:
                return False

            prev_size = self._file_sizes.get(str_path)
            self._file_sizes[str_path] = current_size

            if prev_size is None or prev_size != current_size:
                return False

            # Kiểm tra mở file
            with open(str_path, "rb"):
                pass
            return True
        except (PermissionError, OSError):
            return False

    def _watch_loop(self):
        """Vòng lặp ngầm quét thư mục định kỳ."""
        logger = get_logger()
        while self._is_running:
            try:
                watch_dir_str = self.config_mgr.get("watch_folder_path", "")
                enabled = self.config_mgr.get("watch_folder_enabled", False)

                if enabled and watch_dir_str:
                    watch_dir = Path(watch_dir_str)
                    if watch_dir.exists() and watch_dir.is_dir():
                        for entry in watch_dir.iterdir():
                            if not self._is_running:
                                break
                            if entry.is_file() and entry.suffix.lower() in SUPPORTED_MEDIA_EXTS:
                                abs_str = str(entry.resolve())
                                if abs_str in self._processed_files:
                                    continue

                                if self._is_file_ready(entry):
                                    self._process_detected_file(entry)
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp Watch Folder: {e}")

            time.sleep(2.0)

    def _process_detected_file(self, file_path: Path):
        """Tạo tác vụ chuyển đổi tự động khi phát hiện file mới."""
        logger = get_logger()
        abs_str = str(file_path.resolve())
        self._processed_files.add(abs_str)

        preset = self.config_mgr.get("watch_folder_preset", "mp4_h264")
        output_dir = self.config_mgr.get(
            "watch_folder_output",
            self.config_mgr.get("default_output_dir", str(Path.home() / "Downloads"))
        )
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"[WatchFolder] Phát hiện file mới: {file_path.name} -> Áp dụng preset '{preset}'")

        # Cấu hình params theo preset
        params: Dict[str, Any] = {
            "input_file": abs_str,
            "output_dir": output_dir,
            "gpu_mode": self.config_mgr.get("gpu_preference", "auto"),
        }

        if preset == "mp3_extract":
            params.update({
                "mode": "audio_extract",
                "format": "mp3",
                "codec": "libmp3lame",
                "audio_bitrate": "192k",
            })
            job_name = f"[WatchFolder] Trích MP3: {file_path.name}"
        elif preset == "remux":
            params.update({
                "mode": "remux",
                "format": "mp4",
            })
            job_name = f"[WatchFolder] Remux MP4: {file_path.name}"
        elif preset == "social_zalo":
            params.update({
                "mode": "preset",
                "preset_id": "zalo_hd",
                "format": "mp4",
                "codec": "h264",
            })
            job_name = f"[WatchFolder] Nén Zalo: {file_path.name}"
        else:  # Mặc định mp4_h264
            params.update({
                "mode": "reencode",
                "format": "mp4",
                "codec": "h264",
                "resolution": "original",
                "crf": 23,
            })
            job_name = f"[WatchFolder] Chuyển đổi MP4: {file_path.name}"

        job = Job(
            module_id="converter",
            name=job_name,
            params=params
        )

        QueueManager.get_instance().submit(job)

        if self.on_file_detected:
            try:
                self.on_file_detected(abs_str, preset)
            except Exception:
                pass
