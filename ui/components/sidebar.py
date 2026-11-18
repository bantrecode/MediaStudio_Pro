"""
Sidebar Component
Thanh điều hướng bên trái giao diện:
- Tự động sinh danh sách nút bấm dựa trên các module (BaseModule) được đăng ký
- Hỗ trợ thu gọn/mở rộng (220px <-> 64px icon-only) kèm animation QPropertyAnimation
- Lưu/khôi phục trạng thái bằng QSettings
- Hiển thị huy hiệu card đồ họa GPU thời gian thực.
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QSettings
from modules.base_module import BaseModule
from core.gpu import GPUDetector


class Sidebar(QWidget):
    page_changed = Signal(int)
    open_settings = Signal()
    open_about = Signal()
    open_help = Signal()

    EXPANDED_WIDTH = 220
    COLLAPSED_WIDTH = 64

    def __init__(self, modules: List[BaseModule], parent=None):
        super().__init__(parent)
        self.modules = modules
        self.setObjectName("Sidebar")
        self.settings = QSettings("MediaStudio", "MediaStudioPro")

        # Đọc trạng thái đã lưu
        self.is_collapsed = self.settings.value("sidebar_collapsed", False, type=bool)
        self._auto_collapsed = False

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self._setup_ui()

        # Áp dụng kích thước ban đầu
        initial_w = self.COLLAPSED_WIDTH if self.is_collapsed else self.EXPANDED_WIDTH
        self.setFixedWidth(initial_w)
        self._update_ui_state(self.is_collapsed)

    def _get_sidebar_width(self) -> int:
        return self.width()

    def _set_sidebar_width(self, w: int):
        self.setFixedWidth(w)

    sidebar_width = Property(int, _get_sidebar_width, _set_sidebar_width)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 16, 12, 14)
        self.main_layout.setSpacing(6)

        # 1. Header Thương hiệu + Nút Toggle Thu Gọn
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(4)

        self.title_vbox = QVBoxLayout()
        self.title_vbox.setSpacing(1)
        self.lbl_title = QLabel("🎬 Media Studio")
        self.lbl_title.setObjectName("SidebarTitle")
        self.lbl_sub = QLabel("Desktop Pro")
        self.lbl_sub.setObjectName("SidebarSubtitle")
        self.title_vbox.addWidget(self.lbl_title)
        self.title_vbox.addWidget(self.lbl_sub)
        header_row.addLayout(self.title_vbox, 1)

        self.btn_toggle = QPushButton("☰")
        self.btn_toggle.setObjectName("SidebarToggle")
        self.btn_toggle.setFixedSize(28, 28)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setToolTip("Thu gọn / Mở rộng Sidebar (220px ↔ 64px)")
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        header_row.addWidget(self.btn_toggle)

        self.main_layout.addLayout(header_row)

        # Kẻ ngang
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.HLine)
        self.sep.setProperty("class", "separator")
        self.main_layout.addWidget(self.sep)

        # 2. Sinh nút động từ danh sách BaseModule
        self.buttons = []
        for index, mod in enumerate(self.modules):
            btn = QPushButton(f"{mod.icon}  {mod.display_name}")
            btn.setProperty("class", "sidebar-btn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(mod.display_name)
            btn.clicked.connect(lambda checked, idx=index: self.page_changed.emit(idx))
            self.button_group.addButton(btn, index)
            self.buttons.append(btn)
            self.main_layout.addWidget(btn)

        if self.buttons:
            self.buttons[0].setChecked(True)

        self.main_layout.addStretch()

        # 3. Phím Cài đặt, Trợ giúp & Giới thiệu
        self.sep2 = QFrame()
        self.sep2.setFrameShape(QFrame.HLine)
        self.sep2.setProperty("class", "separator")
        self.main_layout.addWidget(self.sep2)

        self.btn_help = QPushButton("📖  Hướng Dẫn")
        self.btn_help.setProperty("class", "sidebar-btn")
        self.btn_help.setCursor(Qt.PointingHandCursor)
        self.btn_help.setToolTip("Hướng Dẫn Sử Dụng")
        self.btn_help.clicked.connect(self.open_help.emit)
        self.main_layout.addWidget(self.btn_help)

        self.btn_settings = QPushButton("⚙️  Cài Đặt")
        self.btn_settings.setProperty("class", "sidebar-btn")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setToolTip("Cài Đặt Hệ Thống")
        self.btn_settings.clicked.connect(self.open_settings.emit)
        self.main_layout.addWidget(self.btn_settings)

        self.btn_about = QPushButton("ℹ️  Giới Thiệu")
        self.btn_about.setProperty("class", "sidebar-btn")
        self.btn_about.setCursor(Qt.PointingHandCursor)
        self.btn_about.setToolTip("Giới Thiệu & Bản Quyền")
        self.btn_about.clicked.connect(self.open_about.emit)
        self.main_layout.addWidget(self.btn_about)

        # 4. Huy hiệu GPU
        self.gpu_box = QFrame()
        self.gpu_box.setProperty("class", "card-nested")
        gpu_layout = QVBoxLayout(self.gpu_box)
        gpu_layout.setContentsMargins(6, 4, 6, 4)
        gpu_layout.setSpacing(2)

        self.lbl_gpu_title = QLabel("⚡ TĂNG TỐC GPU:")
        self.lbl_gpu_title.setProperty("class", "label-muted")
        self.lbl_gpu_title.setStyleSheet("font-size: 9px; font-weight: bold;")

        gpu_info = GPUDetector.detect_gpu()
        self.lbl_gpu_name = QLabel(gpu_info["acceleration_name"].split(" (")[0])
        self.lbl_gpu_name.setProperty("class", "label-success")
        self.lbl_gpu_name.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.lbl_gpu_name.setWordWrap(True)

        gpu_layout.addWidget(self.lbl_gpu_title)
        gpu_layout.addWidget(self.lbl_gpu_name)
        self.main_layout.addWidget(self.gpu_box)

    def _update_ui_state(self, collapsed: bool):
        """Cập nhật văn bản, lề và trạng thái hiển thị của các thành phần."""
        if collapsed:
            self.main_layout.setContentsMargins(4, 14, 4, 12)
            self.lbl_title.setVisible(False)
            self.lbl_sub.setVisible(False)
            self.gpu_box.setVisible(False)
            for idx, btn in enumerate(self.buttons):
                btn.setText(self.modules[idx].icon)
                btn.setStyleSheet("text-align: center; padding: 10px 0; font-size: 15px;")
            self.btn_help.setText("📖")
            self.btn_help.setStyleSheet("text-align: center; padding: 10px 0; font-size: 14px;")
            self.btn_settings.setText("⚙️")
            self.btn_settings.setStyleSheet("text-align: center; padding: 10px 0; font-size: 14px;")
            self.btn_about.setText("ℹ️")
            self.btn_about.setStyleSheet("text-align: center; padding: 10px 0; font-size: 14px;")
        else:
            self.main_layout.setContentsMargins(12, 16, 12, 14)
            self.lbl_title.setVisible(True)
            self.lbl_sub.setVisible(True)
            self.gpu_box.setVisible(True)
            for idx, btn in enumerate(self.buttons):
                btn.setText(f"{self.modules[idx].icon}  {self.modules[idx].display_name}")
                btn.setStyleSheet("")
            self.btn_help.setText("📖  Hướng Dẫn")
            self.btn_help.setStyleSheet("")
            self.btn_settings.setText("⚙️  Cài Đặt")
            self.btn_settings.setStyleSheet("")
            self.btn_about.setText("ℹ️  Giới Thiệu")
            self.btn_about.setStyleSheet("")

    def _start_animation(self, target_w: int):
        if hasattr(self, "_anim") and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"sidebar_width")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target_w)
        self._anim.start()

    def collapse(self, animate: bool = True, auto: bool = False):
        if self.is_collapsed:
            return
        self.is_collapsed = True
        self._auto_collapsed = auto
        if not auto:
            self.settings.setValue("sidebar_collapsed", True)

        self._update_ui_state(True)
        if animate:
            self._start_animation(self.COLLAPSED_WIDTH)
        else:
            self.setFixedWidth(self.COLLAPSED_WIDTH)

    def expand(self, animate: bool = True, manual: bool = False):
        if not self.is_collapsed:
            return
        self.is_collapsed = False
        self._auto_collapsed = False
        if manual:
            self.settings.setValue("sidebar_collapsed", False)

        self._update_ui_state(False)
        if animate:
            self._start_animation(self.EXPANDED_WIDTH)
        else:
            self.setFixedWidth(self.EXPANDED_WIDTH)

    def toggle_collapse(self):
        if self.is_collapsed:
            self.expand(animate=True, manual=True)
        else:
            self.collapse(animate=True, auto=False)

    def set_active_page(self, index: int):
        btn = self.button_group.button(index)
        if btn:
            btn.setChecked(True)
