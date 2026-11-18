"""
Empty State Component
Hiển thị trạng thái danh sách / bảng trống với biểu tượng, hướng dẫn và nút thao tác nhanh.
"""

from typing import Optional, Callable
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class EmptyStateWidget(QWidget):
    def __init__(
        self,
        icon: str = "📁",
        title: str = "Chưa có dữ liệu",
        subtitle: str = "Kéo thả file vào đây hoặc bấm nút bên dưới",
        action_text: Optional[str] = "Chọn File...",
        action_callback: Optional[Callable] = None,
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName("EmptyStateWidget")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(8)

        lbl_icon = QLabel(icon)
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 32px; background: transparent;")
        layout.addWidget(lbl_icon)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("EmptyStateTitle")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setObjectName("EmptyStateSubtitle")
            lbl_sub.setAlignment(Qt.AlignCenter)
            lbl_sub.setWordWrap(True)
            layout.addWidget(lbl_sub)

        if action_text and action_callback:
            self.btn_action = QPushButton(action_text)
            self.btn_action.setProperty("class", "btn-secondary")
            self.btn_action.setCursor(Qt.PointingHandCursor)
            self.btn_action.setStyleSheet("padding: 5px 14px; font-size: 11px; margin-top: 4px;")
            self.btn_action.clicked.connect(action_callback)
            layout.addWidget(self.btn_action, 0, Qt.AlignCenter)
        else:
            self.btn_action = None
