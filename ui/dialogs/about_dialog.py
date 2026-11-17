"""
About Dialog
Hộp thoại thông tin phần mềm, giấy phép mã nguồn mở (FFmpeg GPL, yt-dlp Unlicense, Qt LGPL)
và điều khoản từ chối trách nhiệm bản quyền.
"""

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFrame
)
from PySide6.QtCore import Qt
from core.system import get_appdata_dir


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thông Tin Phần Mềm - All-in-One Media Studio")
        self.resize(500, 420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        lbl_title = QLabel("🎬 All-in-One Media Studio")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")

        lbl_ver = QLabel("Phiên bản: 1.0.0 (Architecture Phase 0) | Chạy độc lập trên Windows 64-bit")
        lbl_ver.setStyleSheet("font-size: 11px; color: #818CF8;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_ver)

        # Khung giấy phép bản quyền
        txt_license = QTextEdit()
        txt_license.setReadOnly(True)
        txt_license.setStyleSheet("""
            background: #181B20; border: 1px solid #2B303C; border-radius: 8px;
            font-size: 11px; color: #CBD5E1;
        """)

        license_html = f"""
        <h4 style='color: #F8FAFC;'>Thư Viện Mã Nguồn Mở & Giấy Phép:</h4>
        <ul>
            <li><b>FFmpeg:</b> Được cấp phép theo GNU GPL v3.0 / LGPL v2.1. Mã nguồn FFmpeg chính thức tại <a href='https://ffmpeg.org' style='color: #818CF8;'>https://ffmpeg.org</a></li>
            <li><b>yt-dlp:</b> Được cấp phép theo The Unlicense (Public Domain). Mã nguồn tại <a href='https://github.com/yt-dlp/yt-dlp' style='color: #818CF8;'>https://github.com/yt-dlp/yt-dlp</a></li>
            <li><b>PySide6 (Qt for Python):</b> Được cấp phép theo GNU LGPL v3. Mã nguồn tại <a href='https://www.qt.io' style='color: #818CF8;'>https://www.qt.io</a></li>
            <li><b>Python:</b> Phiên bản {sys.version.split()[0]} (PSF License).</li>
        </ul>
        <hr style='border: 1px solid #2B303C;'/>
        <h4 style='color: #FBBF24;'>Điều Khoản Miễn Trừ Trách Nhiệm (Disclaimer):</h4>
        <p style='color: #94A3B8; line-height: 1.4;'>
        Ứng dụng này chỉ cung cấp các tiện ích xử lý và hỗ trợ kỹ thuật đồ họa máy tính. 
        Người sử dụng hoàn toàn tự chịu trách nhiệm trước pháp luật về quyền sở hữu trí tuệ, 
        bản quyền nội dung và mục đích sử dụng đối với bất kỳ tài liệu media nào được tải về, cắt ghép hoặc chuyển đổi thông qua ứng dụng.
        </p>
        <p style='color: #64748B; font-size: 10px;'>
        Dữ liệu ứng dụng lưu tại: {get_appdata_dir()}
        </p>
        """
        txt_license.setHtml(license_html)
        layout.addWidget(txt_license)

        # Nút đóng
        btn_box = QHBoxLayout()
        btn_close = QPushButton("Đóng")
        btn_close.setProperty("class", "btn-secondary")
        btn_close.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

