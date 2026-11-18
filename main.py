"""
All-in-One Media Studio - Main Entry Point
Khởi động ứng dụng, nạp theme Dark Mode, đăng ký các module Plugin và khởi chạy giao diện.
"""

import sys
import os
from pathlib import Path

# Đảm bảo đường dẫn gốc nằm trong sys.path
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.logger import setup_logger, setup_crash_handler
from core.single_instance import acquire_single_instance_lock, release_single_instance_lock
from core.config import ConfigManager
from core.job_queue.queue_manager import QueueManager
from ui.bridge import JobQueueBridge
from ui.main_window import MainWindow
from ui.theme import ThemeManager

# Các module plugin
from modules.converter_module import ConverterModule
from modules.downloader_module import DownloaderModule
from modules.merger_module import MergerModule
from modules.cutter_module import CutterModule


def load_stylesheet(app: QApplication):
    """Nạp stylesheet Dark Mode từ file assets/style.qss."""
    style_path = APP_DIR / "assets" / "style.qss"
    if style_path.exists():
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Cảnh báo: Không thể nạp stylesheet: {e}")


def main():
    # 1. Gắn Crash Handler toàn cục
    setup_crash_handler()

    # 2. Khởi tạo Logger
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info("Khởi động All-in-One Media Studio (Phase 0 Architecture)")
    logger.info("=" * 60)

    # 3. Kiểm tra Single Instance (chỉ 1 app chạy tại 1 thời điểm)
    if not acquire_single_instance_lock():
        print("Cảnh báo: Một phiên bản MediaStudio khác đang chạy. Ứng dụng sẽ đóng.")
        sys.exit(0)

    config_mgr = ConfigManager.get_instance()
    max_concurrent = config_mgr.get("max_concurrent_jobs", 2)

    # 2. Khởi tạo Job Queue & Bridge
    queue_mgr = QueueManager.get_instance(max_concurrent=max_concurrent)

    # 3. Đăng ký danh sách các Module
    modules = [
        ConverterModule(),   # Phase 1: Module 4
        DownloaderModule(),  # Phase 2: Module 1
        MergerModule(),      # Phase 3: Module 3
        CutterModule(),      # Phase 4: Module 2
    ]

    for mod in modules:
        queue_mgr.register_executor(mod.module_id, mod.execute_job)

    bridge = JobQueueBridge(queue_mgr)

    # 4. Khởi tạo Qt Application với High-DPI Scaling chuẩn
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("All-in-One Media Studio")
    app.setOrganizationName("MediaStudio")

    # Khởi tạo ThemeManager (Sáng / Tối / Theo hệ thống)
    ThemeManager.get_instance().init_app(app)

    # 5. Khởi chạy Cửa sổ Chính
    window = MainWindow(modules, bridge)
    window.show()

    exit_code = app.exec()
    release_single_instance_lock()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
