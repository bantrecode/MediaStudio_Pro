"""
yt-dlp Engine Core Module
Quản lý các thuật toán và logic tải video từ YouTube, TikTok, Facebook, Douyin:
- Chuẩn hóa tên tiếng Việt không dấu (clean_filename)
- Cấu hình bypass JS runtime (Deno/Node) chống chặn bot
- Trích xuất thông tin video (tiêu đề, thời lượng, kênh, danh sách định dạng độ phân giải)
- Xây dựng danh sách tham số dòng lệnh CLI cho yt-dlp.exe
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
import re
import sys
from typing import Dict, Any, List, Tuple, Optional
import yt_dlp
from core.system import get_binary_path, clean_unicode_filename
from core.logger import get_logger


def clean_filename(filename: str) -> str:
    """Tương thích ngược với hàm clean_filename từ Download_video_tu_Youtube/Desktop."""
    return clean_unicode_filename(filename)


class YtDlpEngine:

    @staticmethod
    def get_ydl_opts_with_bypass(proxy: str = "") -> Dict[str, Any]:
        """
        Cấu hình yt-dlp tối ưu kế thừa từ bản Desktop chạy mượt:
        - Để yt-dlp tự chọn player client mặc định (không ép web_embedded)
        - Hỗ trợ Deno / Node runtime cho JS challenge giải mã link YouTube
        - Socket timeout 30s, retries 3 lần
        """
        ffmpeg_bin = get_binary_path("ffmpeg")
        opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            'ffmpeg_location': ffmpeg_bin,
            'js_runtimes': {'deno': {}, 'node': {}},
        }
        if proxy and proxy.strip():
            opts['proxy'] = proxy.strip()
        return opts

    @staticmethod
    def extract_info(url: str, is_playlist: bool = False, proxy: str = "") -> Dict[str, Any]:
        """
        Trích xuất nhanh metadata của video / playlist mà không tải file.
        """
        opts = YtDlpEngine.get_ydl_opts_with_bypass(proxy=proxy)
        opts['noplaylist'] = not is_playlist
        opts['extract_flat'] = 'in_playlist' if is_playlist else False

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Không thể lấy dữ liệu từ đường link này.")

            # Nếu là Playlist
            if 'entries' in info:
                entries = list(info['entries'])
                return {
                    'is_playlist': True,
                    'title': info.get('title', 'Danh sách phát'),
                    'count': len(entries),
                    'entries': [
                        {
                            'title': e.get('title', 'Unknown'),
                            'url': e.get('url') or f"https://www.youtube.com/watch?v={e.get('id')}",
                            'duration': e.get('duration', 0)
                        } for e in entries if e
                    ]
                }

            # Video đơn
            duration = info.get('duration', 0)
            mins = int(duration // 60)
            secs = int(duration % 60)
            duration_str = f"{mins:02d}:{secs:02d}" if duration else "Trực tiếp / Không rõ"

            # Phân tích các format có sẵn
            video_formats = []
            audio_formats = []
            if 'formats' in info:
                for f in info['formats']:
                    format_id = f.get('format_id', 'N/A')
                    ext = f.get('ext', 'N/A')
                    resolution = f.get('resolution') or f"{f.get('width', '')}x{f.get('height', '')}" or 'N/A'
                    filesize = f.get('filesize') or f.get('filesize_approx') or 0
                    filesize_str = f"{filesize / 1024 / 1024:.1f} MB" if filesize else "N/A"
                    has_video = f.get('vcodec') != 'none'
                    has_audio = f.get('acodec') != 'none'

                    format_str = f"{format_id} - {resolution} ({ext}) - {filesize_str}"
                    if has_video and not has_audio:
                        video_formats.append((format_id, format_str))
                    elif has_audio and not has_video:
                        audio_formats.append((format_id, format_str))
                    elif has_video and has_audio:
                        video_formats.append((format_id, f"{format_str} [Có cả Audio+Video]"))

            return {
                'is_playlist': False,
                'id': info.get('id', ''),
                'title': info.get('title', 'Không có tiêu đề'),
                'uploader': info.get('uploader') or info.get('channel') or "Không rõ",
                'duration': duration,
                'duration_str': duration_str,
                'thumbnail': info.get('thumbnail', ''),
                'webpage_url': info.get('webpage_url', url),
                'video_formats': video_formats,
                'audio_formats': audio_formats
            }

    @staticmethod
    def build_cli_arguments(
        url: str,
        output_dir: str,
        quality: str = "1080p",
        audio_only: bool = False,
        audio_format: str = "mp3",
        download_subs: bool = False,
        is_playlist: bool = False,
        limit_rate: str = "",
        proxy: str = ""
    ) -> List[str]:
        """
        Xây dựng danh sách cờ dòng lệnh cho yt-dlp.exe chạy độc lập.
        """
        args = [
            "--no-warnings",
            "--socket-timeout", "30",
            "--retries", "3",
            "--fragment-retries", "3",
        ]

        if not is_playlist:
            args.append("--no-playlist")
        else:
            args.append("--yes-playlist")

        if proxy and proxy.strip():
            args.extend(["--proxy", proxy.strip()])

        if limit_rate and limit_rate.strip():
            args.extend(["--limit-rate", limit_rate.strip()])

        # Mẫu tên file đầu ra an toàn
        output_tmpl = os.path.join(output_dir, "%(title)s.%(ext)s")
        args.extend(["-o", output_tmpl])

        # Định dạng chất lượng
        if audio_only:
            args.extend([
                "-x",  # Trích xuất âm thanh
                "--audio-format", audio_format,
                "--audio-quality", "192K",
            ])
        else:
            if quality == "best":
                fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"
            elif quality == "4K":
                fmt = "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]"
            elif quality == "1080p":
                fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            elif quality == "720p":
                fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"
            elif quality == "480p":
                fmt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"
            else:
                fmt = "bestvideo+bestaudio/best"

            args.extend(["-f", fmt, "--merge-output-format", "mp4"])

        # Phụ đề
        if download_subs:
            args.extend([
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", "vi,en",
                "--convert-subs", "srt"
            ])

        args.append(url)
        return args
