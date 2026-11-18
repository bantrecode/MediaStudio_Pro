"""
Unit tests for i18n & Translations (core/i18n.py)
"""

from core.i18n import I18nManager, tr


def test_i18n_translation():
    mgr = I18nManager.get_instance()

    # Mặc định tiếng Việt
    mgr.set_language("vi")
    assert tr("Converter") == "Chuyển Đổi Định Dạng"
    assert tr("Job Queue") == "Hàng Đợi Tác Vụ"
    assert tr("PENDING") == "Đang chờ"

    # Chuyển sang tiếng Anh
    mgr.set_language("en")
    assert tr("Converter") == "Media Converter"
    assert tr("Job Queue") == "Job Queue"
    assert tr("PENDING") == "Pending"

    # Reset về tiếng Việt
    mgr.set_language("vi")
    assert tr("Converter") == "Chuyển Đổi Định Dạng"
