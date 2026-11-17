"""
Unit tests cho core/system.py
Kiểm tra: clean_unicode_filename, check_disk_space, CREATE_NO_WINDOW, get_appdata_dir.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

import sys
import os
from pathlib import Path
from core.system import (
    clean_unicode_filename,
    check_disk_space,
    format_bytes,
    CREATE_NO_WINDOW,
    get_appdata_dir,
    get_subprocess_kwargs
)


def test_clean_unicode_filename():
    raw_name = "Video Hướng Dẫn Cắt Ghép & Chuyển Đổi [4K] : 2026?.mp4"
    cleaned = clean_unicode_filename(raw_name)

    # Không được chứa ký tự tiếng Việt có dấu
    assert "ướ" not in cleaned
    assert "ắ" not in cleaned
    assert "Đ" not in cleaned

    # Không được chứa ký tự cấm trên Windows
    for invalid in [":", "?", "*", "<", ">", "|", "/", "\\"]:
        assert invalid not in cleaned

    assert cleaned.endswith(".mp4")


def test_clean_filename_length_limit():
    long_name = "A" * 300 + ".mp4"
    cleaned = clean_unicode_filename(long_name)
    assert len(cleaned) <= 180


def test_check_disk_space():
    has_space, free_bytes, total_bytes = check_disk_space(".", required_bytes=1024)
    assert isinstance(has_space, bool)
    assert free_bytes > 0
    assert total_bytes > 0


def test_format_bytes():
    assert format_bytes(500) == "500.0 B"
    assert "MB" in format_bytes(5 * 1024 * 1024)
    assert "GB" in format_bytes(2 * 1024 * 1024 * 1024)


def test_create_no_window_flag():
    kwargs = get_subprocess_kwargs()
    if sys.platform == "win32":
        assert CREATE_NO_WINDOW == 0x08000000
        assert kwargs.get("creationflags") == 0x08000000
    else:
        assert kwargs == {}


def test_get_appdata_dir():
    appdata = get_appdata_dir()
    assert isinstance(appdata, Path)
    assert appdata.exists()


def test_resource_path():
    from core.system import resource_path
    p = resource_path("assets/bin")
    assert isinstance(p, Path)
    assert "assets" in str(p)

