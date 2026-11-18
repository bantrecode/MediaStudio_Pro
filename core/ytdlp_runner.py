"""
yt-dlp Runner Core Module (CLI Subprocess Mode)
Chạy yt-dlp dưới dạng tiến trình độc lập (yt-dlp.exe) qua subprocess:
- Ưu tiên: %APPDATA%\\MediaStudio\\bin\\yt-dlp.exe (bản cập nhật mới nhất)
  -> assets/bin/yt-dlp.exe (bản đóng gói offline)
  -> PATH hệ thống
- Tự động liên kết --ffmpeg-location tới ffmpeg của app
- Hỗ trợ hủy sạch cây tiến trình bằng psutil (kill_process_tree)
- Parse tiến độ chuẩn xác qua stdout UTF-8 (encoding="utf-8", errors="replace")
- Hỗ trợ tải và tự động cập nhật bản yt-dlp mới nhất từ GitHub
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
import sys
import json
import re
import threading
import urllib.request
import subprocess
from typing import Dict, Any, List, Optional, Callable, Tuple
from core.system import (
    get_binary_path, get_custom_bin_dir, get_subprocess_kwargs,
    clean_unicode_filename, kill_process_tree
)
from core.logger import get_logger


class YtDlpRunner:
    """Quản lý việc chạy yt-dlp.exe độc lập và cập nhật nhị phân."""

    def __init__(self, cmd_args: List[str], output_dir: Optional[str] = None):
        self.cmd_args = cmd_args
        self.output_dir = output_dir
        self.process: Optional[subprocess.Popen] = None
        self.is_cancelled = False

    def cancel(self):
        """Hủy toàn bộ cây tiến trình yt-dlp ngay lập tức."""
        self.is_cancelled = True
        logger = get_logger()
        logger.info("Đang hủy tiến trình yt-dlp...")
        if self.process and self.process.poll() is None:
            kill_process_tree(self.process.pid)

    def run(
        self,
        on_progress: Optional[Callable[[int, str, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Thực thi yt-dlp qua subprocess với cờ CREATE_NO_WINDOW và encoding UTF-8 an toàn.
        """
        logger = get_logger()
        ytdlp_bin = get_binary_path("yt-dlp")
        ffmpeg_bin = get_binary_path("ffmpeg")

        # Kiểm tra nhị phân yt-dlp.exe, nếu chưa có thì fallback sang sys.executable -m yt_dlp
        if os.path.exists(ytdlp_bin):
            base_cmd = [ytdlp_bin]
        else:
            base_cmd = [sys.executable, "-m", "yt_dlp"]

        # Cấu hình lệnh đầy đủ
        full_cmd = base_cmd + [
            "--ffmpeg-location", ffmpeg_bin,
            "--newline",
            "--progress-template", "download:[PROGRESS]:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        ] + self.cmd_args

        if on_log:
            on_log(f"Khởi chạy yt-dlp: {ytdlp_bin} (với ffmpeg: {ffmpeg_bin})")

        try:
            self.process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **get_subprocess_kwargs()
            )
        except Exception as e:
            err = f"Không thể khởi động yt-dlp: {e}"
            logger.error(err)
            if on_log:
                on_log(f"[ERROR] {err}")
            return False, err

        stderr_lines: List[str] = []

        def _drain_stderr():
            try:
                for s_line in iter(self.process.stderr.readline, ""):
                    if not s_line:
                        break
                    clean_s = s_line.strip()
                    if clean_s:
                        stderr_lines.append(clean_s)
                        if len(stderr_lines) > 200:
                            stderr_lines.pop(0)
            except Exception:
                pass

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        # Đọc stdout thời gian thực
        try:
            while self.process.poll() is None:
                if self.is_cancelled:
                    break

                line = self.process.stdout.readline()
                if not line:
                    continue

                line_str = line.strip()

                # Bắt mẫu progress template
                if "[PROGRESS]:" in line_str:
                    try:
                        payload = line_str.split("[PROGRESS]:", 1)[1]
                        parts = payload.split("|")
                        if len(parts) >= 3:
                            pct_raw, speed_raw, eta_raw = parts[0].strip(), parts[1].strip(), parts[2].strip()
                            # Xóa ký tự % và khoảng trắng
                            pct_num = re.sub(r'[^0-9.]', '', pct_raw)
                            pct_int = int(float(pct_num)) if pct_num else 0
                            if on_progress:
                                on_progress(pct_int, speed_raw or "--", eta_raw or "--:--")
                    except Exception:
                        pass
                elif on_log and line_str:
                    # Ghi log các dòng thông báo của yt-dlp
                    if not line_str.startswith("[download]"):
                        on_log(line_str)
        finally:
            self.process.wait()
            stderr_thread.join(timeout=2.0)

        if self.is_cancelled:
            return False, "Tác vụ tải đã bị hủy bởi người dùng."

        if self.process.returncode != 0:
            stderr_out = "\n".join(stderr_lines).strip()
            logger.error(f"yt-dlp lỗi ({self.process.returncode}): {stderr_out}")
            if on_log:
                on_log(f"[ERROR] yt-dlp: {stderr_out[-300:]}")
            return False, stderr_out[-200:] if stderr_out else "Lỗi tải video."

        if on_progress:
            on_progress(100, "Hoàn tất", "00:00")
        if on_log:
            on_log("[SUCCESS] Tải video thành công!")
        return True, "Thành công"

    @staticmethod
    def check_latest_version() -> Tuple[bool, str, str]:
        """Kiểm tra phiên bản mới nhất trên GitHub API: (success, tag_name, download_url)."""
        api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        req = urllib.request.Request(api_url, headers={"User-Agent": "MediaStudio-Updater"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    return False, "", ""
                data = json.loads(response.read().decode("utf-8"))
                tag_name = data.get("tag_name", "")
                assets = data.get("assets", [])
                target_name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
                for asset in assets:
                    if asset.get("name") == target_name:
                        return True, tag_name, asset.get("browser_download_url", "")
                return True, tag_name, ""
        except Exception:
            return False, "", ""

    @staticmethod
    def update_ytdlp_binary(log_callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Tải file yt-dlp.exe mới nhất từ GitHub release về %APPDATA%\\MediaStudio\\bin\\yt-dlp.exe.
        Hệ thống tự động ưu tiên file này thay vì bản đóng gói sẵn.
        """
        logger = get_logger()
        msg = "Đang kiểm tra phiên bản yt-dlp mới nhất từ GitHub..."
        logger.info(msg)
        if log_callback:
            log_callback(msg)

        api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        req = urllib.request.Request(api_url, headers={"User-Agent": "MediaStudio-Updater"})

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status != 200:
                    return False, f"GitHub API trả về mã lỗi: {response.status}"
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "Unknown")
            assets = data.get("assets", [])
            download_url = None

            target_name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
            for asset in assets:
                if asset.get("name") == target_name:
                    download_url = asset.get("browser_download_url")
                    break

            if not download_url:
                return False, f"Không tìm thấy file nhị phân {target_name} trong bản phát hành {tag_name}"

            bin_dir = get_custom_bin_dir()
            dest_file = bin_dir / target_name
            temp_dest = bin_dir / f"{target_name}.tmp"

            msg = f"Đang tải phiên bản {tag_name} từ {download_url}..."
            logger.info(msg)
            if log_callback:
                log_callback(msg)

            # Tải file
            req_dl = urllib.request.Request(download_url, headers={"User-Agent": "MediaStudio-Updater"})
            with urllib.request.urlopen(req_dl, timeout=60) as resp, open(temp_dest, "wb") as out_f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)

            # Đổi tên file tạm
            if dest_file.exists():
                try:
                    dest_file.unlink()
                except Exception:
                    pass
            temp_dest.rename(dest_file)

            success_msg = f"Đã cập nhật thành công yt-dlp lên phiên bản {tag_name}!"
            logger.info(success_msg)
            if log_callback:
                log_callback(f"[SUCCESS] {success_msg}")
            return True, success_msg

        except Exception as e:
            err = f"Lỗi khi cập nhật yt-dlp: {e}"
            logger.error(err)
            if log_callback:
                log_callback(f"[ERROR] {err}")
            return False, err
