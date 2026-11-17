"""
Converter Engine Core Module
Quản lý logic chuyển đổi và nén media:
- Hỗ trợ định dạng: MOV, MP4, MKV, AVI, MP3, WAV
- Chế độ Remux siêu tốc (-c copy) khi chỉ đổi container
- Chế độ Smart Compress CRF (H.264/H.265) tối ưu chất lượng/dung lượng
- Presets một chạm: TikTok, YouTube, Zalo/Messenger (<25MB), Discord (<10MB)
- Tự động tính toán bitrate mục tiêu để ép dung lượng file dưới ngưỡng cho phép
- Ước tính dung lượng file đầu ra (Estimated Size) trước khi render
- Tăng tốc phần cứng GPU (NVIDIA NVENC, Intel QSV, AMD AMF)
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from core.ffmpeg_runner import FFmpegRunner
from core.gpu import GPUDetector
from core.system import clean_unicode_filename
from core.logger import get_logger


SUPPORTED_FORMATS = ["mp4", "mov", "mkv", "avi", "mp3", "wav"]
VIDEO_EXTENSIONS = {".mov", ".mp4", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".m4v"}


class ConverterEngine:

    @staticmethod
    def calculate_target_bitrate_for_max_size(duration: float, max_size_mb: float = 24.0, audio_bitrate_kbps: int = 128) -> int:
        """
        Tính toán video bitrate (kbps) để đảm bảo tổng dung lượng file đầu ra không vượt quá max_size_mb.
        Công thức: target_bitrate = (max_bytes * 8 / duration) - audio_bitrate
        """
        if duration <= 0:
            return 1000

        # Dự phòng 5% cho container overhead
        usable_bytes = (max_size_mb * 0.95) * 1024 * 1024
        total_bitrate_bps = (usable_bytes * 8) / duration
        total_bitrate_kbps = int(total_bitrate_bps / 1000)

        video_bitrate_kbps = total_bitrate_kbps - audio_bitrate_kbps
        # Giới hạn tối thiểu 150 kbps để không bị vỡ nát hình
        return max(150, video_bitrate_kbps)

    @staticmethod
    def estimate_output_size(duration: float, crf: int = 23, resolution: str = "original", is_remux: bool = False, original_size: int = 0) -> int:
        """
        Ước tính dung lượng file đầu ra (bytes) dựa trên CRF và thời lượng:
        - Remux: gần bằng dung lượng file gốc (chỉ đổi container).
        - Re-encode: ước tính dựa trên bitrate trung bình tương ứng với CRF và độ phân giải.
        """
        if is_remux:
            return original_size

        if duration <= 0:
            return 0

        # Bảng bitrate ước tính trung bình (kbps) theo độ phân giải ở mức CRF 23
        base_bitrates = {
            "4K": 12000,
            "1080p": 3500,
            "720p": 1800,
            "480p": 800,
            "original": 3000,
            "audio_only": 192
        }

        base = base_bitrates.get(resolution, 2500)

        # Điều chỉnh theo CRF (mỗi 6 điểm CRF làm dung lượng thay đổi xấp xỉ gấp đôi/giảm một nửa)
        # CRF 23 là mốc chuẩn (factor = 1.0)
        crf_factor = 2 ** ((23 - crf) / 6.0)
        estimated_video_kbps = max(200, int(base * crf_factor))
        estimated_audio_kbps = 128

        total_kbps = estimated_video_kbps + estimated_audio_kbps
        estimated_bytes = int((total_kbps * 1000 / 8) * duration)
        return estimated_bytes

    @staticmethod
    def build_conversion_args(
        input_path: str,
        output_path: str,
        target_format: str = "mp4",
        mode: str = "reencode",          # 'remux', 'reencode', 'preset'
        preset_name: str = "custom",      # 'custom', 'tiktok', 'youtube', 'zalo_25mb', 'discord_10mb'
        codec: str = "h264",              # 'h264' hoặc 'hevc'
        crf: int = 23,
        resolution: str = "original",     # 'original', '4k', '1080p', '720p', '480p'
        gpu_pref: str = "auto",
        duration: float = 0.0
    ) -> List[str]:
        """
        Xây dựng danh sách tham số FFmpeg tối ưu cho tác vụ chuyển đổi.
        """
        args = ["-i", input_path]
        target_fmt = target_format.lower()

        # 1. Chế độ Tách âm thanh (MP3 / WAV)
        if target_fmt in ["mp3", "wav"]:
            args.extend(["-vn"])  # Loại bỏ video stream
            if target_fmt == "mp3":
                args.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
            else:  # wav
                args.extend(["-c:a", "pcm_s16le"])
            args.append(output_path)
            return args

        # 2. Chế độ Remux siêu tốc (-c copy)
        if mode == "remux":
            args.extend(["-c", "copy", output_path])
            return args

        # 3. Chế độ Presets một chạm
        if mode == "preset":
            if preset_name == "zalo_25mb":
                # Ép dung lượng < 24MB để gửi qua Zalo/Messenger mượt mà
                v_bitrate = ConverterEngine.calculate_target_bitrate_for_max_size(duration, max_size_mb=23.5)
                encoder = GPUDetector.get_encoder("h264", preference=gpu_pref)
                args.extend([
                    "-c:v", encoder,
                    "-b:v", f"{v_bitrate}k",
                    "-maxrate", f"{int(v_bitrate * 1.3)}k",
                    "-bufsize", f"{int(v_bitrate * 2)}k",
                    "-vf", "scale='min(1280,iw)':-2",  # Giới hạn tối đa 720p cho file nhẹ
                    "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart",
                    output_path
                ])
                return args

            elif preset_name == "discord_10mb":
                # Ép dung lượng < 9.5MB cho Discord
                v_bitrate = ConverterEngine.calculate_target_bitrate_for_max_size(duration, max_size_mb=9.5, audio_bitrate_kbps=96)
                encoder = GPUDetector.get_encoder("h264", preference=gpu_pref)
                args.extend([
                    "-c:v", encoder,
                    "-b:v", f"{v_bitrate}k",
                    "-maxrate", f"{int(v_bitrate * 1.2)}k",
                    "-bufsize", f"{int(v_bitrate * 2)}k",
                    "-vf", "scale='min(854,iw)':-2",  # Tối đa 480p
                    "-c:a", "aac", "-b:a", "64k",
                    "-movflags", "+faststart",
                    output_path
                ])
                return args

            elif preset_name == "tiktok":
                # Chuẩn hóa khung hình dọc 1080x1920 hoặc chuẩn H.264 chất lượng cao
                encoder = GPUDetector.get_encoder("h264", preference=gpu_pref)
                args.extend([
                    "-c:v", encoder,
                    "-crf", "20",
                    "-preset", "slow" if "libx" in encoder else "p6",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    output_path
                ])
                return args

            elif preset_name == "youtube":
                # YouTube chuẩn 1080p H.264
                encoder = GPUDetector.get_encoder("h264", preference=gpu_pref)
                args.extend([
                    "-c:v", encoder,
                    "-crf", "18",
                    "-c:a", "aac", "-b:a", "256k",
                    "-movflags", "+faststart",
                    output_path
                ])
                return args

        # 4. Chế độ Re-encode tùy chỉnh (Custom)
        encoder = GPUDetector.get_encoder(codec, preference=gpu_pref)
        args.extend(["-c:v", encoder])

        # Cấu hình CRF / CQ
        if "nvenc" in encoder:
            args.extend(["-cq", str(crf), "-preset", "p4"])
        elif "qsv" in encoder:
            args.extend(["-global_quality", str(crf)])
        elif "amf" in encoder:
            args.extend(["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf)])
        else:  # libx264 / libx265 CPU
            args.extend(["-crf", str(crf), "-preset", "medium"])

        # Cấu hình Scale độ phân giải
        res_map = {
            "4k": "scale=3840:-2",
            "1080p": "scale=1920:-2",
            "720p": "scale=1280:-2",
            "480p": "scale=854:-2"
        }
        if resolution.lower() in res_map:
            args.extend(["-vf", res_map[resolution.lower()]])

        # Âm thanh
        args.extend(["-c:a", "aac", "-b:a", "192k"])

        # Web optimization (faststart)
        if target_fmt in ["mp4", "mov"]:
            args.extend(["-movflags", "+faststart"])

        args.append(output_path)
        return args

    @staticmethod
    def scan_directory_for_media(dir_path: str) -> List[str]:
        """Quét toàn bộ thư mục và tìm các file video/audio được hỗ trợ."""
        p = Path(dir_path)
        if not p.is_dir():
            return []

        files = []
        for item in p.rglob("*"):
            if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
                files.append(str(item.resolve()))
        return files

