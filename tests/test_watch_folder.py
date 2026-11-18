"""
Unit tests for Watch Folder Service (core/watch_folder.py)
"""

import tempfile
import time
from pathlib import Path
from core.watch_folder import WatchFolderService


def test_watch_folder_service_lifecycle():
    service = WatchFolderService.get_instance()
    assert not service.is_running

    service.start()
    assert service.is_running

    service.stop()
    assert not service.is_running


def test_watch_folder_file_readiness():
    service = WatchFolderService.get_instance()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"SAMPLE DATA CONTENT")
        temp_file = Path(tf.name)

    try:
        # Chu kỳ 1: phát hiện lần đầu -> False
        ready_1 = service._is_file_ready(temp_file)
        assert not ready_1

        # Chu kỳ 2: kích thước không đổi -> True
        ready_2 = service._is_file_ready(temp_file)
        assert ready_2
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
