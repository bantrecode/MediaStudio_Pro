"""
Placeholder View Component
View đại diện cho các module trong giai đoạn phát triển ban đầu.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt


class PlaceholderView(QWidget):
    def __init__(self, title: str, subtitle: str, features: list, icon: str = "🚀", parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self.features = features
        self.icon = icon
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Card chứa thông tin module
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        # Tiêu đề
        lbl_icon = QLabel(self.icon)
        lbl_icon.setStyleSheet("font-size: 36px;")

        lbl_title = QLabel(self.title)
        lbl_title.setProperty("class", "heading")

        lbl_sub = QLabel(self.subtitle)
        lbl_sub.setProperty("class", "subheading")
        lbl_sub.setWordWrap(True)

        card_layout.addWidget(lbl_icon)
        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_sub)

        # Đường kẻ
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2D333E; margin: 8px 0;")
        card_layout.addWidget(sep)

        # Danh sách tính năng sẽ có
        lbl_feat_title = QLabel("Tính Năng Sẽ Tích Hợp:")
        lbl_feat_title.setStyleSheet("font-weight: 600; color: #818CF8;")
        card_layout.addWidget(lbl_feat_title)

        for feat in self.features:
            lbl_item = QLabel(f"•  {feat}")
            lbl_item.setStyleSheet("color: #CBD5E1; padding-left: 8px;")
            card_layout.addWidget(lbl_item)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()

