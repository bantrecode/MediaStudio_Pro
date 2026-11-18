"""
Unit tests for ThemeManager (ui/theme.py)
Kiểm thử hệ thống Theme Sáng / Tối / Theo hệ thống, bảng tokens,
sinh QSS động, recolor SVG icon và độ tương phản WCAG AA.
"""

import pytest
from ui.theme import (
    ThemeManager, ThemeMode, FontSize, ACCENT_PRESETS,
    DARK_TOKENS, LIGHT_TOKENS, SVG_ICONS
)


def _hex_to_rgb(hex_str: str):
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb):
    def channel(c):
        c_norm = c / 255.0
        return c_norm / 12.92 if c_norm <= 0.03928 else ((c_norm + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _relative_luminance(_hex_to_rgb(hex1))
    l2 = _relative_luminance(_hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_theme_manager_singleton():
    tm1 = ThemeManager.get_instance()
    tm2 = ThemeManager.get_instance()
    assert tm1 is tm2


def test_wcag_aa_contrast():
    """Kiểm tra độ tương phản văn bản so với nền theo chuẩn WCAG AA (>= 4.5:1)."""
    # 1. Dark Mode
    dark_main_contrast = _contrast_ratio(DARK_TOKENS["text_main"], DARK_TOKENS["bg_app"])
    assert dark_main_contrast >= 4.5, f"Dark text_main contrast {dark_main_contrast} < 4.5"

    dark_muted_contrast = _contrast_ratio(DARK_TOKENS["text_muted"], DARK_TOKENS["bg_app"])
    assert dark_muted_contrast >= 4.5, f"Dark text_muted contrast {dark_muted_contrast} < 4.5"

    # 2. Light Mode
    light_main_contrast = _contrast_ratio(LIGHT_TOKENS["text_main"], LIGHT_TOKENS["bg_app"])
    assert light_main_contrast >= 4.5, f"Light text_main contrast {light_main_contrast} < 4.5"

    light_muted_contrast = _contrast_ratio(LIGHT_TOKENS["text_muted"], LIGHT_TOKENS["bg_app"])
    assert light_muted_contrast >= 4.5, f"Light text_muted contrast {light_muted_contrast} < 4.5"


def test_theme_mode_switching():
    tm = ThemeManager.get_instance()

    tm.set_mode(ThemeMode.DARK.value)
    assert tm.mode == ThemeMode.DARK.value
    assert tm.get_effective_theme() == "dark"
    assert tm.is_dark() is True

    tm.set_mode(ThemeMode.LIGHT.value)
    assert tm.mode == ThemeMode.LIGHT.value
    assert tm.get_effective_theme() == "light"
    assert tm.is_dark() is False

    tm.set_mode(ThemeMode.SYSTEM.value)
    assert tm.mode == ThemeMode.SYSTEM.value
    assert tm.get_effective_theme() in ["dark", "light"]


def test_font_size_and_accent_switching():
    tm = ThemeManager.get_instance()

    tm.set_font_size(FontSize.LARGE.value)
    assert tm.font_size == FontSize.LARGE.value

    tokens = tm.get_tokens()
    assert tokens["font_base"] == "15px"

    tm.set_accent_preset("Emerald")
    assert tm.accent_name == "Emerald"
    tokens = tm.get_tokens()
    assert tokens["accent"] == ACCENT_PRESETS["Emerald"]["accent"]


def test_qss_generation():
    tm = ThemeManager.get_instance()
    tm.set_mode(ThemeMode.DARK.value)
    qss_dark = tm.generate_qss()
    assert "#121418" in qss_dark
    assert "QTableWidget" in qss_dark
    assert "QScrollBar" in qss_dark
    assert "QProgressBar" in qss_dark
    assert "#EmptyStateWidget" in qss_dark
    assert "#JobItemWidget" in qss_dark

    tm.set_mode(ThemeMode.LIGHT.value)
    qss_light = tm.generate_qss()
    assert "#F8FAFC" in qss_light
    assert "#0F172A" in qss_light


def test_svg_icon_rendering():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    tm = ThemeManager.get_instance()
    for name in ["converter", "downloader", "merger", "cutter", "settings", "trash", "sun", "moon"]:
        icon = tm.get_svg_icon(name, color="#6366F1", size=24)
        assert not icon.isNull(), f"Icon {name} rendering failed"


def test_log_colors():
    tm = ThemeManager.get_instance()
    tm.set_mode(ThemeMode.DARK.value)
    assert tm.get_log_color("SUCCESS") == DARK_TOKENS["success_text"]
    assert tm.get_log_color("ERROR") == DARK_TOKENS["danger_text"]
    assert tm.get_log_color("WARNING") == DARK_TOKENS["warning_text"]
