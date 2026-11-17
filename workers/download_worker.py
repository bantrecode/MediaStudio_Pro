"""
Download Worker Module
Luồng nền (QThread) thực thi việc tải video / audio sử dụng yt-dlp.
Không làm đơ (freeze) giao diện, hỗ trợ hủy tác vụ, tải hàng loạt và báo cáo tiến độ chi tiết.
"""

import os
import re
from typing import List, Optional
from PySide6.QtCore import QThread, Signal
import yt_dlp
from core.ytdlp_engine import YtDlpEngine, clean_filename


class DownloadWorker(QThread):
    # Signals báo cáo về giao diện UI
    progress_changed = Signal(int, str, str)   # (percent, speed, eta)
    status_message = Signal(str, str)          # (message, level: 'INFO', 'SUCCESS', 'WARNING', 'ERROR')
    item_finished = Signal(str)                # (file_name)
    all_finished = Signal(bool, str)           # (success, message)

    def __init__(
        self,
        urls: List[str],
        output_dir: str,
        quality: str = "1080p",
        audio_only: bool = False,
        audio_format: str = "mp3",
        download_subs: bool = False,
        is_playlist: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.urls = urls
        self.output_dir = output_dir
        self.quality = quality
        self.audio_only = audio_only
        self.audio_format = audio_format
        self.download_subs = download_subs
        self.is_playlist = is_playlist
        self.is_cancelled = False

    def cancel(self):
        """Hủy tác vụ tải xuống."""
        self.is_cancelled = True
        self.status_message.emit("Đang dừng tác vụ tải...", "WARNING")

    def _progress_hook(self, d: dict):
        if self.is_cancelled:
            raise yt_dlp.utils.DownloadCancelled("Tác vụ đã bị người dùng hủy.")

        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)

            percent = 0
            if total > 0:
                percent = int((downloaded / total) * 100)

            # Tốc độ tải
            speed = d.get('speed') or 0
            if speed > 1024 * 1024:
                speed_str = f"{speed / 1024 / 1024:.1f} MB/s"
            elif speed > 1024:
                speed_str = f"{speed / 1024:.1f} KB/s"
            else:
                speed_str = f"{speed:.0f} B/s"

            # Thời gian ước tính (ETA)
            eta = d.get('eta')
            if eta is not None:
                eta_str = f"{int(eta // 60):02d}:{int(eta % 60):02d}"
            else:
                eta_str = "--:--"

            self.progress_changed.emit(percent, speed_str, eta_str)

        elif status == 'finished':
            self.progress_changed.emit(100, "Hoàn tất tải", "Đang xử lý")
            self.status_message.emit("Đang ghép nối âm thanh/hình ảnh bằng FFmpeg...", "INFO")

    def run(self):
        """Hàm thực thi chính trên luồng nền."""
        os.makedirs(self.output_dir, exist_ok=True)
        total_urls = len(self.urls)
        success_count = 0

        self.status_message.emit(f"Bắt đầu xử lý {total_urls} đường link...", "INFO")

        opts = YtDlpEngine.build_download_opts(
            output_dir=self.output_dir,
            quality=self.quality,
            audio_only=self.audio_only,
            audio_format=self.audio_format,
            download_subs=self.download_subs,
            is_playlist=self.is_playlist,
            progress_hook=self._progress_hook
        )

        for idx, url in enumerate(self.urls, 1):
            if self.is_cancelled:
                break

            url = url.strip()
            if not url:
                continue

            self.status_message.emit(f"[{idx}/{total_urls}] Đang tải link: {url}", "INFO")

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'Video') if info else 'Video'
                    
                    # Chuẩn hóa tên file đã tải nếu cần
                    clean_title = clean_filename(title)
                    self.item_finished.emit(clean_title)
                    self.status_message.emit(f"Tải thành công: {clean_title}", "SUCCESS")
                    success_count += 1

            except yt_dlp.utils.DownloadCancelled:
                self.status_message.emit("Tác vụ đã bị người dùng hủy.", "WARNING")
                self.all_finished.emit(False, "Tác vụ đã bị hủy.")
                return

            except Exception as e:
                err_msg = str(e)
                # Cắt ngắn thông báo lỗi nếu quá dài
                if len(err_msg) > 200:
                    err_msg = err_msg[:200] + "..."
                self.status_message.emit(f"Lỗi khi tải link [{url}]: {err_msg}", "ERROR")

        if self.is_cancelled:
            self.all_finished.emit(False, "Tác vụ đã bị hủy.")
        else:
            summary = f"Hoàn tất tải {success_count}/{total_urls} mục vào: {self.output_dir}"
            self.status_message.emit(summary, "SUCCESS")
            self.all_finished.emit(True, summary)

