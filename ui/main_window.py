"""
Main Window Shell
Khung cửa sổ chính của All-in-One Media Studio:
- Sidebar tự động nạp các BaseModule, có thể thu gọn (220px <-> 64px)
- Workspace điều hướng mượt mà
- QSplitter dọc giữa Workspace và BottomPanel (mặc định 80:20, lưu/khôi phục QSettings)
- Tự động mở panel Hàng đợi khi có job mới được thêm
- Tự động thu gọn Sidebar khi cửa sổ < 1100px
- Kéo-thả thông minh (Smart Drag & Drop Routing) giữa các tab
- Thông báo âm thanh / Tự động tắt máy khi hoàn tất hàng đợi.
"""

import os
import sys
import subprocess
import threading
from pathlib import Path
from typing import List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QTabWidget, QMessageBox, QApplication, QSplitter, QPushButton,
    QSystemTrayIcon
)
from PySide6.QtCore import Qt, Slot, QSettings, QByteArray
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from modules.base_module import BaseModule
from ui.components.sidebar import Sidebar
from ui.components.job_queue_panel import JobQueuePanel
from ui.components.log_console import LogConsole
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.help_dialog import HelpDialog
from ui.bridge import JobQueueBridge
from ui.theme import ThemeManager
from core.config import ConfigManager
from core.logger import get_logger
from core.power_manager import play_completion_sound, shutdown_computer, cancel_shutdown, sleep_computer
from core.watch_folder import WatchFolderService
from core.ytdlp_runner import YtDlpRunner

MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".ts", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma"}


class MainWindow(QMainWindow):
    def __init__(self, modules: List[BaseModule], bridge: JobQueueBridge):
        super().__init__()
        self.modules = modules
        self.bridge = bridge
        self.config_mgr = ConfigManager.get_instance()
        self.settings = QSettings("MediaStudio", "MediaStudioPro")

        self.setWindowTitle("All-in-One Media Studio")
        self.resize(1150, 760)
        self.setMinimumSize(980, 640)
        self.setAcceptDrops(True)

        # Khởi tạo System Tray Icon cho Toast Notification
        self.tray_icon = QSystemTrayIcon(self)
        try:
            self.tray_icon.setIcon(ThemeManager.get_instance().get_svg_icon("converter", size=24))
            self.tray_icon.show()
        except Exception:
            pass

        self._setup_ui()
        self._connect_signals()

        # 1. Khôi phục hàng đợi bền vững từ SQLite
        self.bridge.queue_manager.load_persisted_jobs()

        # 2. Khởi động Watch Folder nếu được kích hoạt
        if self.config_mgr.get("watch_folder_enabled", False):
            WatchFolderService.get_instance().start()

        # 3. Tự động kiểm tra cập nhật yt-dlp ở chế độ nền
        if self.config_mgr.get("auto_check_ytdlp_update", True):
            threading.Thread(target=self._check_ytdlp_startup, daemon=True).start()

    def _check_ytdlp_startup(self):
        try:
            ok, tag, _ = YtDlpRunner.check_latest_version()
            if ok and tag:
                self.log_console.append_log(f"Kiểm tra yt-dlp: Phiên bản mới nhất trên GitHub là {tag}", "INFO")
        except Exception:
            pass

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar bên trái (có thể thu gọn)
        self.sidebar = Sidebar(self.modules)
        main_layout.addWidget(self.sidebar)

        # 2. Vùng làm việc chính bên phải với QSplitter co giãn
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # QSplitter dọc giữa Workspace (80%) và BottomPanel (20%)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setObjectName("MainSplitter")
        self.splitter.setChildrenCollapsible(True)

        # Workspace Stacked Widget chứa các Module Views
        self.workspace = QStackedWidget()
        self.workspace.setObjectName("Workspace")

        self.view_widgets = []
        for mod in self.modules:
            view_widget = mod.create_widget(self.workspace, self.bridge)
            self.workspace.addWidget(view_widget)
            self.view_widgets.append(view_widget)

        self.splitter.addWidget(self.workspace)

        # 3. Bottom Container: Tabs giữa Job Queue và Log Console
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setObjectName("BottomPanel")

        self.queue_panel = JobQueuePanel(self.bridge)
        self.log_console = LogConsole()

        self.bottom_tabs.addTab(self.queue_panel, "⚡ Hàng Đợi Tác Vụ")
        self.bottom_tabs.addTab(self.log_console, "📋 Nhật Ký Hệ Thống")

        # Nút thu gọn / mở rộng nhanh góc phải TabBar
        self.btn_toggle_bottom = QPushButton("🔽 Ẩn Hàng Đợi")
        self.btn_toggle_bottom.setObjectName("BtnToggleBottom")
        self.btn_toggle_bottom.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_bottom.setToolTip("Thu gọn hoặc mở rộng panel Hàng đợi / Nhật ký")
        self.btn_toggle_bottom.clicked.connect(self._toggle_bottom_panel)
        self.bottom_tabs.setCornerWidget(self.btn_toggle_bottom, Qt.TopRightCorner)

        self.splitter.addWidget(self.bottom_tabs)

        # Thiết lập tỉ lệ co dãn mặc định 80:20 và khôi phục từ QSettings
        self.splitter.setStretchFactor(0, 8)
        self.splitter.setStretchFactor(1, 2)
        self._saved_bottom_size = 180

        saved_state = self.settings.value("main_splitter_state")
        if saved_state:
            self.splitter.restoreState(saved_state)
        else:
            # Mặc định 80% trên, 20% dưới
            self.splitter.setSizes([590, 150])

        # Khôi phục trạng thái ẩn nếu lần trước người dùng đã ẩn panel
        was_collapsed = self.settings.value("bottom_panel_collapsed", False, type=bool)
        if was_collapsed:
            self._collapse_bottom_panel(save=False)

        right_layout.addWidget(self.splitter)
        main_layout.addWidget(right_container, 1)

    def _is_bottom_collapsed(self) -> bool:
        sizes = self.splitter.sizes()
        return len(sizes) >= 2 and sizes[1] <= 35

    def _collapse_bottom_panel(self, save: bool = True):
        sizes = self.splitter.sizes()
        if len(sizes) >= 2 and sizes[1] > 35:
            self._saved_bottom_size = sizes[1]
            self.splitter.setSizes([sizes[0] + sizes[1], 0])
            self.btn_toggle_bottom.setText("🔼 Hiện Hàng Đợi")
            if save:
                self.settings.setValue("bottom_panel_collapsed", True)

    def _expand_bottom_panel(self, save: bool = True):
        sizes = self.splitter.sizes()
        restore_h = getattr(self, "_saved_bottom_size", 170)
        if restore_h < 120:
            restore_h = 170
        total = sum(sizes) if sum(sizes) > 0 else 740
        self.splitter.setSizes([max(200, total - restore_h), restore_h])
        self.btn_toggle_bottom.setText("🔽 Ẩn Hàng Đợi")
        if save:
            self.settings.setValue("bottom_panel_collapsed", False)

    def _toggle_bottom_panel(self):
        if self._is_bottom_collapsed():
            self._expand_bottom_panel(save=True)
        else:
            self._collapse_bottom_panel(save=True)

    def _connect_signals(self):
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.sidebar.open_help.connect(self._open_help)
        self.sidebar.open_settings.connect(self._open_settings)
        self.sidebar.open_about.connect(self._open_about)

        # Cầu nối Queue log vào console
        self.bridge.job_log.connect(lambda job, line: self.log_console.append_log(f"[{job.name}] {line}"))
        self.bridge.all_jobs_finished.connect(self._on_all_jobs_finished)

        # Tự động mở bảng Hàng Đợi khi có job mới được thêm
        self.bridge.job_added.connect(self._on_job_added_auto_expand)

    @Slot(object)
    def _on_job_added_auto_expand(self, job):
        """Khi có job mới được thêm vào hàng đợi, tự động mở bảng nếu đang ẩn."""
        if self._is_bottom_collapsed():
            self._expand_bottom_panel(save=False)
        self.bottom_tabs.setCurrentIndex(0)

    def _on_page_changed(self, index: int):
        self.workspace.setCurrentIndex(index)
        if index < len(self.modules):
            self.log_console.append_log(f"Chuyển sang module: {self.modules[index].display_name}", "INFO")

    def _open_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            new_max = self.config_mgr.get("max_concurrent_jobs", 2)
            self.bridge.queue_manager.set_max_concurrent(new_max)
            self.log_console.append_log(f"Đã cập nhật cài đặt (Max jobs song song: {new_max})", "SUCCESS")

    def _open_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    @Slot()
    def _on_all_jobs_finished(self):
        self.log_console.append_log("TẤT CẢ TÁC VỤ TRONG HÀNG ĐỢI ĐÃ HOÀN TẤT!", "SUCCESS")

        # 1. Âm thanh thông báo
        if self.config_mgr.get("play_sound_when_finished", True):
            play_completion_sound()

        # 2. Thông báo Windows Toast Notification
        if self.config_mgr.get("toast_notification", True) and hasattr(self, "tray_icon"):
            try:
                self.tray_icon.showMessage(
                    "MediaStudio Pro",
                    "Tất cả tác vụ trong hàng đợi đã hoàn tất thành công!",
                    QSystemTrayIcon.Information,
                    4000
                )
            except Exception:
                pass

        # 3. Hành động khi hoàn thành (Tắt máy / Ngủ)
        act = self.config_mgr.get("action_when_finished", "none")
        if act == "shutdown" or self.config_mgr.get("shutdown_when_finished", False):
            self.log_console.append_log("Đang kích hoạt hẹn giờ tắt máy tính trong 60 giây...", "WARNING")
            shutdown_computer(60)
            ret = QMessageBox.warning(
                self, "Tự Động Tắt Máy",
                "Hàng đợi đã hoàn tất. Máy tính sẽ tắt sau 60 giây.\nBấm 'Cancel' để hủy tắt máy.",
                QMessageBox.Cancel | QMessageBox.Ok
            )
            if ret == QMessageBox.Cancel:
                cancel_shutdown()
                self.log_console.append_log("Đã hủy lệnh tắt máy tính.", "INFO")
        elif act == "sleep":
            self.log_console.append_log("Đang đưa máy tính vào chế độ Ngủ (Sleep)...", "WARNING")
            sleep_computer()

    def resizeEvent(self, event):
        """Tự động thu gọn Sidebar khi cửa sổ < 1100px để nhường chỗ cho Workspace."""
        super().resizeEvent(event)
        new_width = event.size().width()
        if new_width < 1100 and not self.sidebar.is_collapsed:
            self.sidebar.collapse(animate=True, auto=True)
        elif new_width >= 1100 and getattr(self.sidebar, "_auto_collapsed", False):
            self.sidebar.expand(animate=True)

    def closeEvent(self, event):
        """Lưu trạng thái Splitter và panel trước khi đóng ứng dụng."""
        self.settings.setValue("main_splitter_state", self.splitter.saveState())
        self.settings.setValue("bottom_panel_collapsed", self._is_bottom_collapsed())
        event.accept()

    # ==========================================
    # KÉO THẢ THÔNG MINH (Smart Drag & Drop Routing)
    # ==========================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        # 1. Kiểm tra text link URL
        text_data = event.mimeData().text().strip()
        urls_data = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        raw_urls = [u.toString() for u in event.mimeData().urls() if not u.isLocalFile()]

        # Nếu là đường link web (YouTube, TikTok, http...)
        link_target = None
        if text_data.startswith("http://") or text_data.startswith("https://"):
            link_target = text_data
        elif raw_urls and (raw_urls[0].startswith("http://") or raw_urls[0].startswith("https://")):
            link_target = raw_urls[0]

        if link_target:
            cur_idx = self.workspace.currentIndex()
            # Module Downloader thường ở index 1
            if cur_idx != 1:
                ret = QMessageBox.question(
                    self, "Chuyển Sang Tải Video?",
                    f"Bạn vừa kéo thả đường link video trực tuyến:\n{link_target}\n\nBạn có muốn chuyển sang tab 'Tải Video' không?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if ret == QMessageBox.Yes:
                    self.sidebar.set_active_page(1)
                    self.workspace.setCurrentIndex(1)
                    downloader_view = self.view_widgets[1]
                    if hasattr(downloader_view, "txt_url"):
                        downloader_view.txt_url.setText(link_target)
                        if hasattr(downloader_view, "_inspect_video"):
                            downloader_view._inspect_video()
            else:
                downloader_view = self.view_widgets[1]
                if hasattr(downloader_view, "txt_url"):
                    downloader_view.txt_url.setText(link_target)
                    if hasattr(downloader_view, "_inspect_video"):
                        downloader_view._inspect_video()
            return

        # 2. Xử lý file/thư mục cục bộ
        if not urls_data:
            return

        # Thu thập toàn bộ file
        all_files = []
        for p in urls_data:
            if os.path.isfile(p):
                all_files.append(p)
            elif os.path.isdir(p):
                for r, _, fs in os.walk(p):
                    for f in fs:
                        all_files.append(os.path.join(r, f))

        video_files = [f for f in all_files if Path(f).suffix.lower() in MEDIA_EXTENSIONS]
        audio_files = [f for f in all_files if Path(f).suffix.lower() in AUDIO_EXTENSIONS]

        cur_idx = self.workspace.currentIndex()
        cur_view = self.view_widgets[cur_idx]

        # Kịch bản A: Kéo thả nhiều video
        if len(video_files) > 1:
            if cur_idx == 3:  # Đang ở tab Cutter (chỉ xử lý 1 video)
                ret = QMessageBox.question(
                    self, "Gợi Ý Chuyển Tab",
                    f"Bạn vừa kéo thả {len(video_files)} video. Tab Cắt Video chỉ xử lý 1 video tại 1 thời điểm.\n"
                    "Bạn có muốn chuyển sang tab 'Ghép Video' để nối chúng không?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if ret == QMessageBox.Yes:
                    self.sidebar.set_active_page(2)
                    self.workspace.setCurrentIndex(2)
                    merger_view = self.view_widgets[2]
                    if hasattr(merger_view, "_queue_probe_files"):
                        merger_view._queue_probe_files(video_files)
                    return
                else:
                    # Chỉ lấy file đầu tiên vào Cutter
                    if hasattr(cur_view, "_load_video"):
                        cur_view._load_video(video_files[0])
                    return
            elif cur_idx == 1:  # Đang ở tab Downloader
                ret = QMessageBox.question(
                    self, "Gợi Ý Chuyển Tab",
                    f"Bạn vừa kéo thả {len(video_files)} video cục bộ vào tab Tải Video.\n"
                    "Bạn có muốn chuyển sang tab 'Chuyển Đổi' để nén/đổi định dạng hàng loạt không?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if ret == QMessageBox.Yes:
                    self.sidebar.set_active_page(0)
                    self.workspace.setCurrentIndex(0)
                    conv_view = self.view_widgets[0]
                    if hasattr(conv_view, "_load_files_into_table"):
                        conv_view._load_files_into_table(video_files)
                    return

        # Kịch bản B: 1 video file đơn lẻ
        if len(video_files) == 1:
            v_file = video_files[0]
            if cur_idx == 1:  # Đang ở Downloader
                ret = QMessageBox.question(
                    self, "Gợi Ý Chuyển Tab",
                    f"Bạn vừa kéo thả video: {os.path.basename(v_file)}\n"
                    "Bạn có muốn chuyển sang tab 'Cắt Video' để chỉnh sửa không?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if ret == QMessageBox.Yes:
                    self.sidebar.set_active_page(3)
                    self.workspace.setCurrentIndex(3)
                    cutter_view = self.view_widgets[3]
                    if hasattr(cutter_view, "_load_video"):
                        cutter_view._load_video(v_file)
                    return

        # Nạp trực tiếp vào view hiện tại
        if cur_idx == 0:  # Converter
            targets = video_files + audio_files
            if targets and hasattr(cur_view, "_load_files_into_table"):
                cur_view._load_files_into_table(targets)
        elif cur_idx == 2:  # Merger
            if video_files and hasattr(cur_view, "_queue_probe_files"):
                cur_view._queue_probe_files(video_files)
            if audio_files and hasattr(cur_view, "txt_bgm_file"):
                cur_view.txt_bgm_file.setText(audio_files[0])
        elif cur_idx == 3:  # Cutter
            if video_files and hasattr(cur_view, "_load_video"):
                cur_view._load_video(video_files[0])

    def open_files(self, file_paths: List[str]):
        """Xử lý mở danh sách file truyền từ dòng lệnh hoặc menu ngữ cảnh chuột phải."""
        if not file_paths:
            return
        video_files = [f for f in file_paths if Path(f).suffix.lower() in MEDIA_EXTENSIONS]
        audio_files = [f for f in file_paths if Path(f).suffix.lower() in AUDIO_EXTENSIONS]
        targets = video_files + audio_files
        if not targets:
            return

        # Nạp vào Converter (Tab 0) làm mặc định
        self.sidebar.set_active_page(0)
        self.workspace.setCurrentIndex(0)
        conv_view = self.view_widgets[0]
        if hasattr(conv_view, "_load_files_into_table"):
            conv_view._load_files_into_table(targets)

        self.log_console.append_log(
            f"Kéo thả nhận {len(video_files)} video, {len(audio_files)} audio", "INFO"
        )
