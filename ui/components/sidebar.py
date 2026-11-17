"""
Sidebar Component
Thanh điều hướng bên trái giao diện:
- Tự động sinh danh sách nút bấm dựa trên các module (BaseModule) được đăng ký
- Nút Cài Đặt và Giới Thiệu
- Hiển thị huy hiệu card đồ họa GPU thời gian thực.
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt, Signal
from modules.base_module import BaseModule
from core.gpu import GPUDetector


class Sidebar(QWidget):
    page_changed = Signal(int)
    open_settings = Signal()
    open_about = Signal()

    def __init__(self, modules: List[BaseModule], parent=None):
        super().__init__(parent)
        self.modules = modules
        self.setObjectName("Sidebar")
        self.setFixedWidth(230)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(8)

        # 1. Header Thương hiệu
        lbl_title = QLabel("🎬 Media Studio")
        lbl_title.setObjectName("SidebarTitle")
        lbl_sub = QLabel("All-in-One Desktop Studio")
        lbl_sub.setObjectName("SidebarSubtitle")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Kẻ ngang
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #23272F; margin: 8px 0;")
        layout.addWidget(sep)

        # 2. Sinh nút động từ danh sách BaseModule
        self.buttons = []
        for index, mod in enumerate(self.modules):
            btn = QPushButton(f"{mod.icon}  {mod.display_name}")
            btn.setProperty("class", "sidebar-btn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=index: self.page_changed.emit(idx))
            self.button_group.addButton(btn, index)
            self.buttons.append(btn)
            layout.addWidget(btn)

        if self.buttons:
            self.buttons[0].setChecked(True)

        layout.addStretch()

        # 3. Phím Cài đặt & Giới thiệu
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #23272F; margin: 8px 0;")
        layout.addWidget(sep2)

        btn_settings = QPushButton("⚙️  Cài Đặt Hệ Thống")
        btn_settings.setProperty("class", "sidebar-btn")
        btn_settings.setCursor(Qt.PointingHandCursor)
        btn_settings.clicked.connect(self.open_settings.emit)
        layout.addWidget(btn_settings)

        btn_about = QPushButton("ℹ️  Giới Thiệu & Bản Quyền")
        btn_about.setProperty("class", "sidebar-btn")
        btn_about.setCursor(Qt.PointingHandCursor)
        btn_about.clicked.connect(self.open_about.emit)
        layout.addWidget(btn_about)

        # 4. Huy hiệu GPU
        gpu_box = QFrame()
        gpu_box.setStyleSheet("""
            background-color: #121418; border: 1px solid #23272F;
            border-radius: 6px; padding: 6px; margin-top: 4px;
        """)
        gpu_layout = QVBoxLayout(gpu_box)
        gpu_layout.setContentsMargins(6, 4, 6, 4)
        gpu_layout.setSpacing(2)

        lbl_t = QLabel("⚡ TĂNG TỐC PHẦN CỨNG:")
        lbl_t.setStyleSheet("font-size: 9px; color: #94A3B8; font-weight: bold;")
        
        gpu_info = GPUDetector.detect_gpu()
        lbl_v = QLabel(gpu_info["acceleration_name"].split(" (")[0])
        lbl_v.setStyleSheet("font-size: 11px; color: #34D399; font-weight: 600;")
        lbl_v.setWordWrap(True)

        gpu_layout.addWidget(lbl_t)
        gpu_layout.addWidget(lbl_v)
        layout.addWidget(gpu_box)

    def set_active_page(self, index: int):
        btn = self.button_group.button(index)
        if btn:
            btn.setChecked(True)
