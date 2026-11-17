"""
Helper script to download ffmpeg.exe, ffprobe.exe and yt-dlp.exe
into assets/bin/ for development and build.
"""

import os
import sys
import urllib.request
from pathlib import Path

BIN_DIR = Path(__file__).resolve().parent

def download_file(url: str, target_path: Path):
    print(f"Đang tải {target_path.name} từ {url}...")
    try:
        urllib.request.urlretrieve(url, str(target_path))
        print(f"[+] Đã tải thành công: {target_path}")
    except Exception as e:
        print(f"[-] Lỗi khi tải {target_path.name}: {e}")

def main():
    os.makedirs(BIN_DIR, exist_ok=True)

    ytdlp_path = BIN_DIR / "yt-dlp.exe"
    if not ytdlp_path.exists():
        download_file("https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe", ytdlp_path)
    else:
        print(f"[i] yt-dlp.exe đã tồn tại trong {BIN_DIR}")

    ffmpeg_path = BIN_DIR / "ffmpeg.exe"
    ffprobe_path = BIN_DIR / "ffprobe.exe"
    if not ffmpeg_path.exists() or not ffprobe_path.exists():
        print(f"\n[!] Lưu ý về FFmpeg:")
        print(f"Vui lòng copy file ffmpeg.exe và ffprobe.exe vào thư mục:")
        print(f"👉 {BIN_DIR}")
        print(f"Hoặc tải bản release chính thức tại: https://www.gyan.dev/ffmpeg/builds/")
    else:
        print(f"[i] ffmpeg.exe và ffprobe.exe đã có sẵn.")

if __name__ == "__main__":
    main()
