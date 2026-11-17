"""
Build Automation Script for All-in-One Media Studio
Tự động dọn dẹp thư mục cũ, kiểm tra phụ thuộc và chạy PyInstaller đóng gói chế độ --onedir.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Thư mục gốc dự án
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent


def print_step(msg: str):
    print(f"\n[+] =========================================")
    print(f"[+] {msg}")
    print(f"[+] =========================================")


def check_prerequisites():
    print_step("Kiểm tra môi trường build...")

    # 1. Kiểm tra Python
    py_ver = sys.version_info
    print(f"Python: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 10):
        print("[-] CẢNH BÁO: Khuyến nghị sử dụng Python 3.10 trở lên.")

    # 2. Kiểm tra PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("[-] LỖI: PyInstaller chưa được cài đặt. Hãy chạy: pip install pyinstaller")
        sys.exit(1)

    # 3. Kiểm tra PySide6
    try:
        import PySide6
        print(f"PySide6 version: {PySide6.__version__}")
    except ImportError:
        print("[-] LỖI: PySide6 chưa được cài đặt. Hãy chạy: pip install PySide6")
        sys.exit(1)

    # 4. Kiểm tra file ffmpeg.exe trong assets/bin/
    bin_dir = ROOT_DIR / "assets" / "bin"
    ffmpeg_file = bin_dir / "ffmpeg.exe"
    ffprobe_file = bin_dir / "ffprobe.exe"
    ytdlp_file = bin_dir / "yt-dlp.exe"

    if ffmpeg_file.exists() and ffprobe_file.exists():
        print(f"[+] Đã tìm thấy ffmpeg.exe và ffprobe.exe trong {bin_dir} (Sẵn sàng đóng gói offline 100%)")
    else:
        print(f"[!] LƯU Ý: Chưa có ffmpeg.exe/ffprobe.exe trong thư mục: {bin_dir}")

    if ytdlp_file.exists():
        print(f"[+] Đã tìm thấy yt-dlp.exe trong {bin_dir}")


def clean_previous_builds():
    print_step("Dọn dẹp thư mục dist cũ...")
    dist_dir = ROOT_DIR / "dist"
    if dist_dir.exists():
        print(f"Đang xóa thư mục: {dist_dir}...")
        try:
            shutil.rmtree(dist_dir)
        except Exception as e:
            print(f"[!] Không thể xóa {dist_dir}: {e}")


def run_pyinstaller():
    print_step("Đang chạy PyInstaller (--onedir)...")
    spec_file = SCRIPT_DIR / "app.spec"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--noconfirm",
        "--clean"
    ]

    print(f"Thực thi lệnh: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if result.returncode != 0:
        print(f"[-] LỖI: Quá trình build PyInstaller thất bại với mã lỗi {result.returncode}")
        sys.exit(result.returncode)


def verify_output():
    print_step("Kiểm tra tính toàn vẹn của bản build...")
    dist_dir = ROOT_DIR / "dist" / "MediaStudio"
    exe_file = dist_dir / "MediaStudio.exe"

    if not exe_file.exists():
        print("[-] LỖI: Không tìm thấy file MediaStudio.exe sau khi build!")
        sys.exit(1)

    # Tính toán tổng dung lượng bản build
    total_size = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)

    print(f"\n[SUCCESS] ĐÓNG GÓI THÀNH CÔNG!")
    print(f"[+] Thư mục ứng dụng: {dist_dir}")
    print(f"[+] File thực thi: {exe_file}")
    print(f"[+] Tổng dung lượng gói: {size_mb:.1f} MB")
    print(f"\n[+] Để chạy thử bản build: & '{exe_file}'")


def clean_intermediate_builds():
    """Xóa thư mục cache tạm build/app để tránh người dùng click nhầm file exe tạm."""
    temp_build = ROOT_DIR / "build" / "app"
    if temp_build.exists():
        print(f"[+] Dọn dẹp cache tạm: {temp_build}")
        try:
            shutil.rmtree(temp_build)
        except Exception:
            pass


def create_portable_zip():
    print_step("Đang tạo gói nén Portable ZIP để gửi sang máy tính khác...")
    dist_dir = ROOT_DIR / "dist" / "MediaStudio"
    zip_output = ROOT_DIR / "dist" / "MediaStudio_Portable"
    if dist_dir.exists():
        try:
            print(f"Đang nén {dist_dir} ➔ {zip_output}.zip ...")
            archive_path = shutil.make_archive(
                base_name=str(zip_output),
                format="zip",
                root_dir=str(ROOT_DIR / "dist"),
                base_dir="MediaStudio"
            )
            zip_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
            print(f"[+] ĐÃ TẠO FILE NÉN THÀNH CÔNG: {archive_path} ({zip_size_mb:.1f} MB)")
            print(f"[+] Bạn có thể gửi file .zip này sang bất kỳ máy tính Windows khác để chạy ngay!")
        except Exception as e:
            print(f"[!] Lỗi khi nén ZIP: {e}")


def main():
    check_prerequisites()
    clean_previous_builds()
    run_pyinstaller()
    clean_intermediate_builds()
    verify_output()
    create_portable_zip()


if __name__ == "__main__":
    main()

