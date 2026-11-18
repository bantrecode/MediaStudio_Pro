"""
FFmpeg Engine Module
Lớp wrapper thực thi FFmpeg và FFprobe:
- Đọc thông số media (duration, resolution, fps, bitrate, audio info) bằng ffprobe.
- Chạy lệnh FFmpeg bất đồng bộ với tính năng parse tiến độ chính xác qua `-progress pipe:1`.
- Báo cáo % hoàn thành, tốc độ xử lý, thời gian ước tính (ETA).
- Hỗ trợ hủy tiến trình an toàn không để lại tiến trình ma (zombie process).
"""

import os
import sys
import json
import re
import subprocess
import time
from typing import Dict, Any, Optional, Callable
from core.path_manager import PathManager


class FFmpegEngine:

    @staticmethod
    def probe_media(file_path: str) -> Dict[str, Any]:
        """
        Trích xuất toàn bộ thông số chi tiết của video/audio sử dụng ffprobe.
        Trả về dictionary đã được chuẩn hóa.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        ffprobe_bin = PathManager.get_ffprobe_path()
        cmd = [
            ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            startupinfo=startupinfo
        )

        if result.returncode != 0:
            raise RuntimeError(f"Lỗi khi đọc file bằng ffprobe: {result.stderr.strip()}")

        data = json.loads(result.stdout)
        format_info = data.get("format", {})
        streams = data.get("streams", [])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        duration = 0.0
        if "duration" in format_info:
            try:
                duration = float(format_info["duration"])
            except (ValueError, TypeError):
                pass
        elif video_stream and "duration" in video_stream:
            try:
                duration = float(video_stream["duration"])
            except (ValueError, TypeError):
                pass

        # Tính toán FPS
        fps = 0.0
        if video_stream and "r_frame_rate" in video_stream:
            r_fps = video_stream["r_frame_rate"]
            if "/" in r_fps:
                num, den = r_fps.split("/")
                if float(den) > 0:
                    fps = round(float(num) / float(den), 2)
            else:
                try:
                    fps = round(float(r_fps), 2)
                except ValueError:
                    pass

        return {
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "filesize": int(format_info.get("size", 0)),
            "duration": duration,
            "bitrate": int(format_info.get("bit_rate", 0)),
            "format_name": format_info.get("format_name", ""),
            "has_video": video_stream is not None,
            "has_audio": audio_stream is not None,
            "video_codec": video_stream.get("codec_name", "") if video_stream else "",
            "width": int(video_stream.get("width", 0)) if video_stream else 0,
            "height": int(video_stream.get("height", 0)) if video_stream else 0,
            "fps": fps,
            "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
            "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
            "raw_data": data
        }


class FFmpegRunner:
    """
    Quản lý việc chạy một tiến trình FFmpeg có theo dõi tiến độ và khả năng hủy bỏ.
    """

    def __init__(self, cmd_args: list, total_duration: float = 0.0):
        self.cmd_args = cmd_args
        self.total_duration = total_duration
        self.process: Optional[subprocess.Popen] = None
        self.is_cancelled = False
        self.start_time = 0.0

    def cancel(self):
        """Hủy tiến trình FFmpeg an toàn."""
        self.is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                # Trên Windows, gửi lệnh taskkill để dọn triệt để cây tiến trình con
                if sys.platform.startswith("win"):
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        capture_output=True
                    )
                else:
                    self.process.terminate()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def run(
        self,
        on_progress: Optional[Callable[[int, str, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Thực thi lệnh FFmpeg.
        - on_progress: Callback nhận (percent: int, speed: str, eta: str)
        - on_log: Callback nhận log text từng dòng
        Trả về True nếu thành công, False nếu lỗi hoặc bị hủy.
        """
        ffmpeg_bin = PathManager.get_ffmpeg_path()
        full_cmd = [ffmpeg_bin, "-y", "-nostats", "-progress", "pipe:1"] + self.cmd_args

        if on_log:
            on_log(f"[INFO] Bắt đầu thực thi FFmpeg: {' '.join(full_cmd[:6])}...")

        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self.start_time = time.time()
            self.process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                startupinfo=startupinfo,
                bufsize=1
            )
        except Exception as e:
            if on_log:
                on_log(f"[ERROR] Không thể khởi chạy FFmpeg: {str(e)}")
            return False

        out_time_ms = 0
        speed_str = "N/A"
        stderr_lines = []

        def _drain_stderr():
            try:
                for s_line in iter(self.process.stderr.readline, ""):
                    if not s_line:
                        break
                    s_clean = s_line.strip()
                    if s_clean:
                        stderr_lines.append(s_clean)
                        if len(stderr_lines) > 300:
                            stderr_lines.pop(0)
            except Exception:
                pass

        import threading
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        # Đọc luồng -progress pipe:1
        try:
            while self.process.poll() is None:
                if self.is_cancelled:
                    break

                line = self.process.stdout.readline()
                if not line:
                    continue

                line_str = line.strip()
                if "=" in line_str:
                    key, val = line_str.split("=", 1)
                    key = key.strip()
                    val = val.strip()

                    if key == "out_time_us":
                        try:
                            out_time_ms = int(val) / 1_000_000.0
                        except ValueError:
                            pass
                    elif key == "out_time_ms":
                        try:
                            out_time_ms = int(val) / 1_000.0
                        except ValueError:
                            pass
                    elif key == "speed":
                        speed_str = val
                    elif key == "progress" and val == "continue":
                        # Tính toán % và ETA
                        if self.total_duration > 0 and out_time_ms > 0:
                            percent = min(99, int((out_time_ms / self.total_duration) * 100))
                            elapsed = max(0.001, time.time() - self.start_time)
                            current_speed = (out_time_ms / elapsed) if out_time_ms > 0 else 0.0
                            if current_speed > 0:
                                remaining_sec = max(0.0, self.total_duration - out_time_ms)
                                eta_seconds = int(remaining_sec / current_speed)
                                eta_str = f"{eta_seconds // 60:02d}:{eta_seconds % 60:02d}"
                            else:
                                eta_str = "--:--"

                            if on_progress:
                                on_progress(percent, speed_str, eta_str)
        finally:
            self.process.wait()
            stderr_thread.join(timeout=2.0)

        if self.is_cancelled:
            if on_log:
                on_log("[WARNING] Tác vụ đã bị người dùng hủy.")
            return False

        if self.process.returncode != 0:
            stderr_out = "\n".join(stderr_lines).strip()
            if on_log:
                on_log(f"[ERROR] FFmpeg kết thúc với mã lỗi ({self.process.returncode}): {stderr_out[-500:]}")
            return False

        if on_progress:
            on_progress(100, speed_str, "00:00")
        if on_log:
            on_log("[SUCCESS] Tác vụ FFmpeg hoàn thành thành công!")
        return True

