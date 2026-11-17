"""
Main Window Shell
Khung cửa sổ chính của All-in-One Media Studio:
- Sidebar tự động nạp các BaseModule
- Workspace điều hướng mượt mà
- Panel hàng đợi Job Queue + Khung Log Console tích hợp
- Hỗ trợ Kéo & Thả (Drag & Drop) file/thư mục
- Thông báo âm thanh / Tự động tắt máy khi hoàn tất hàng đợi.
"""

import os
import sys
import subprocess
from typing import List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QTabWidget, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from modules.base_module import BaseModule
from ui.components.sidebar import Sidebar
from ui.components.job_queue_panel import JobQueuePanel
from ui.components.log_console import LogConsole
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.bridge import JobQueueBridge
from core.config import ConfigManager
from core.logger import get_logger


class MainWindow(QMainWindow):
    def __init__(self, modules: List[BaseModule], bridge: JobQueueBridge):
        super().__init__()
        self.modules = modules
        self.bridge = bridge
        self.config_mgr = ConfigManager.get_instance()

        self.setWindowTitle("All-in-One Media Studio")
        self.resize(1150, 760)
        self.setMinimumSize(980, 640)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar bên trái
        self.sidebar = Sidebar(self.modules)
        main_layout.addWidget(self.sidebar)

        # 2. Vùng làm việc chính bên phải
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Workspace Stacked Widget chứa các Module Views
        self.workspace = QStackedWidget()
        self.workspace.setObjectName("Workspace")

        for mod in self.modules:
            view_widget = mod.create_widget(self.workspace, self.bridge)
            self.workspace.addWidget(view_widget)

        right_layout.addWidget(self.workspace, 3)

        # 3. Bottom Container: Tabs giữa Job Queue và Log Console
        bottom_tabs = QTabWidget()
        bottom_tabs.setObjectName("BottomPanel")
        bottom_tabs.setStyleSheet("""
            QTabWidget::pane { border-top: 1px solid #23272F; background: #0E1013; }
            QTabBar::tab { background: #121418; color: #94A3B8; padding: 6px 16px; font-size: 11px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #181B20; color: #FFFFFF; border-top: 2px solid #6366F1; }
        """)

        self.queue_panel = JobQueuePanel(self.bridge)
        self.log_console = LogConsole()

        bottom_tabs.addTab(self.queue_panel, "⚡ Hàng Đợi Tác Vụ")
        bottom_tabs.addTab(self.log_console, "📋 Nhật Ký Hệ Thống")

        right_layout.addWidget(bottom_tabs, 2)
        main_layout.addWidget(right_container, 1)

    def _connect_signals(self):
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.sidebar.open_settings.connect(self._open_settings)
        self.sidebar.open_about.connect(self._open_about)

        # Cầu nối Queue log vào console
        self.bridge.job_log.connect(lambda job, line: self.log_console.append_log(f"[{job.name}] {line}"))
        self.bridge.all_jobs_finished.connect(self._on_all_jobs_finished)

    def _on_page_changed(self, index: int):
        self.workspace.setCurrentIndex(index)
        if index < len(self.modules):
            self.log_console.append_log(f"Chuyển sang module: {self.modules[index].display_name}", "INFO")

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            # Cập nhật số luồng chạy song song trong queue
            new_max = self.config_mgr.get("max_concurrent_jobs", 2)
            self.bridge.queue_manager.set_max_concurrent(new_max)
            self.log_console.append_log(f"Đã cập nhật cài đặt (Max jobs song song: {new_max})", "SUCCESS")

    def _open_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    @Slot()
    def _on_all_jobs_finished(self):
        self.log_console.append_log("TẤT CẢ TÁC VỤ TRONG HÀNG ĐỢI ĐÃ HOÀN TẤT!", "SUCCESS")

        # Âm thanh thông báo
        if self.config_mgr.get("play_sound_when_finished", True):
            QApplication.beep()

        # Kiểm tra tùy chọn tắt máy
        if self.config_mgr.get("shutdown_when_finished", False):
            self.log_console.append_log("Đang kích hoạt hẹn giờ tắt máy tính trong 60 giây...", "WARNING")
            if sys.platform == "win32":
                subprocess.run(["shutdown", "/s", "/t", "60"])

    # Xử lý Kéo & Thả (Drag & Drop)
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if file_paths:
            self.log_console.append_log(f"Nhận file kéo thả: {', '.join(os.path.basename(f) for f in file_paths[:3])}", "INFO")
