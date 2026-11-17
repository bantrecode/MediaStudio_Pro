"""
Log Console Component
Bảng điều khiển nhật ký thời gian thực với phân loại màu sắc, nút xóa,
và tính năng 'Xuất log để báo lỗi' thành file ZIP.
"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor
from core.logger import export_logs
from core.system import get_logs_dir


class LogConsole(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogConsole")
        self.is_expanded = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 8)
        layout.setSpacing(6)

        # Header của Console
        header = QHBoxLayout()

        lbl_title = QLabel("📋 Nhật Ký Hệ Thống (Console Logs)")
        lbl_title.setStyleSheet("font-weight: 600; color: #CBD5E1; font-size: 12px;")

        self.btn_export = QPushButton("📤 Xuất Log Báo Lỗi")
        self.btn_export.setProperty("class", "btn-secondary")
        self.btn_export.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._export_log_file)

        self.btn_open_folder = QPushButton("📂 Mở Thư Mục Log")
        self.btn_open_folder.setProperty("class", "btn-secondary")
        self.btn_open_folder.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_log_folder)

        self.btn_clear = QPushButton("Xóa Màn Hình")
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_logs)

        self.btn_toggle = QPushButton("Thu gọn ▲")
        self.btn_toggle.setProperty("class", "btn-secondary")
        self.btn_toggle.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_collapse)

        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(self.btn_export)
        header.addWidget(self.btn_open_folder)
        header.addWidget(self.btn_clear)
        header.addWidget(self.btn_toggle)
        layout.addLayout(header)

        # Khung hiển thị log
        self.log_text = QTextEdit()
        self.log_text.setObjectName("LogDisplay")
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(100)
        layout.addWidget(self.log_text)

        self.append_log("Khởi động hệ thống All-in-One Media Studio...", "SUCCESS")

    @Slot(str, str)
    def append_log(self, message: str, level: str = "INFO"):
        """Thêm một dòng log mới có màu sắc và timestamp."""
        now = datetime.now().strftime("%H:%M:%S")

        upper_msg = message.upper()
        if "[SUCCESS]" in upper_msg:
            level = "SUCCESS"
        elif "[ERROR]" in upper_msg or "[EXCEPTION]" in upper_msg:
            level = "ERROR"
        elif "[WARNING]" in upper_msg:
            level = "WARNING"

        colors = {
            "INFO": "#94A3B8",
            "SUCCESS": "#34D399",
            "WARNING": "#FBBF24",
            "ERROR": "#F87171"
        }
        color = colors.get(level.upper(), "#CBD5E1")

        html_line = (
            f"<span style='color: #64748B;'>[{now}]</span> "
            f"<span style='color: {color}; font-weight: 600;'>[{level.upper()}]</span> "
            f"<span style='color: #E2E8F0;'>{message}</span>"
        )
        self.log_text.append(html_line)
        self.log_text.moveCursor(QTextCursor.End)

    def clear_logs(self):
        self.log_text.clear()

    def toggle_collapse(self):
        if self.is_expanded:
            self.log_text.hide()
            self.btn_toggle.setText("Mở rộng ▼")
            self.is_expanded = False
        else:
            self.log_text.show()
            self.btn_toggle.setText("Thu gọn ▲")
            self.is_expanded = True

    def _export_log_file(self):
        default_name = f"mediastudio_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        dest, _ = QFileDialog.getSaveFileName(self, "Lưu file log báo lỗi", default_name, "Zip Archives (*.zip)")
        if dest:
            if export_logs(dest):
                QMessageBox.information(self, "Thành Công", f"Đã xuất log thành công vào:\n{dest}")
                self.append_log(f"Đã xuất log ra file: {dest}", "SUCCESS")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xuất file log. Vui lòng thử lại!")

    def _open_log_folder(self):
        logs_dir = str(get_logs_dir())
        if os.name == "nt":
            os.startfile(logs_dir)
