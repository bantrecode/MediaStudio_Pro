"""
Theme Manager - MediaStudio Pro
Quản lý giao diện Sáng / Tối / Theo hệ thống (Light, Dark, System),
bảng token màu sắc, sinh QSS động và quản lý SVG icon đổi màu theo theme.
Hỗ trợ WCAG AA contrast, cỡ chữ linh hoạt và màu nhấn (accent color).
"""

import os
import sys
import math
from enum import Enum
from typing import Optional, Dict, Any

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Qt, QByteArray, QSettings
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer


class ThemeMode(str, Enum):
    SYSTEM = "system"
    DARK = "dark"
    LIGHT = "light"


class FontSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


FONT_SIZES = {
    FontSize.SMALL: {
        "base": "12px",
        "small": "10px",
        "heading": "16px",
        "subheading": "11px",
        "code": "11px",
        "btn_padding": "6px 14px",
    },
    FontSize.MEDIUM: {
        "base": "13px",
        "small": "11px",
        "heading": "18px",
        "subheading": "12px",
        "code": "12px",
        "btn_padding": "8px 18px",
    },
    FontSize.LARGE: {
        "base": "15px",
        "small": "12px",
        "heading": "20px",
        "subheading": "13px",
        "code": "13px",
        "btn_padding": "10px 20px",
    },
}

ACCENT_PRESETS = {
    "Indigo": {"accent": "#6366F1", "hover": "#4F46E5", "active": "#4338CA", "light": "#818CF8"},
    "Cyan": {"accent": "#0284C7", "hover": "#0369A1", "active": "#075985", "light": "#38BDF8"},
    "Emerald": {"accent": "#059669", "hover": "#047857", "active": "#065F46", "light": "#34D399"},
    "Rose": {"accent": "#E11D48", "hover": "#BE123C", "active": "#9F1239", "light": "#FB7185"},
    "Amber": {"accent": "#D97706", "hover": "#B45309", "active": "#92400E", "light": "#FBBF24"},
    "Violet": {"accent": "#7C3AED", "hover": "#6D28D9", "active": "#5B21B6", "light": "#A78BFA"},
}

# SVG Icon Library (stroke-based with {color} placeholder)
SVG_ICONS = {
    "converter": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>'
        '</svg>'
    ),
    "downloader": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" y1="15" x2="12" y2="3"/>'
        '</svg>'
    ),
    "merger": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>'
        '<circle cx="12" cy="12" r="3"/>'
        '<line x1="12" y1="3" x2="12" y2="9"/>'
        '<line x1="12" y1="15" x2="12" y2="21"/>'
        '</svg>'
    ),
    "cutter": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/>'
        '<line x1="20" y1="4" x2="8.12" y2="15.88"/>'
        '<line x1="14.47" y1="14.48" x2="20" y2="20"/>'
        '<line x1="8.12" y1="8.12" x2="12" y2="12"/>'
        '</svg>'
    ),
    "settings": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
        '</svg>'
    ),
    "folder": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
        '</svg>'
    ),
    "play": (
        '<svg viewBox="0 0 24 24" fill="{color}" stroke="none">'
        '<polygon points="5 3 19 12 5 21 5 3"/>'
        '</svg>'
    ),
    "pause": (
        '<svg viewBox="0 0 24 24" fill="{color}" stroke="none">'
        '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
        '</svg>'
    ),
    "stop": (
        '<svg viewBox="0 0 24 24" fill="{color}" stroke="none">'
        '<rect x="5" y="5" width="14" height="14" rx="2" ry="2"/>'
        '</svg>'
    ),
    "trash": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '</svg>'
    ),
    "sun": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="5"/>'
        '<line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
        '</svg>'
    ),
    "moon": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
        '</svg>'
    ),
    "monitor": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>'
        '<line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
        '</svg>'
    ),
    "refresh": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
        '</svg>'
    ),
    "check": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.5" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="20 6 9 17 4 12"/>'
        '</svg>'
    ),
}

# Base Dark & Light Tokens adhering to WCAG AA Contrast (>= 4.5:1)
DARK_TOKENS = {
    "bg_app": "#121418",
    "bg_surface": "#181B20",
    "bg_card": "#1E2229",
    "bg_input": "#181B20",
    "bg_hover": "#262B34",
    "border": "#2D333E",
    "border_subtle": "#23272F",
    "text_main": "#F8FAFC",       # 17:1 on #121418
    "text_secondary": "#E2E8F0",  # 14.5:1
    "text_muted": "#94A3B8",      # 6.5:1 on #121418 (AA compliant)
    "text_dim": "#64748B",
    "accent_text": "#FFFFFF",
    "success": "#10B981",
    "success_bg": "#064E3B",
    "success_text": "#34D399",
    "warning": "#F59E0B",
    "warning_bg": "#78350F",
    "warning_text": "#FBBF24",
    "danger": "#EF4444",
    "danger_bg": "#7F1D1D",
    "danger_text": "#F87171",
    "log_bg": "#0D0F12",
    "log_text": "#CBD5E1",
    "scrollbar_bg": "#121418",
    "scrollbar_handle": "#2D333E",
    "scrollbar_handle_hover": "#4B5563",
    "table_alt": "#15181E",
    "empty_state_bg": "#14171D",
    "empty_state_border": "#2B303C",
}

LIGHT_TOKENS = {
    "bg_app": "#F8FAFC",
    "bg_surface": "#FFFFFF",
    "bg_card": "#FFFFFF",
    "bg_input": "#FFFFFF",
    "bg_hover": "#F1F5F9",
    "border": "#CBD5E1",
    "border_subtle": "#E2E8F0",
    "text_main": "#0F172A",       # 16.5:1 on #F8FAFC
    "text_secondary": "#1E293B",  # 14:1
    "text_muted": "#475569",      # 6.5:1 on #F8FAFC (AA compliant)
    "text_dim": "#64748B",
    "accent_text": "#FFFFFF",
    "success": "#059669",
    "success_bg": "#D1FAE5",
    "success_text": "#065F46",
    "warning": "#D97706",
    "warning_bg": "#FEF3C7",
    "warning_text": "#92400E",
    "danger": "#DC2626",
    "danger_bg": "#FEE2E2",
    "danger_text": "#991B1B",
    "log_bg": "#F1F5F9",
    "log_text": "#1E293B",
    "scrollbar_bg": "#F8FAFC",
    "scrollbar_handle": "#CBD5E1",
    "scrollbar_handle_hover": "#94A3B8",
    "table_alt": "#F8FAFC",
    "empty_state_bg": "#F8FAFC",
    "empty_state_border": "#CBD5E1",
}


QSS_TEMPLATE = """
/* ===================================================
   MediaStudio Pro - Dynamic Stylesheet (Theme: {effective_theme})
   =================================================== */

/* Cửa sổ toàn cục và font chữ */
QWidget {{
    background-color: {bg_app};
    color: {text_main};
    font-family: "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
    font-size: {font_base};
    selection-background-color: {accent};
    selection-color: {accent_text};
}}

QMainWindow, QDialog {{
    background-color: {bg_app};
}}

/* Sidebar bên trái */
#Sidebar {{
    background-color: {bg_surface};
    border-right: 1px solid {border_subtle};
}}

#SidebarTitle {{
    font-size: {font_heading};
    font-weight: bold;
    color: {text_main};
}}

#SidebarSubtitle {{
    font-size: {font_subheading};
    color: {accent};
    font-weight: 600;
}}

/* Nút bấm trên Sidebar */
QPushButton.sidebar-btn {{
    background-color: transparent;
    color: {text_muted};
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: {font_btn_padding};
    font-size: {font_base};
    font-weight: 500;
}}

QPushButton.sidebar-btn:hover {{
    background-color: {bg_hover};
    color: {text_main};
}}

QPushButton.sidebar-btn:checked, QPushButton.sidebar-btn.active {{
    background-color: {accent};
    color: {accent_text};
    font-weight: bold;
}}

/* Nút toggle Sidebar & Toggle Bottom */
#SidebarToggle, #BtnToggleBottom {{
    background-color: {bg_surface};
    color: {text_muted};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px 8px;
}}

#SidebarToggle:hover, #BtnToggleBottom:hover {{
    background-color: {bg_hover};
    color: {accent};
    border-color: {accent};
}}

/* Đường phân cách */
QFrame.separator {{
    color: {border_subtle};
    background-color: {border_subtle};
    height: 1px;
    margin: 4px 0;
    border: none;
}}

/* Khu vực làm việc chính (Workspace) */
#Workspace {{
    background-color: {bg_app};
    padding: 16px;
}}

/* Thẻ / Card Container */
QFrame.card {{
    background-color: {bg_card};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 16px;
}}

/* Tiêu đề mục */
QLabel.heading {{
    font-size: {font_heading};
    font-weight: bold;
    color: {text_main};
}}

QLabel.subheading {{
    font-size: {font_subheading};
    color: {text_muted};
}}

/* Label phụ */
QLabel.label-muted {{
    color: {text_muted};
    font-size: {font_small};
}}

QLabel.label-accent {{
    color: {accent};
    font-weight: 600;
}}

QLabel.label-success {{
    color: {success};
    font-weight: 500;
}}

QLabel.label-warning {{
    color: {warning};
    font-weight: 500;
}}

QLabel.label-danger {{
    color: {danger};
    font-weight: 500;
}}

QLabel.code-view {{
    font-family: "Consolas", "Courier New", monospace;
    color: {text_main};
}}

/* Thẻ lồng nhau (Nested Card) */
QFrame.card-nested {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 10px;
}}

/* Ô nhập liệu (QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox) */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
    background-color: {bg_input};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 12px;
    color: {text_main};
    font-size: {font_base};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
    border: 1px solid {accent};
    background-color: {bg_input};
}}

/* Nút bấm hành động tiêu chuẩn */
QPushButton.btn-primary {{
    background-color: {accent};
    color: {accent_text};
    border: none;
    border-radius: 8px;
    padding: {font_btn_padding};
    font-weight: 600;
    font-size: {font_base};
}}

QPushButton.btn-primary:hover {{
    background-color: {accent_hover};
}}

QPushButton.btn-primary:pressed {{
    background-color: {accent_active};
}}

QPushButton.btn-secondary {{
    background-color: {bg_hover};
    color: {text_main};
    border: 1px solid {border};
    border-radius: 8px;
    padding: {font_btn_padding};
    font-weight: 500;
    font-size: {font_base};
}}

QPushButton.btn-secondary:hover {{
    background-color: {bg_surface};
    border-color: {accent};
    color: {accent};
}}

QPushButton.btn-danger {{
    background-color: {danger};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: {font_btn_padding};
    font-weight: 600;
    font-size: {font_base};
}}

QPushButton.btn-danger:hover {{
    background-color: {danger_text};
}}

/* Thanh tiến trình (ProgressBar) */
QProgressBar {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 6px;
    text-align: center;
    color: {text_main};
    font-weight: bold;
    height: 16px;
    font-size: {font_small};
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent_light});
    border-radius: 5px;
}}

/* Bảng điều khiển Log Console */
#LogConsole {{
    background-color: {bg_surface};
    border-top: 1px solid {border_subtle};
}}

#LogDisplay {{
    background-color: {log_bg};
    border: 1px solid {border_subtle};
    border-radius: 6px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: {font_code};
    color: {log_text};
    padding: 6px;
}}

/* QScrollBar */
QScrollBar:vertical {{
    border: none;
    background-color: {scrollbar_bg};
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: {scrollbar_handle};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {scrollbar_handle_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background-color: {scrollbar_bg};
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: {scrollbar_handle};
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {scrollbar_handle_hover};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ComboBox */
QComboBox {{
    background-color: {bg_input};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 12px;
    color: {text_main};
    font-size: {font_base};
}}

QComboBox:hover {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {bg_surface};
    border: 1px solid {border};
    selection-background-color: {accent};
    selection-color: {accent_text};
    color: {text_main};
    padding: 4px;
}}

/* QTableWidget & QHeaderView */
QTableWidget, QTableView {{
    background-color: {bg_card};
    alternate-background-color: {table_alt};
    color: {text_main};
    gridline-color: {border_subtle};
    border: 1px solid {border};
    border-radius: 8px;
    selection-background-color: {accent};
    selection-color: {accent_text};
    font-size: {font_base};
}}

QHeaderView::section {{
    background-color: {bg_surface};
    color: {text_muted};
    font-weight: 600;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {border};
    border-right: 1px solid {border_subtle};
    font-size: {font_small};
}}

QTableCornerButton::section {{
    background-color: {bg_surface};
    border: none;
    border-bottom: 1px solid {border};
}}

/* QToolTip */
QToolTip {{
    background-color: {bg_card};
    color: {text_main};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {font_small};
}}

/* QMenu & QMenuBar */
QMenuBar {{
    background-color: {bg_surface};
    color: {text_main};
    border-bottom: 1px solid {border_subtle};
}}

QMenuBar::item:selected {{
    background-color: {bg_hover};
    color: {accent};
}}

QMenu {{
    background-color: {bg_surface};
    color: {text_main};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 20px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {accent};
    color: {accent_text};
}}

/* QTabWidget & QTabBar */
QTabWidget::pane {{
    border: 1px solid {border};
    background-color: {bg_surface};
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: {bg_app};
    color: {text_muted};
    padding: 6px 16px;
    font-size: {font_small};
    font-weight: 600;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    border: 1px solid transparent;
}}

QTabBar::tab:selected {{
    background-color: {bg_surface};
    color: {text_main};
    border: 1px solid {border};
    border-bottom: none;
    border-top: 2px solid {accent};
}}

QTabBar::tab:hover:!selected {{
    background-color: {bg_hover};
    color: {text_main};
}}

/* QSplitter */
QSplitter::handle:vertical {{
    background-color: {bg_surface};
    height: 6px;
    margin: 1px 0px;
    border-top: 1px solid {border_subtle};
    border-bottom: 1px solid {border_subtle};
}}

QSplitter::handle:vertical:hover {{
    background-color: {accent};
}}

QSplitter::handle:horizontal {{
    background-color: {bg_surface};
    width: 6px;
    margin: 0px 1px;
    border-left: 1px solid {border_subtle};
    border-right: 1px solid {border_subtle};
}}

QSplitter::handle:horizontal:hover {{
    background-color: {accent};
}}

/* QScrollArea */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* Checkbox & Radio */
QCheckBox, QRadioButton {{
    color: {text_main};
    spacing: 8px;
    font-size: {font_base};
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border};
    border-radius: 4px;
    background-color: {bg_input};
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {accent};
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}

/* QSlider (Player Controls / Seekbar / Volume) */
QSlider::groove:horizontal {{
    height: 6px;
    background: {border};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {accent_text};
    border: 2px solid {accent};
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {accent};
    border-color: {accent_text};
}}

/* Empty State Widget */
#EmptyStateWidget {{
    background-color: {empty_state_bg};
    border: 1px dashed {empty_state_border};
    border-radius: 8px;
    padding: 16px;
}}

#EmptyStateWidget:hover {{
    border-color: {accent};
}}

#EmptyStateTitle {{
    font-size: {font_base};
    font-weight: bold;
    color: {text_main};
    background: transparent;
}}

#EmptyStateSubtitle {{
    font-size: {font_small};
    color: {text_muted};
    background: transparent;
}}

/* Job Queue Panel & Status Badges */
#JobItemWidget {{
    background-color: {bg_surface};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 4px;
}}

.status-badge {{
    font-size: 10px;
    font-weight: bold;
    border-radius: 4px;
    padding: 2px 6px;
}}

.status-queued {{
    background-color: {bg_hover};
    color: {text_muted};
}}

.status-running {{
    background-color: {warning_bg};
    color: {warning_text};
}}

.status-success {{
    background-color: {success_bg};
    color: {success_text};
}}

.status-failed {{
    background-color: {danger_bg};
    color: {danger_text};
}}

.status-paused {{
    background-color: {bg_hover};
    color: {text_muted};
}}

.status-cancelled {{
    background-color: {bg_hover};
    color: {text_dim};
}}
"""


class ThemeManager(QObject):
    """
    Singleton ThemeManager điều phối giao diện sáng/tối/theo hệ thống,
    cỡ chữ, màu nhấn và sinh CSS động.
    """
    theme_changed = Signal(str)  # Emits "dark" or "light"

    _instance: Optional["ThemeManager"] = None

    def __init__(self):
        super().__init__()
        self.settings = QSettings("MediaStudio", "MediaStudioPro")
        self._mode = self.settings.value("theme_mode", ThemeMode.SYSTEM.value, type=str)
        self._font_size = self.settings.value("font_size", FontSize.MEDIUM.value, type=str)
        self._accent_name = self.settings.value("accent_preset", "Indigo", type=str)
        self._custom_accent = self.settings.value("accent_color", "#6366F1", type=str)
        self._app: Optional[QApplication] = None
        self._connected_hints = False

    @classmethod
    def get_instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def init_app(self, app: QApplication):
        """Khởi tạo và kết nối ThemeManager với QApplication."""
        self._app = app

        # Lắng nghe thay đổi theme từ hệ thống qua QGuiApplication.styleHints() (Qt >= 6.5)
        if not self._connected_hints:
            try:
                style_hints = QGuiApplication.styleHints()
                if hasattr(style_hints, "colorSchemeChanged"):
                    style_hints.colorSchemeChanged.connect(self._on_system_scheme_changed)
                    self._connected_hints = True
            except Exception as e:
                print(f"[ThemeManager] Không thể lắng nghe colorSchemeChanged: {e}")

        self.apply_theme()

    def _on_system_scheme_changed(self, scheme):
        if self._mode == ThemeMode.SYSTEM.value:
            self.apply_theme()

    def get_system_theme(self) -> str:
        """
        Xác định theme của hệ điều hành:
        1. Thử QGuiApplication.styleHints().colorScheme() (Qt >= 6.5)
        2. Fallback: Đọc Windows Registry AppsUseLightTheme
        3. Fallback mặc định: "dark"
        """
        # 1. Qt 6.5+ styleHints
        try:
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "colorScheme"):
                scheme = hints.colorScheme()
                if hasattr(Qt, "ColorScheme"):
                    if scheme == Qt.ColorScheme.Dark:
                        return "dark"
                    elif scheme == Qt.ColorScheme.Light:
                        return "light"
        except Exception:
            pass

        # 2. Windows Registry Fallback
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if val == 1 else "dark"
            except Exception:
                pass

        return "dark"

    def get_effective_theme(self) -> str:
        """Trả về theme thực sự áp dụng: 'dark' hoặc 'light'."""
        if self._mode == ThemeMode.SYSTEM.value:
            return self.get_system_theme()
        return self._mode

    def is_dark(self) -> bool:
        return self.get_effective_theme() == "dark"

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def font_size(self) -> str:
        return self._font_size

    @property
    def accent_name(self) -> str:
        return self._accent_name

    def set_mode(self, mode: str):
        if mode in [ThemeMode.SYSTEM.value, ThemeMode.DARK.value, ThemeMode.LIGHT.value]:
            self._mode = mode
            self.settings.setValue("theme_mode", mode)
            self.apply_theme()

    def set_font_size(self, size: str):
        if size in [FontSize.SMALL.value, FontSize.MEDIUM.value, FontSize.LARGE.value]:
            self._font_size = size
            self.settings.setValue("font_size", size)
            self.apply_theme()

    def set_accent_preset(self, name: str):
        if name in ACCENT_PRESETS:
            self._accent_name = name
            preset = ACCENT_PRESETS[name]
            self._custom_accent = preset["accent"]
            self.settings.setValue("accent_preset", name)
            self.settings.setValue("accent_color", preset["accent"])
            self.apply_theme()

    def get_tokens(self) -> Dict[str, Any]:
        """Tạo bảng token tổng hợp từ theme, font-size và accent hiện tại."""
        eff = self.get_effective_theme()
        base_tokens = dict(DARK_TOKENS if eff == "dark" else LIGHT_TOKENS)

        # Merge Accent
        preset = ACCENT_PRESETS.get(self._accent_name, ACCENT_PRESETS["Indigo"])
        base_tokens["accent"] = preset["accent"]
        base_tokens["accent_hover"] = preset["hover"]
        base_tokens["accent_active"] = preset["active"]
        base_tokens["accent_light"] = preset["light"]

        # Merge Font Sizes
        f_size_enum = FontSize(self._font_size) if self._font_size in [f.value for f in FontSize] else FontSize.MEDIUM
        f_data = FONT_SIZES[f_size_enum]
        base_tokens["font_base"] = f_data["base"]
        base_tokens["font_small"] = f_data["small"]
        base_tokens["font_heading"] = f_data["heading"]
        base_tokens["font_subheading"] = f_data["subheading"]
        base_tokens["font_code"] = f_data["code"]
        base_tokens["font_btn_padding"] = f_data["btn_padding"]
        base_tokens["effective_theme"] = eff

        return base_tokens

    def generate_qss(self) -> str:
        """Sinh stylesheet QSS động từ template và bảng token."""
        tokens = self.get_tokens()
        return QSS_TEMPLATE.format(**tokens)

    def apply_theme(self):
        """Áp dụng stylesheet cho toàn bộ ứng dụng và phát tín hiệu theme_changed."""
        app = self._app or QApplication.instance()
        if app:
            qss = self.generate_qss()
            app.setStyleSheet(qss)
        self.theme_changed.emit(self.get_effective_theme())

    def get_svg_icon(self, name_or_svg: str, color: Optional[str] = None, size: int = 20) -> QIcon:
        """
        Tạo QIcon từ vector SVG, recolor theo màu chỉ định (hoặc theo theme).
        """
        if color is None:
            tokens = self.get_tokens()
            color = tokens["text_muted"]

        svg_data = SVG_ICONS.get(name_or_svg, name_or_svg)
        svg_colored = svg_data.replace("{color}", color).replace("currentColor", color)
        if not svg_colored.strip().startswith("<svg"):
            return QIcon()

        try:
            renderer = QSvgRenderer(QByteArray(svg_colored.encode("utf-8")))
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return QIcon(pixmap)
        except Exception as e:
            return QIcon()

    def get_log_color(self, level: str) -> str:
        """Trả về mã màu log phù hợp với theme hiện tại."""
        tokens = self.get_tokens()
        lvl = level.upper()
        if "SUCCESS" in lvl:
            return tokens["success_text"]
        elif "WARN" in lvl:
            return tokens["warning_text"]
        elif "ERR" in lvl or "FAIL" in lvl:
            return tokens["danger_text"]
        elif "INFO" in lvl:
            return tokens["accent_light"] if self.is_dark() else tokens["accent"]
        return tokens["text_muted"]
