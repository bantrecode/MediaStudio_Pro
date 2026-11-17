"""
Config Core Module
Quản lý cấu hình ứng dụng lưu trữ tại %APPDATA%\\MediaStudio\\settings.json.
Hỗ trợ load, save, cập nhật và phục hồi khi file JSON lỗi.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import json
from pathlib import Path
from typing import Dict, Any
from core.system import get_appdata_dir


CURRENT_SCHEMA_VERSION = 1

DEFAULT_SETTINGS: Dict[str, Any] = {
    "schema_version": CURRENT_SCHEMA_VERSION,
    "default_output_dir": str(Path.home() / "Downloads"),
    "naming_pattern": "{title}_{date}",
    "proxy": "",
    "max_concurrent_jobs": 2,
    "gpu_preference": "auto",  # 'auto', 'nvidia', 'intel', 'amd', 'cpu'
    "theme": "dark",
    "language": "vi",
    "auto_clipboard": True,
    "shutdown_when_finished": False,
    "play_sound_when_finished": True,
}


class ConfigManager:
    _instance = None

    def __init__(self):
        self.config_file = get_appdata_dir() / "settings.json"
        self._settings = dict(DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    def load(self) -> Dict[str, Any]:
        """Nạp cấu hình từ đĩa. Nếu chưa có hoặc hỏng, tạo mới mặc định."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        # Kiểm tra và nâng cấp schema nếu cần
                        loaded_version = loaded.get("schema_version", 0)
                        if loaded_version < CURRENT_SCHEMA_VERSION:
                            loaded["schema_version"] = CURRENT_SCHEMA_VERSION

                        # Cập nhật các key mới nếu default có mà loaded chưa có
                        for k, v in DEFAULT_SETTINGS.items():
                            if k not in loaded:
                                loaded[k] = v
                        self._settings = loaded
                        return self._settings
            except Exception:
                # Sao lưu file hỏng và khôi phục mặc định
                bad_file = self.config_file.with_suffix(".json.bad")
                try:
                    self.config_file.rename(bad_file)
                except Exception:
                    pass

        self._settings = dict(DEFAULT_SETTINGS)
        self.save()
        return self._settings

    def save(self) -> bool:
        """Lưu cấu hình hiện tại xuống đĩa."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return dict(self._settings)

    def update_all(self, new_settings: Dict[str, Any]) -> None:
        self._settings.update(new_settings)
        self.save()

