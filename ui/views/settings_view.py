"""
Settings & Diagnostics View
Trang cài đặt và chẩn đoán hệ thống: kiểm tra FFmpeg, GPU, thư mục dữ liệu, và dọn dẹp file tạm.
"""

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from core.path_manager import PathManager
from core.hardware_detector import HardwareDetector


class SettingsView(QWidget):
    def __init__(self, log_callback=None, parent=None):
        super().__init__(parent)
        self.log_callback = log_callback
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Card Thông Tin Hệ Thống
        card_sys = QFrame()
        card_sys.setProperty("class", "card")
        sys_layout = QVBoxLayout(card_sys)
        sys_layout.setSpacing(10)

        lbl_sys_title = QLabel("⚙️ Trạng Thái Hệ Thống & Phần Cứng")
        lbl_sys_title.setProperty("class", "heading")
        sys_layout.addWidget(lbl_sys_title)

        hw_info = HardwareDetector.detect_hardware()
        ffmpeg_path = PathManager.get_ffmpeg_path()
        ffprobe_path = PathManager.get_ffprobe_path()

        infos = [
            ("Bộ Tăng Tốc (Hardware Accel):", hw_info["acceleration_name"]),
            ("Encoder H.264 Khuyến Nghị:", hw_info["best_h264_encoder"]),
            ("Encoder HEVC/H.265 Khuyến Nghị:", hw_info["best_hevc_encoder"]),
            ("Đường Dẫn FFmpeg:", ffmpeg_path),
            ("Đường Dẫn FFprobe:", ffprobe_path),
            ("Thư Mục AppData:", str(PathManager.get_user_data_dir())),
            ("Thư Mục File Tạm:", str(PathManager.get_temp_dir())),
        ]

        for title, val in infos:
            row = QHBoxLayout()
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("color: #94A3B8; font-weight: 500; min-width: 220px;")
            lbl_v = QLabel(str(val))
            lbl_v.setStyleSheet("color: #FFFFFF; font-family: monospace;")
            lbl_v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row.addWidget(lbl_t)
            row.addWidget(lbl_v)
            row.addStretch()
            sys_layout.addLayout(row)

        layout.addWidget(card_sys)

        # Card Quản Lý File Tạm
        card_actions = QFrame()
        card_actions.setProperty("class", "card")
        act_layout = QVBoxLayout(card_actions)
        act_layout.setSpacing(12)

        lbl_act_title = QLabel("🧹 Tiện Ích & Dọn Dẹp")
        lbl_act_title.setProperty("class", "heading")
        act_layout.addWidget(lbl_act_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_open_temp = QPushButton("📂 Mở Thư Mục Tạm")
        btn_open_temp.setProperty("class", "btn-secondary")
        btn_open_temp.setCursor(Qt.PointingHandCursor)
        btn_open_temp.clicked.connect(self._open_temp_folder)

        btn_clear_temp = QPushButton("🗑️ Xóa Sạch File Tạm")
        btn_clear_temp.setProperty("class", "btn-secondary")
        btn_clear_temp.setCursor(Qt.PointingHandCursor)
        btn_clear_temp.clicked.connect(self._clear_temp_folder)

        btn_row.addWidget(btn_open_temp)
        btn_row.addWidget(btn_clear_temp)
        btn_row.addStretch()
        act_layout.addLayout(btn_row)

        layout.addWidget(card_actions)
        layout.addStretch()

    def _open_temp_folder(self):
        temp_dir = PathManager.get_temp_dir()
        if os.name == 'nt':
            os.startfile(temp_dir)
        if self.log_callback:
            self.log_callback(f"Đã mở thư mục tạm: {temp_dir}", "INFO")

    def _clear_temp_folder(self):
        temp_dir = PathManager.get_temp_dir()
        count = 0
        for f in temp_dir.glob("*"):
            try:
                if f.is_file():
                    f.unlink()
                    count += 1
            except Exception:
                pass
        QMessageBox.information(self, "Thông Báo", f"Đã dọn dẹp {count} file tạm.")
        if self.log_callback:
            self.log_callback(f"Đã dọn dẹp thành công {count} file tạm.", "SUCCESS")

