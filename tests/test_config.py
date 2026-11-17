"""
Unit tests cho core/config.py
Kiểm tra: Nạp, lưu, cập nhật và khôi phục khi file cấu hình JSON lỗi.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

import json
from pathlib import Path
from core.config import ConfigManager, DEFAULT_SETTINGS


def test_config_load_and_defaults(temp_test_dir, monkeypatch):
    test_json = temp_test_dir / "settings.json"
    monkeypatch.setattr("core.config.get_appdata_dir", lambda: temp_test_dir)

    cfg = ConfigManager()
    assert cfg.get("max_concurrent_jobs") == 2
    assert cfg.get("theme") == "dark"
    assert cfg.get("schema_version") == 1
    assert test_json.exists()


def test_config_save_and_update(temp_test_dir, monkeypatch):
    monkeypatch.setattr("core.config.get_appdata_dir", lambda: temp_test_dir)

    cfg = ConfigManager()
    cfg.set("max_concurrent_jobs", 4)
    assert cfg.get("max_concurrent_jobs") == 4

    # Khởi tạo instance mới để kiểm tra tính bền vững ghi vào file
    cfg2 = ConfigManager()
    assert cfg2.get("max_concurrent_jobs") == 4


def test_config_corrupted_file_recovery(temp_test_dir, monkeypatch):
    test_json = temp_test_dir / "settings.json"
    monkeypatch.setattr("core.config.get_appdata_dir", lambda: temp_test_dir)

    # Ghi nội dung JSON rác vào file
    test_json.write_text("{ CORRUPTED_JSON_CONTENT !!! ", encoding="utf-8")

    cfg = ConfigManager()
    # Phải tự khôi phục về default mà không crash
    assert cfg.get("max_concurrent_jobs") == DEFAULT_SETTINGS["max_concurrent_jobs"]
    assert (temp_test_dir / "settings.json.bad").exists()

