"""
Settings Dialog - MediaStudio Pro
Hộp thoại cấu hình toàn diện:
- Chung & Tác Vụ: Thư mục xuất, Proxy, GPU, FFmpeg/FFprobe tùy chỉnh, Cập nhật yt-dlp, Hành động khi xong.
- Giao Diện: Sáng/Tối/Hệ thống, Cỡ chữ, Màu nhấn, Ngôn ngữ (vi/en).
- Thư Mục Theo Dõi (Watch Folder): Bật/tắt, đường dẫn theo dõi, thư mục xuất, preset tự động.
- Phím Tắt (Shortcuts): Bảng tra cứu phím tắt nhanh cho Cutter và ứng dụng.
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QComboBox, QCheckBox, QFileDialog, QMessageBox, QFrame,
    QFormLayout, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from core.config import ConfigManager
from core.database import HistoryDB
from core.gpu import GPUDetector
from core.path_manager import PathManager
from core.ytdlp_runner import YtDlpRunner
from core.watch_folder import WatchFolderService
from core.i18n import I18nManager, tr
from ui.theme import ThemeManager, ThemeMode, FontSize, ACCENT_PRESETS


class YtDlpUpdateWorker(QThread):
    finished_signal = Signal(bool, str)

    def run(self):
        success, msg = YtDlpRunner.update_ytdlp_binary()
        self.finished_signal.emit(success, msg)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Settings") + " - MediaStudio Pro")
        self.resize(640, 560)
        self.config_mgr = ConfigManager.get_instance()
        self.theme_mgr = ThemeManager.get_instance()
        self.update_worker: Optional[YtDlpUpdateWorker] = None
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.tab_widget = QTabWidget()

        # =====================================================================
        # TAB 1: CHUNG & TÁC VỤ
        # =====================================================================
        tab_general = QWidget()
        gen_layout = QVBoxLayout(tab_general)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        # 1. Thư mục xuất mặc định
        dest_box = QHBoxLayout()
        self.txt_output = QLineEdit()
        btn_browse = QPushButton("📁 Chọn")
        btn_browse.setProperty("class", "btn-secondary")
        btn_browse.clicked.connect(self._browse_output)
        dest_box.addWidget(self.txt_output, 1)
        dest_box.addWidget(btn_browse)
        form.addRow("Thư mục lưu mặc định:", dest_box)

        # 2. Mẫu đặt tên
        self.cbo_naming = QComboBox()
        self.cbo_naming.addItem("{title}_{date}", "{title}_{date}")
        self.cbo_naming.addItem("{title}", "{title}")
        self.cbo_naming.addItem("{title}_{resolution}", "{title}_{resolution}")
        form.addRow("Mẫu đặt tên file:", self.cbo_naming)

        # 3. Số job chạy song song
        self.spn_concurrent = QSpinBox()
        self.spn_concurrent.setRange(1, 8)
        self.spn_concurrent.setValue(2)
        form.addRow("Số tác vụ chạy song song:", self.spn_concurrent)

        # 4. Tùy chọn GPU
        self.cbo_gpu = QComboBox()
        self.cbo_gpu.addItem("Tự động tối ưu (Auto)", "auto")
        self.cbo_gpu.addItem("NVIDIA NVENC", "nvidia")
        self.cbo_gpu.addItem("Intel QuickSync (QSV)", "intel")
        self.cbo_gpu.addItem("AMD AMF", "amd")
        self.cbo_gpu.addItem("CPU Software (libx264)", "cpu")
        form.addRow("Tăng tốc phần cứng GPU:", self.cbo_gpu)

        # 5. Đường dẫn FFmpeg / FFprobe tùy chọn
        ffmpeg_box = QHBoxLayout()
        self.txt_ffmpeg = QLineEdit()
        self.txt_ffmpeg.setPlaceholderText("Mặc định (tự động nhận diện)")
        btn_browse_ff = QPushButton("📁")
        btn_browse_ff.setProperty("class", "btn-secondary")
        btn_browse_ff.clicked.connect(self._browse_ffmpeg)
        btn_test_ff = QPushButton("Kiểm tra")
        btn_test_ff.setProperty("class", "btn-secondary")
        btn_test_ff.clicked.connect(self._test_ffmpeg)
        ffmpeg_box.addWidget(self.txt_ffmpeg, 1)
        ffmpeg_box.addWidget(btn_browse_ff)
        ffmpeg_box.addWidget(btn_test_ff)
        form.addRow("Đường dẫn FFmpeg thủ công:", ffmpeg_box)

        # 6. Proxy
        self.txt_proxy = QLineEdit()
        self.txt_proxy.setPlaceholderText("http://127.0.0.1:1080 (Để trống nếu không dùng)")
        form.addRow("Proxy mạng (cho yt-dlp):", self.txt_proxy)

        # 7. Hành động khi toàn bộ hàng đợi hoàn tất
        self.cbo_finish_action = QComboBox()
        self.cbo_finish_action.addItem("Không làm gì", "none")
        self.cbo_finish_action.addItem("Tự động tắt máy tính (sau 60 giây)", "shutdown")
        self.cbo_finish_action.addItem("Đưa máy tính vào chế độ Ngủ (Sleep)", "sleep")
        form.addRow("Khi hàng đợi hoàn tất:", self.cbo_finish_action)

        gen_layout.addLayout(form)

        # Checkbox tùy chọn
        opts_box = QVBoxLayout()
        self.chk_clipboard = QCheckBox("Tự động nhận diện đường link khi copy vào Clipboard")
        self.chk_sound = QCheckBox("Phát âm thanh thông báo khi hoàn thành tác vụ")
        self.chk_toast = QCheckBox("Gửi thông báo Windows (Toast Notification) khi hoàn tất")
        self.chk_auto_update_ytdlp = QCheckBox("Tự động kiểm tra bản cập nhật yt-dlp mới khi mở app")

        opts_box.addWidget(self.chk_clipboard)
        opts_box.addWidget(self.chk_sound)
        opts_box.addWidget(self.chk_toast)
        opts_box.addWidget(self.chk_auto_update_ytdlp)
        gen_layout.addLayout(opts_box)

        # Khung cập nhật yt-dlp & xóa db
        action_card = QFrame()
        action_card.setProperty("class", "card-nested")
        act_layout = QHBoxLayout(action_card)

        self.btn_update_ytdlp = QPushButton("🔄 Cập Nhật yt-dlp Mới Nhất")
        self.btn_update_ytdlp.setProperty("class", "btn-secondary")
        self.btn_update_ytdlp.clicked.connect(self._update_ytdlp)

        self.btn_clear_db = QPushButton("🗑️ Xóa Lịch Sử Đã Chạy")
        self.btn_clear_db.setProperty("class", "btn-secondary")
        self.btn_clear_db.clicked.connect(self._clear_history)

        act_layout.addWidget(self.btn_update_ytdlp)
        act_layout.addWidget(self.btn_clear_db)
        gen_layout.addWidget(action_card)
        gen_layout.addStretch()

        self.tab_widget.addTab(tab_general, "⚙️ Chung & Tác Vụ")

        # =====================================================================
        # TAB 2: GIAO DIỆN & NGÔN NGỮ
        # =====================================================================
        tab_theme = QWidget()
        theme_layout = QVBoxLayout(tab_theme)
        theme_layout.setContentsMargins(16, 16, 16, 16)
        theme_layout.setSpacing(14)

        theme_form = QFormLayout()
        theme_form.setSpacing(14)

        self.cbo_theme_mode = QComboBox()
        self.cbo_theme_mode.addItem("🖥️  Theo hệ điều hành (System)", ThemeMode.SYSTEM.value)
        self.cbo_theme_mode.addItem("🌙  Chế độ Tối (Dark Mode)", ThemeMode.DARK.value)
        self.cbo_theme_mode.addItem("☀️  Chế độ Sáng (Light Mode)", ThemeMode.LIGHT.value)
        self.cbo_theme_mode.currentIndexChanged.connect(self._on_live_theme_change)
        theme_form.addRow("Chế độ giao diện:", self.cbo_theme_mode)

        self.cbo_font_size = QComboBox()
        self.cbo_font_size.addItem("Nhỏ (12px)", FontSize.SMALL.value)
        self.cbo_font_size.addItem("Vừa (13px - Mặc định)", FontSize.MEDIUM.value)
        self.cbo_font_size.addItem("Lớn (15px)", FontSize.LARGE.value)
        self.cbo_font_size.currentIndexChanged.connect(self._on_live_font_change)
        theme_form.addRow("Cỡ chữ hiển thị:", self.cbo_font_size)

        self.cbo_accent = QComboBox()
        for name, preset in ACCENT_PRESETS.items():
            self.cbo_accent.addItem(f"{name} ({preset['accent']})", name)
        self.cbo_accent.currentIndexChanged.connect(self._on_live_accent_change)
        theme_form.addRow("Màu sắc điểm nhấn:", self.cbo_accent)

        self.cbo_lang = QComboBox()
        self.cbo_lang.addItem("🇻🇳  Tiếng Việt (Mặc định)", "vi")
        self.cbo_lang.addItem("🇬🇧  English", "en")
        theme_form.addRow("Ngôn ngữ giao diện (i18n):", self.cbo_lang)

        theme_layout.addLayout(theme_form)

        preview_card = QFrame()
        preview_card.setProperty("class", "card-nested")
        pv_layout = QVBoxLayout(preview_card)
        pv_layout.setSpacing(8)

        lbl_pv_title = QLabel("👁️ Xem trước giao diện thực tế:")
        lbl_pv_title.setProperty("class", "heading")
        pv_layout.addWidget(lbl_pv_title)

        lbl_pv_desc = QLabel(
            "Giao diện chuẩn WCAG AA với độ tương phản cao, áp dụng ngay tức thì."
        )
        lbl_pv_desc.setProperty("class", "label-muted")
        lbl_pv_desc.setWordWrap(True)
        pv_layout.addWidget(lbl_pv_desc)

        pv_btn_row = QHBoxLayout()
        pv_btn1 = QPushButton("Nút Điểm Nhấn")
        pv_btn1.setProperty("class", "btn-primary")
        pv_btn2 = QPushButton("Nút Thứ Cấp")
        pv_btn2.setProperty("class", "btn-secondary")
        pv_btn3 = QPushButton("Nút Cảnh Báo")
        pv_btn3.setProperty("class", "btn-danger")
        pv_btn_row.addWidget(pv_btn1)
        pv_btn_row.addWidget(pv_btn2)
        pv_btn_row.addWidget(pv_btn3)
        pv_layout.addLayout(pv_btn_row)

        theme_layout.addWidget(preview_card)
        theme_layout.addStretch()

        self.tab_widget.addTab(tab_theme, "🎨 Giao Diện")

        # =====================================================================
        # TAB 3: THƯ MỤC THEO DÕI (WATCH FOLDER)
        # =====================================================================
        tab_wf = QWidget()
        wf_layout = QVBoxLayout(tab_wf)
        wf_layout.setContentsMargins(16, 16, 16, 16)
        wf_layout.setSpacing(14)

        lbl_wf_title = QLabel("📂 Tự Động Hóa Với Thư Mục Theo Dõi (Watch Folder)")
        lbl_wf_title.setProperty("class", "heading")
        wf_layout.addWidget(lbl_wf_title)

        lbl_wf_info = QLabel(
            "Khi tính năng này được bật, bạn chỉ cần kéo-thả file video/audio vào thư mục theo dõi. "
            "MediaStudio Pro sẽ tự động phát hiện, kiểm tra và xếp tác vụ xử lý vào Hàng đợi."
        )
        lbl_wf_info.setProperty("class", "label-muted")
        lbl_wf_info.setWordWrap(True)
        wf_layout.addWidget(lbl_wf_info)

        wf_form = QFormLayout()
        wf_form.setSpacing(12)

        self.chk_wf_enable = QCheckBox("Kích hoạt dịch vụ theo dõi thư mục tự động")
        self.chk_wf_enable.setStyleSheet("font-weight: bold;")
        wf_form.addRow("", self.chk_wf_enable)

        # Thư mục theo dõi
        wf_path_box = QHBoxLayout()
        self.txt_wf_path = QLineEdit()
        self.txt_wf_path.setPlaceholderText("D:\\Videos\\Incoming...")
        btn_browse_wf = QPushButton("📁 Chọn")
        btn_browse_wf.setProperty("class", "btn-secondary")
        btn_browse_wf.clicked.connect(self._browse_wf_path)
        wf_path_box.addWidget(self.txt_wf_path, 1)
        wf_path_box.addWidget(btn_browse_wf)
        wf_form.addRow("Thư mục theo dõi (Watch Dir):", wf_path_box)

        # Thư mục lưu kết quả
        wf_out_box = QHBoxLayout()
        self.txt_wf_output = QLineEdit()
        self.txt_wf_output.setPlaceholderText("D:\\Videos\\Processed...")
        btn_browse_wf_out = QPushButton("📁 Chọn")
        btn_browse_wf_out.setProperty("class", "btn-secondary")
        btn_browse_wf_out.clicked.connect(self._browse_wf_output)
        wf_out_box.addWidget(self.txt_wf_output, 1)
        wf_out_box.addWidget(btn_browse_wf_out)
        wf_form.addRow("Thư mục xuất file kết quả:", wf_out_box)

        # Preset xử lý
        self.cbo_wf_preset = QComboBox()
        self.cbo_wf_preset.addItem("Chuyển đổi MP4 H.264 (Chuẩn phổ biến)", "mp4_h264")
        self.cbo_wf_preset.addItem("Trích xuất âm thanh MP3 192k", "mp3_extract")
        self.cbo_wf_preset.addItem("Nén tối ưu chia sẻ Zalo HD (< 25MB)", "social_zalo")
        self.cbo_wf_preset.addItem("Remux siêu tốc (-c copy trong 1s)", "remux")
        wf_form.addRow("Preset xử lý tự động:", self.cbo_wf_preset)

        wf_layout.addLayout(wf_form)
        wf_layout.addStretch()

        self.tab_widget.addTab(tab_wf, "📂 Thư Mục Theo Dõi")

        # =====================================================================
        # TAB 4: PHÍM TẮT (SHORTCUTS)
        # =====================================================================
        tab_sc = QWidget()
        sc_layout = QVBoxLayout(tab_sc)
        sc_layout.setContentsMargins(16, 16, 16, 16)
        sc_layout.setSpacing(12)

        lbl_sc_title = QLabel("⌨️ Danh Mục Phím Tắt Nhanh (Keyboard Shortcuts)")
        lbl_sc_title.setProperty("class", "heading")
        sc_layout.addWidget(lbl_sc_title)

        table_sc = QTableWidget(7, 3)
        table_sc.setHorizontalHeaderLabels(["Phím Tắt", "Chức Năng", "Khu Vực"])
        table_sc.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_sc.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table_sc.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table_sc.setEditTriggers(QTableWidget.NoEditTriggers)

        shortcuts = [
            ("Space", "Phát hoặc Tạm dừng video (Play / Pause)", "Trình Cắt Video (Cutter)"),
            ("[", "Đặt vị trí hiện tại làm Điểm Bắt Đầu (In Point)", "Trình Cắt Video (Cutter)"),
            ("]", "Đặt vị trí hiện tại làm Điểm Kết Thúc (Out Point)", "Trình Cắt Video (Cutter)"),
            ("←  /  →", "Tua lùi hoặc tiến 1 giây (-1s / +1s)", "Trình Cắt Video (Cutter)"),
            ("Shift + ← / →", "Tua lùi hoặc tiến từng khung hình (1 frame ~40ms)", "Trình Cắt Video (Cutter)"),
            ("Ctrl + V", "Tự động dán liên kết media từ bộ nhớ tạm", "Trình Tải Video (Downloader)"),
            ("▲  /  ▼", "Thay đổi thứ tự ưu tiên các tác vụ đang chờ", "Bảng Hàng Đợi (Job Queue)"),
        ]

        for row_idx, (key, desc, scope) in enumerate(shortcuts):
            item_key = QTableWidgetItem(key)
            item_key.setTextAlignment(Qt.AlignCenter)
            item_desc = QTableWidgetItem(desc)
            item_scope = QTableWidgetItem(scope)
            item_scope.setTextAlignment(Qt.AlignCenter)

            table_sc.setItem(row_idx, 0, item_key)
            table_sc.setItem(row_idx, 1, item_desc)
            table_sc.setItem(row_idx, 2, item_scope)

        sc_layout.addWidget(table_sc)
        self.tab_widget.addTab(tab_sc, "⌨️ Phím Tắt")

        layout.addWidget(self.tab_widget)

        # Nút Lưu / Đóng
        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Lưu Cài Đặt")
        btn_save.setProperty("class", "btn-primary")
        btn_save.clicked.connect(self._save_values)

        btn_cancel = QPushButton("Đóng")
        btn_cancel.setProperty("class", "btn-secondary")
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def _load_values(self):
        s = self.config_mgr.get_all()
        self.txt_output.setText(s.get("default_output_dir", ""))
        self.txt_proxy.setText(s.get("proxy", ""))
        self.spn_concurrent.setValue(s.get("max_concurrent_jobs", 2))
        self.txt_ffmpeg.setText(s.get("custom_ffmpeg_path", ""))

        # Naming
        idx = self.cbo_naming.findData(s.get("naming_pattern", "{title}_{date}"))
        if idx >= 0:
            self.cbo_naming.setCurrentIndex(idx)

        # GPU
        idx_gpu = self.cbo_gpu.findData(s.get("gpu_preference", "auto"))
        if idx_gpu >= 0:
            self.cbo_gpu.setCurrentIndex(idx_gpu)

        # Finish action
        act = s.get("action_when_finished", "none")
        idx_act = self.cbo_finish_action.findData(act)
        if idx_act >= 0:
            self.cbo_finish_action.setCurrentIndex(idx_act)

        self.chk_clipboard.setChecked(s.get("auto_clipboard", True))
        self.chk_sound.setChecked(s.get("play_sound_when_finished", True))
        self.chk_toast.setChecked(s.get("toast_notification", True))
        self.chk_auto_update_ytdlp.setChecked(s.get("auto_check_ytdlp_update", True))

        # Tải cấu hình Giao diện
        current_mode = self.theme_mgr.mode
        idx_mode = self.cbo_theme_mode.findData(current_mode)
        if idx_mode >= 0:
            self.cbo_theme_mode.blockSignals(True)
            self.cbo_theme_mode.setCurrentIndex(idx_mode)
            self.cbo_theme_mode.blockSignals(False)

        current_size = self.theme_mgr.font_size
        idx_size = self.cbo_font_size.findData(current_size)
        if idx_size >= 0:
            self.cbo_font_size.blockSignals(True)
            self.cbo_font_size.setCurrentIndex(idx_size)
            self.cbo_font_size.blockSignals(False)

        current_accent = self.theme_mgr.accent_name
        idx_acc = self.cbo_accent.findData(current_accent)
        if idx_acc >= 0:
            self.cbo_accent.blockSignals(True)
            self.cbo_accent.setCurrentIndex(idx_acc)
            self.cbo_accent.blockSignals(False)

        cur_lang = I18nManager.get_instance().current_language
        idx_l = self.cbo_lang.findData(cur_lang)
        if idx_l >= 0:
            self.cbo_lang.setCurrentIndex(idx_l)

        # Watch folder
        self.chk_wf_enable.setChecked(s.get("watch_folder_enabled", False))
        self.txt_wf_path.setText(s.get("watch_folder_path", ""))
        self.txt_wf_output.setText(s.get("watch_folder_output", ""))
        idx_wf_p = self.cbo_wf_preset.findData(s.get("watch_folder_preset", "mp4_h264"))
        if idx_wf_p >= 0:
            self.cbo_wf_preset.setCurrentIndex(idx_wf_p)

    def _on_live_theme_change(self):
        mode = self.cbo_theme_mode.currentData()
        if mode:
            self.theme_mgr.set_mode(mode)

    def _on_live_font_change(self):
        size = self.cbo_font_size.currentData()
        if size:
            self.theme_mgr.set_font_size(size)

    def _on_live_accent_change(self):
        preset_name = self.cbo_accent.currentData()
        if preset_name:
            self.theme_mgr.set_accent_preset(preset_name)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Xuất", self.txt_output.text())
        if folder:
            self.txt_output.setText(folder)

    def _browse_wf_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Theo Dõi", self.txt_wf_path.text())
        if folder:
            self.txt_wf_path.setText(folder)

    def _browse_wf_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Xuất File Tự Động", self.txt_wf_output.text())
        if folder:
            self.txt_wf_output.setText(folder)

    def _browse_ffmpeg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file ffmpeg.exe thủ công", "", "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            self.txt_ffmpeg.setText(file_path)

    def _test_ffmpeg(self):
        path = self.txt_ffmpeg.text().strip() or PathManager.get_ffmpeg_path()
        ok, msg = PathManager.test_binary(path)
        if ok:
            QMessageBox.information(self, "FFmpeg Hợp Lệ", f"✅ Khởi chạy thành công:\n{msg}")
        else:
            QMessageBox.warning(self, "FFmpeg Không Hợp Lệ", f"❌ Không thể thực thi file:\n{msg}")

    def _save_values(self):
        new_s = {
            "default_output_dir": self.txt_output.text().strip(),
            "proxy": self.txt_proxy.text().strip(),
            "max_concurrent_jobs": self.spn_concurrent.value(),
            "naming_pattern": self.cbo_naming.currentData(),
            "gpu_preference": self.cbo_gpu.currentData(),
            "action_when_finished": self.cbo_finish_action.currentData(),
            "auto_clipboard": self.chk_clipboard.isChecked(),
            "play_sound_when_finished": self.chk_sound.isChecked(),
            "toast_notification": self.chk_toast.isChecked(),
            "auto_check_ytdlp_update": self.chk_auto_update_ytdlp.isChecked(),
            "custom_ffmpeg_path": self.txt_ffmpeg.text().strip(),
            # Watch folder
            "watch_folder_enabled": self.chk_wf_enable.isChecked(),
            "watch_folder_path": self.txt_wf_path.text().strip(),
            "watch_folder_output": self.txt_wf_output.text().strip(),
            "watch_folder_preset": self.cbo_wf_preset.currentData(),
        }
        self.config_mgr.update_all(new_s)

        # Cập nhật đường dẫn FFmpeg trong PathManager
        PathManager.set_custom_ffmpeg_path(new_s["custom_ffmpeg_path"])

        # Cập nhật Watch Folder Service
        wf_service = WatchFolderService.get_instance()
        if new_s["watch_folder_enabled"] and new_s["watch_folder_path"]:
            wf_service.start()
        else:
            wf_service.stop()

        # Lưu cài đặt Giao diện
        mode = self.cbo_theme_mode.currentData()
        size = self.cbo_font_size.currentData()
        preset_name = self.cbo_accent.currentData()
        lang = self.cbo_lang.currentData()

        if mode:
            self.theme_mgr.set_mode(mode)
        if size:
            self.theme_mgr.set_font_size(size)
        if preset_name:
            self.theme_mgr.set_accent_preset(preset_name)
        if lang:
            I18nManager.get_instance().set_language(lang)

        QMessageBox.information(self, "Thành Công", "Đã lưu cài đặt thành công!")
        self.accept()

    def _update_ytdlp(self):
        self.btn_update_ytdlp.setEnabled(False)
        self.btn_update_ytdlp.setText("⏳ Đang cập nhật...")
        self.update_worker = YtDlpUpdateWorker()
        self.update_worker.finished_signal.connect(self._on_update_done)
        self.update_worker.start()

    def _on_update_done(self, success: bool, msg: str):
        self.btn_update_ytdlp.setEnabled(True)
        self.btn_update_ytdlp.setText("🔄 Cập Nhật yt-dlp Mới Nhất")
        if success:
            QMessageBox.information(self, "Thành Công", msg)
        else:
            QMessageBox.warning(self, "Cập Nhật Thất Bại", msg)

    def _clear_history(self):
        ret = QMessageBox.question(self, "Xác Nhận", "Bạn có chắc chắn muốn xóa toàn bộ lịch sử tác vụ và cache link không?")
        if ret == QMessageBox.Yes:
            HistoryDB.get_instance().clear_history()
            QMessageBox.information(self, "Thành Công", "Đã xóa sạch lịch sử SQLite!")
