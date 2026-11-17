"""
Settings Dialog
Hộp thoại cấu hình ứng dụng: thư mục xuất, proxy, mẫu tên, số lượng job song song, GPU, và cập nhật yt-dlp.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QComboBox, QCheckBox, QFileDialog, QMessageBox, QFrame, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal
from core.config import ConfigManager
from core.database import HistoryDB
from core.gpu import GPUDetector
from core.ytdlp_runner import YtDlpRunner


class YtDlpUpdateWorker(QThread):
    finished_signal = Signal(bool, str)

    def run(self):
        success, msg = YtDlpRunner.update_ytdlp_binary()
        self.finished_signal.emit(success, msg)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài Đặt Hệ Thống - MediaStudio")
        self.resize(520, 480)
        self.config_mgr = ConfigManager.get_instance()
        self.update_worker: Optional[YtDlpUpdateWorker] = None
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

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
        form.addRow("Lựa chọn Tăng tốc GPU:", self.cbo_gpu)

        # 5. Proxy
        self.txt_proxy = QLineEdit()
        self.txt_proxy.setPlaceholderText("http://127.0.0.1:1080 (Để trống nếu không dùng)")
        form.addRow("Proxy mạng (cho yt-dlp):", self.txt_proxy)

        layout.addLayout(form)

        # Các tùy chọn checkbox
        opts_box = QVBoxLayout()
        self.chk_clipboard = QCheckBox("Tự động nhận diện đường link khi copy vào Clipboard")
        self.chk_sound = QCheckBox("Phát âm thanh thông báo khi hoàn thành tác vụ")
        self.chk_shutdown = QCheckBox("Tự động tắt máy tính khi toàn bộ hàng đợi hoàn tất")

        opts_box.addWidget(self.chk_clipboard)
        opts_box.addWidget(self.chk_sound)
        opts_box.addWidget(self.chk_shutdown)
        layout.addLayout(opts_box)

        # Khung hành động phụ
        action_card = QFrame()
        action_card.setStyleSheet("background: #181B20; border: 1px solid #2B303C; border-radius: 8px; padding: 10px;")
        act_layout = QHBoxLayout(action_card)

        self.btn_update_ytdlp = QPushButton("🔄 Cập Nhật yt-dlp Mới Nhất")
        self.btn_update_ytdlp.setProperty("class", "btn-secondary")
        self.btn_update_ytdlp.clicked.connect(self._update_ytdlp)

        self.btn_clear_db = QPushButton("🗑️ Xóa Lịch Sử Đã Chạy")
        self.btn_clear_db.setProperty("class", "btn-secondary")
        self.btn_clear_db.clicked.connect(self._clear_history)

        act_layout.addWidget(self.btn_update_ytdlp)
        act_layout.addWidget(self.btn_clear_db)
        layout.addWidget(action_card)

        layout.addStretch()

        # Nút Lưu / Hủy
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

        # Naming
        idx = self.cbo_naming.findData(s.get("naming_pattern", "{title}_{date}"))
        if idx >= 0:
            self.cbo_naming.setCurrentIndex(idx)

        # GPU
        idx_gpu = self.cbo_gpu.findData(s.get("gpu_preference", "auto"))
        if idx_gpu >= 0:
            self.cbo_gpu.setCurrentIndex(idx_gpu)

        self.chk_clipboard.setChecked(s.get("auto_clipboard", True))
        self.chk_sound.setChecked(s.get("play_sound_when_finished", True))
        self.chk_shutdown.setChecked(s.get("shutdown_when_finished", False))

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Xuất", self.txt_output.text())
        if folder:
            self.txt_output.setText(folder)

    def _save_values(self):
        new_s = {
            "default_output_dir": self.txt_output.text().strip(),
            "proxy": self.txt_proxy.text().strip(),
            "max_concurrent_jobs": self.spn_concurrent.value(),
            "naming_pattern": self.cbo_naming.currentData(),
            "gpu_preference": self.cbo_gpu.currentData(),
            "auto_clipboard": self.chk_clipboard.isChecked(),
            "play_sound_when_finished": self.chk_sound.isChecked(),
            "shutdown_when_finished": self.chk_shutdown.isChecked(),
        }
        self.config_mgr.update_all(new_s)
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

