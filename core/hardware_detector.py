"""
Hardware Detector Module
Phát hiện card đồ họa và các bộ giải mã/mã hóa phần cứng (GPU Acceleration)
hỗ trợ bởi FFmpeg: NVIDIA NVENC, Intel QSV, AMD AMF.
"""

import subprocess
from typing import Dict, List, Optional
from core.path_manager import PathManager


class HardwareDetector:
    _cached_encoders = None
    _hardware_info = None

    @classmethod
    def get_supported_encoders(cls) -> List[str]:
        """
        Chạy `ffmpeg -encoders` để lấy danh sách chính xác các video encoder được hỗ trợ.
        """
        if cls._cached_encoders is not None:
            return cls._cached_encoders

        ffmpeg_bin = PathManager.get_ffmpeg_path()
        encoders = []

        try:
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                [ffmpeg_bin, "-encoders"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                startupinfo=startupinfo,
                timeout=5
            )

            for line in result.stdout.splitlines():
                line = line.strip()
                # Định dạng dòng FFmpeg: V..... <encoder_name> <description>
                if line.startswith("V") or line.startswith("v"):
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 2:
                        encoders.append(parts[1])

        except Exception:
            # Nếu FFmpeg chưa có hoặc lỗi, fallback về các codec phần mềm cơ bản
            encoders = ["libx264", "libx265", "aac", "mp3"]

        cls._cached_encoders = encoders
        return cls._cached_encoders

    @classmethod
    def detect_hardware(cls) -> Dict[str, any]:
        """
        Phân tích khả năng tăng tốc phần cứng của máy tính.
        Trả về dictionary chi tiết:
        {
            "has_nvidia": bool,
            "has_intel": bool,
            "has_amd": bool,
            "best_h264_encoder": str,
            "best_hevc_encoder": str,
            "acceleration_name": str
        }
        """
        if cls._hardware_info is not None:
            return cls._hardware_info

        encoders = cls.get_supported_encoders()

        has_nvidia = "h264_nvenc" in encoders or "hevc_nvenc" in encoders
        has_intel = "h264_qsv" in encoders or "hevc_qsv" in encoders
        has_amd = "h264_amf" in encoders or "hevc_amf" in encoders

        # Xác định encoder H.264 tối ưu
        if has_nvidia and "h264_nvenc" in encoders:
            best_h264 = "h264_nvenc"
            accel_name = "NVIDIA NVENC (Tăng tốc phần cứng)"
        elif has_intel and "h264_qsv" in encoders:
            best_h264 = "h264_qsv"
            accel_name = "Intel QuickSync (QSV)"
        elif has_amd and "h264_amf" in encoders:
            best_h264 = "h264_amf"
            accel_name = "AMD AMF (Tăng tốc phần cứng)"
        else:
            best_h264 = "libx264"
            accel_name = "CPU Software (libx264 - Chuẩn độ tương thích cao)"

        # Xác định encoder HEVC / H.265 tối ưu
        if has_nvidia and "hevc_nvenc" in encoders:
            best_hevc = "hevc_nvenc"
        elif has_intel and "hevc_qsv" in encoders:
            best_hevc = "hevc_qsv"
        elif has_amd and "hevc_amf" in encoders:
            best_hevc = "hevc_amf"
        else:
            best_hevc = "libx265"

        cls._hardware_info = {
            "has_nvidia": has_nvidia,
            "has_intel": has_intel,
            "has_amd": has_amd,
            "best_h264_encoder": best_h264,
            "best_hevc_encoder": best_hevc,
            "acceleration_name": accel_name,
            "all_encoders": encoders
        }
        return cls._hardware_info

    @classmethod
    def get_encoder_for_codec(cls, codec: str = "h264", mode: str = "auto") -> str:
        """
        Lấy tên encoder cụ thể dựa trên codec và chế độ người dùng chọn:
        - codec: 'h264' hoặc 'hevc'/'h265'
        - mode: 'auto', 'nvidia', 'intel', 'amd', 'cpu'
        """
        info = cls.detect_hardware()
        encoders = info["all_encoders"]

        codec_lower = codec.lower()
        is_hevc = codec_lower in ["hevc", "h265", "x265"]

        if mode == "auto":
            return info["best_hevc_encoder"] if is_hevc else info["best_h264_encoder"]
        elif mode == "nvidia":
            target = "hevc_nvenc" if is_hevc else "h264_nvenc"
            return target if target in encoders else ("libx265" if is_hevc else "libx264")
        elif mode == "intel":
            target = "hevc_qsv" if is_hevc else "h264_qsv"
            return target if target in encoders else ("libx265" if is_hevc else "libx264")
        elif mode == "amd":
            target = "hevc_amf" if is_hevc else "h264_amf"
            return target if target in encoders else ("libx265" if is_hevc else "libx264")
        else:  # cpu
            return "libx265" if is_hevc else "libx264"

