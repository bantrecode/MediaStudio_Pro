# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec Configuration for All-in-One Media Studio
Chế độ: --onedir (phân phối thư mục độc lập, giảm thiểu tối đa False Positive Antivirus)
Không dùng UPX nén exe để tránh bị Windows Defender gắn cờ mã độc giả.
"""

import os
import sys
from pathlib import Path

# Thư mục gốc của dự án
SPEC_DIR = Path(os.path.abspath(SPEC)).parent
ROOT_DIR = SPEC_DIR.parent

block_cipher = None

# Thu thập dữ liệu tĩnh (Assets, stylesheet, nhị phân bin/)
datas = [
    (str(ROOT_DIR / 'assets'), 'assets'),
]

# Hidden imports cần thiết cho PySide6 và các thư viện hệ thống
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'psutil',
    'sqlite3',
    'urllib.request',
    'json',
    'uuid',
    'shutil',
    'subprocess',
]

# Loại bỏ các thư viện nặng không dùng đến để giảm dung lượng bản build
excludes = [
    'tkinter',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'IPython',
    'notebook',
    'pytest',
    '_pytest',
    'unittest',
]

a = Analysis(
    [str(ROOT_DIR / 'main.py')],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Đường dẫn icon nếu có
icon_file = ROOT_DIR / 'assets' / 'app_icon.ico'
icon_path = str(icon_file) if icon_file.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MediaStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # BẮT BUỘC False: UPX là nguyên nhân số 1 gây cảnh báo Antivirus giả
    console=False,  # Chạy giao diện GUI, không bật console đen
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MediaStudio',
)

