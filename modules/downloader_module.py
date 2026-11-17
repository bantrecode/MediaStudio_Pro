"""
Downloader Module (Module 1) - Phase 2 Implementation
Trình tải video đa năng yt-dlp qua subprocess CLI độc lập:
- Kế thừa BaseModule để cắm vào Shell UI và Job Queue
- Chạy yt-dlp.exe với cờ CREATE_NO_WINDOW và tiến trình độc lập
- Báo cáo % tiến độ, tốc độ (MB/s, KB/s) và ETA thời gian thực
- Tự động lưu link đã tải vào SQLite để chống tải trùng lặp
- Tiêu diệt sạch cây tiến trình khi người dùng hủy bằng kill_process_tree()
"""

import os
from typing import Dict, Any, Tuple, Optional
from PySide6.QtWidgets import QWidget
from modules.base_module import BaseModule
from core.ytdlp_engine import YtDlpEngine
from core.ytdlp_runner import YtDlpRunner
from core.database import HistoryDB
from core.job_queue.job_model import Job
from ui.views.downloader_view import DownloaderView


class DownloaderModule(BaseModule):
    @property
    def module_id(self) -> str:
        return "downloader"

    @property
    def display_name(self) -> str:
        return "Trình Tải Video"

    @property
    def icon(self) -> str:
        return "📥"

    @property
    def description(self) -> str:
        return "Tải video 4K/1080p, tách nhạc MP3, tải batch, playlist, phụ đề từ YouTube/TikTok/Facebook."

    def create_widget(self, parent: Optional[QWidget], bridge: Any) -> QWidget:
        return DownloaderView(bridge, parent)

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        url = params.get("url")
        if not url or not url.strip():
            return False, "Thiếu đường dẫn URL video."

        output_dir = params.get("output_dir")
        if not output_dir or not os.path.exists(output_dir):
            return False, f"Thư mục lưu không tồn tại: {output_dir}"

        return True, ""

    def execute_job(
        self,
        job: Job,
        progress_callback: Any,
        log_callback: Any,
        cancel_event: Any,
        pause_event: Any
    ) -> Tuple[bool, str, str]:
        """
        Thực thi tải video bằng YtDlpRunner (CLI subprocess mode).
        Hàm này chạy hoàn toàn trên worker thread của Job Queue.
        """
        p = job.params
        url = p.get("url", "").strip()
        output_dir = p.get("output_dir", "")
        quality = p.get("quality", "1080p")
        audio_only = p.get("audio_only", False)
        audio_format = p.get("audio_format", "mp3")
        download_subs = p.get("download_subs", False)
        is_playlist = p.get("is_playlist", False)
        limit_rate = p.get("limit_rate", "")
        proxy = p.get("proxy", "")
        title = p.get("title", "Video")

        log_callback(f"Bắt đầu tải link: {url}")

        # Xây dựng tham số CLI cho yt-dlp.exe
        cli_args = YtDlpEngine.build_cli_arguments(
            url=url,
            output_dir=output_dir,
            quality=quality,
            audio_only=audio_only,
            audio_format=audio_format,
            download_subs=download_subs,
            is_playlist=is_playlist,
            limit_rate=limit_rate,
            proxy=proxy
        )

        runner = YtDlpRunner(cmd_args=cli_args, output_dir=output_dir)
        job._runner_handle = runner

        success, message = runner.run(
            on_progress=progress_callback,
            on_log=log_callback
        )

        if success:
            log_callback(f"[SUCCESS] Tải hoàn tất và lưu vào thư mục: {output_dir}")
            # Ghi nhận vào SQLite để chống tải trùng lặp
            try:
                HistoryDB.get_instance().record_downloaded_url(url=url, title=title)
            except Exception:
                pass
            return True, output_dir, ""
        else:
            return False, "", message
