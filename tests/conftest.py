"""
Pytest Fixtures for Core Testing
"""

import sys
import os
import pytest
from pathlib import Path

# Đảm bảo import được core/ từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def temp_test_dir(tmp_path):
    """Fixture cung cấp thư mục tạm sạch cho mỗi test case."""
    test_dir = tmp_path / "mediastudio_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir

