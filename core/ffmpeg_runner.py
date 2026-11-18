"""
FFmpeg Runner Core Module
Quản lý việc thực thi FFmpeg và FFprobe:
- Chạy với cờ CREATE_NO_WINDOW (không nháy console)
- Trích xuất thời lượng và metadata chính xác bằng ffprobe
- Báo cáo % tiến độ và ETA thời gian thực qua '-progress pipe:1'
- Dịch lỗi kỹ thuật thành thông báo tiếng Việt dễ hiểu
- Dọn dẹp file tạm/dở dang khi bị hủy hoặc gặp lỗi
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
from core.system import (
    get_binary_path, get_subprocess_kwargs,
    kill_process_tree, suspend_process_tree, resume_process_tree
)
from core.logger import get_logger


class FFmpegRunner:

    @staticmethod
    def probe(file_path: str) -> Dict[str, Any]:
        """Trích xuất thông số kỹ thuật của file media bằng ffprobe."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        ffprobe_bin = get_binary_path("ffprobe")
        cmd = [
            ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                **get_subprocess_kwargs()
            )
        except Exception as e:
            raise RuntimeError(f"Lỗi khi chạy ffprobe: {e}")

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe thất bại: {result.stderr.strip() or 'Không đọc được file'}")

        try:
            data = json.loads(result.stdout)
        except Exception as e:
            raise RuntimeError(f"Không phân tích được JSON từ ffprobe: {e}")

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
            "raw": data
        }

    @staticmethod
    def translate_error(stderr_text: str) -> str:
        """Chuyển đổi các thông báo lỗi FFmpeg phổ biến thành tiếng Việt dễ hiểu."""
        text = stderr_text.lower()
        if "unknown encoder" in text:
            return "Bộ mã hóa GPU không được hỗ trợ trên thiết bị này. Đang chuyển sang CPU."
        if "no space left on device" in text:
            return "Ổ đĩa đã hết dung lượng trống. Vui lòng dọn dẹp ổ đĩa."
        if "permission denied" in text:
            return "Không có quyền ghi vào thư mục đầu ra đã chọn."
        if "invalid data found when processing input" in text:
            return "File video đầu vào bị lỗi hoặc cấu trúc file không hợp lệ."
        if "does not contain any stream" in text:
            return "File không chứa luồng hình ảnh hoặc âm thanh hợp lệ."
        if "vp9_superframe" in text or "invalid frame marker" in text:
            return "Lỗi khung hình VP9, cần sử dụng chế độ mã hóa lại."
        if "already exists" in text:
            return "File đầu ra đã tồn tại và không được phép ghi đè."
        return stderr_text[-300:] if stderr_text else "Lỗi xử lý FFmpeg không xác định."

    def __init__(self, cmd_args: List[str], total_duration: float = 0.0, output_path: Optional[str] = None):
        self.cmd_args = cmd_args
        self.total_duration = total_duration
        self.output_path = output_path
        self.process: Optional[subprocess.Popen] = None
        self.is_cancelled = False
        self.start_time = 0.0

    def cancel(self):
        """Hủy tác vụ và dọn dẹp sạch cây tiến trình và file đầu ra dở dang."""
        self.is_cancelled = True
        logger = get_logger()
        logger.info("Đang hủy toàn bộ cây tiến trình FFmpeg...")

        if self.process and self.process.poll() is None:
            kill_process_tree(self.process.pid)

        # Xóa file đầu ra dở dang nếu có
        if self.output_path and os.path.exists(self.output_path):
            try:
                time.sleep(0.3)
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                    logger.info(f"Đã dọn dẹp file đầu ra dở dang: {self.output_path}")
            except Exception as e:
                logger.warning(f"Không thể xóa file dở dang {self.output_path}: {e}")

    def pause(self):
        """Tạm dừng cả cây tiến trình FFmpeg."""
        if self.process and self.process.poll() is None:
            suspend_process_tree(self.process.pid)

    def resume(self):
        """Tiếp tục cây tiến trình FFmpeg."""
        if self.process and self.process.poll() is None:
            resume_process_tree(self.process.pid)

    def run(
        self,
        on_progress: Optional[Callable[[int, str, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Thực thi FFmpeg có báo cáo tiến độ.
        Trả về (success: bool, message: str)
        """
        logger = get_logger()
        ffmpeg_bin = get_binary_path("ffmpeg")
        full_cmd = [ffmpeg_bin, "-y", "-nostats", "-progress", "pipe:1"] + self.cmd_args

        if on_log:
            on_log(f"Bắt đầu lệnh FFmpeg: {' '.join(full_cmd[:8])}...")

        try:
            self.start_time = time.time()
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
            err = f"Không thể khởi động FFmpeg: {e}"
            logger.error(err)
            if on_log:
                on_log(f"[ERROR] {err}")
            return False, err

        out_time_sec = 0.0
        speed_str = "1.0x"
        stderr_lines: List[str] = []

        # Luồng phụ đọc và xả bộ đệm stderr để chống tràn buffer (OS pipe deadlock)
        def _drain_stderr():
            try:
                for s_line in iter(self.process.stderr.readline, ""):
                    if not s_line:
                        break
                    clean_s = s_line.strip()
                    if clean_s:
                        stderr_lines.append(clean_s)
                        if len(stderr_lines) > 300:
                            stderr_lines.pop(0)
            except Exception:
                pass

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        try:
            while self.process.poll() is None:
                if self.is_cancelled:
                    break

                line = self.process.stdout.readline()
                if not line:
                    continue

                line = line.strip()
                if "=" in line:
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()

                    if key in ["out_time_us", "out_time_ms"]:
                        divisor = 1_000_000.0 if key == "out_time_us" else 1_000.0
                        try:
                            out_time_sec = int(val) / divisor
                        except ValueError:
                            pass
                    elif key == "speed":
                        speed_str = val
                    elif key == "progress" and val == "continue":
                        if self.total_duration > 0 and out_time_sec > 0:
                            percent = min(99, int((out_time_sec / self.total_duration) * 100))
                            elapsed = max(0.001, time.time() - self.start_time)
                            
                            # Tính ETA chính xác từ tốc độ xử lý thực tế
                            current_speed = (out_time_sec / elapsed) if out_time_sec > 0 else 0.0
                            if current_speed > 0:
                                remaining_sec = max(0.0, self.total_duration - out_time_sec)
                                eta_sec = int(remaining_sec / current_speed)
                                eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}"
                            else:
                                eta_str = "--:--"

                            if on_progress:
                                on_progress(percent, speed_str, eta_str)
        finally:
            self.process.wait()
            stderr_thread.join(timeout=2.0)

        if self.is_cancelled:
            return False, "Tác vụ đã bị người dùng hủy."

        if self.process.returncode != 0:
            stderr_out = "\n".join(stderr_lines).strip()
            user_msg = self.translate_error(stderr_out)
            logger.error(f"FFmpeg thất bại ({self.process.returncode}): {stderr_out}")
            if on_log:
                on_log(f"[ERROR] {user_msg}")
            # Dọn file lỗi
            if self.output_path and os.path.exists(self.output_path):
                try:
                    os.remove(self.output_path)
                except Exception:
                    pass
            return False, user_msg

        if on_progress:
            on_progress(100, speed_str, "00:00")
        if on_log:
            on_log("[SUCCESS] FFmpeg xử lý thành công!")
        return True, "Thành công"

