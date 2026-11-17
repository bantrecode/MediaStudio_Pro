"""
Cutter Engine Core Module (Phase 4)
Quản lý logic cắt và phân đoạn video:
- Chế độ Cắt Nhanh Stream Copy (-c copy): Cắt tức thì không hao tổn chất lượng.
- Cảnh báo Keyframe cho Stream Copy khi cần độ chính xác khung hình.
- Chế độ Cắt Chính Xác Re-encode: Khớp từng khung hình (frame-accurate) kèm tăng tốc GPU.
- Tính năng Tự động Chia Nhỏ theo thời lượng (Auto-Split):
  * Chia cho TikTok / Shorts (60s, 90s, 180s) hoặc Facebook Reels.
  * Tự động sinh danh sách phân đoạn (Phần 1, Phần 2...).
- Chuyển đổi và chuẩn hóa mốc thời gian (hh:mm:ss.ms <-> giây).
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from core.gpu import GPUDetector
from core.system import clean_unicode_filename
from core.logger import get_logger


class CutterEngine:

    @staticmethod
    def format_seconds_to_time(seconds: float, include_ms: bool = False) -> str:
        """
        Chuyển số giây thành chuỗi thời gian định dạng 'HH:MM:SS' hoặc 'HH:MM:SS.mmm'.
        Ví dụ: 75.5 -> '00:01:15.500'
        """
        if seconds < 0:
            seconds = 0.0

        total_secs = int(seconds)
        millis = int((seconds - total_secs) * 1000)
        hours = total_secs // 3600
        minutes = (total_secs % 3600) // 60
        secs = total_secs % 60

        if include_ms:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def parse_time_to_seconds(time_str: str) -> float:
        """
        Chuyển chuỗi thời gian về số giây dạng float.
        Hỗ trợ:
        - 'HH:MM:SS' hoặc 'HH:MM:SS.mmm'
        - 'MM:SS' hoặc 'MM:SS.mmm'
        - 'SS' hoặc số nguyên/thực
        """
        s = str(time_str).strip()
        if not s:
            return 0.0

        try:
            # Nếu là số thực thuần túy
            return float(s)
        except ValueError:
            pass

        parts = s.split(":")
        try:
            if len(parts) == 3:
                h, m, sec = parts
                return int(h) * 3600 + int(m) * 60 + float(sec)
            elif len(parts) == 2:
                m, sec = parts
                return int(m) * 60 + float(sec)
            elif len(parts) == 1:
                return float(parts[0])
        except (ValueError, TypeError):
            return 0.0

        return 0.0

    @staticmethod
    def generate_split_segments(
        total_duration: float,
        segment_duration: float,
        overlap_seconds: float = 0.0,
        base_name: str = "Phần"
    ) -> List[Dict[str, Any]]:
        """
        Tự động tính toán các phân đoạn chia nhỏ video theo thời lượng định sẵn.
        Ví dụ: Video 150s chia mỗi đoạn 60s -> 3 đoạn (0-60, 60-120, 120-150).
        """
        if total_duration <= 0 or segment_duration <= 0:
            return []

        segments = []
        current_start = 0.0
        part_idx = 1

        while current_start < total_duration:
            current_end = min(total_duration, current_start + segment_duration)
            dur = current_end - current_start

            if dur >= 0.5:  # Bỏ qua đoạn rác quá ngắn (< 0.5s)
                segments.append({
                    "index": part_idx,
                    "name": f"{base_name} {part_idx}",
                    "start": round(current_start, 3),
                    "end": round(current_end, 3),
                    "duration": round(dur, 3)
                })
                part_idx += 1

            if current_end >= total_duration:
                break

            # Bước nhảy tiếp theo (trừ độ gối đầu overlap nếu có)
            step = segment_duration - max(0.0, overlap_seconds)
            if step <= 0:
                step = segment_duration
            current_start += step

        return segments

    @staticmethod
    def get_keyframe_warning() -> str:
        """Thông báo cảnh báo keyframe khi dùng stream copy."""
        return (
            "⚠️ Chế độ Cắt Nhanh (Stream Copy) chỉ cắt tại Keyframe (I-frame) gần nhất. "
            "Thời điểm bắt đầu thực tế có thể xê dịch từ 0.1s - 1s tùy video. "
            "Để chuẩn xác 100% từng khung hình, hãy chọn 'Cắt Chính Xác (Re-encode)'."
        )

    @staticmethod
    def build_cut_copy_args(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float
    ) -> List[str]:
        """
        Tạo đối số FFmpeg cho chế độ Cắt Nhanh (Stream Copy):
        -ss đặt trước -i để seek nhanh tới keyframe
        -t xác định thời lượng cắt
        -avoid_negative_ts make_zero để reset timestamp tránh đen hình
        """
        start = max(0.0, start_time)
        dur = max(0.1, end_time - start)

        return [
            "-ss", f"{start:.3f}",
            "-i", input_path,
            "-t", f"{dur:.3f}",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            output_path
        ]

    @staticmethod
    def build_cut_reencode_args(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        use_gpu: bool = True,
        crf: int = 23,
        preset: str = "medium"
    ) -> List[str]:
        """
        Tạo đối số FFmpeg cho chế độ Cắt Chính Xác (Re-encode):
        -ss và -to chuẩn xác từng khung hình
        Mã hóa lại H.264 qua GPU hoặc CPU (libx264)
        """
        start = max(0.0, start_time)
        dur = max(0.1, end_time - start)

        cmd = [
            "-ss", f"{start:.3f}",
            "-i", input_path,
            "-t", f"{dur:.3f}",
        ]

        # Lựa chọn bộ mã hóa
        selected_codec = "libx264"
        if use_gpu:
            best_gpu = GPUDetector.get_best_encoder()
            if best_gpu and best_gpu.get("available") and best_gpu.get("codec") == "h264":
                selected_codec = best_gpu["encoder"]

        if selected_codec == "h264_nvenc":
            cmd.extend(["-c:v", "h264_nvenc", "-cq", str(crf), "-preset", "p4"])
        elif selected_codec == "h264_qsv":
            cmd.extend(["-c:v", "h264_qsv", "-global_quality", str(crf), "-preset", "medium"])
        elif selected_codec == "h264_amf":
            cmd.extend(["-c:v", "h264_amf", "-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-quality", "balanced"])
        else:
            cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", preset])

        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ])

        return cmd

