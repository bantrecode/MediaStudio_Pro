"""
GPU Detector Core Module
Phát hiện và kiểm thử thực tế khả năng tăng tốc phần cứng (NVIDIA NVENC, Intel QSV, AMD AMF).
Chạy test encode ngắn để xác thực driver, tự động fallback về CPU (libx264/libx265) nếu lỗi.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import subprocess
from typing import Dict, List, Any
from core.system import get_binary_path, get_subprocess_kwargs
from core.logger import get_logger


class GPUDetector:
    _cached_info: Dict[str, Any] = None

    @classmethod
    def get_supported_encoders(cls) -> List[str]:
        """Lấy danh sách encoders từ ffmpeg -encoders với cờ CREATE_NO_WINDOW."""
        ffmpeg_bin = get_binary_path("ffmpeg")
        encoders: List[str] = []

        try:
            cmd = [ffmpeg_bin, "-encoders"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                **get_subprocess_kwargs()
            )

            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("V") or line.startswith("v"):
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 2:
                        encoders.append(parts[1])
        except Exception as e:
            get_logger().warning(f"Không thể đọc danh sách encoders: {e}")
            encoders = ["libx264", "libx265"]

        return encoders

    @classmethod
    def test_encoder(cls, encoder_name: str) -> bool:
        """
        Kiểm thử thực tế một encoder bằng cách encode 0.1 giây video mẫu.
        Kích thước 256x256 để đảm bảo vượt qua giới hạn kích thước tối thiểu của NVENC/QSV/AMF (>= 144x144).
        """
        ffmpeg_bin = get_binary_path("ffmpeg")
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1",
            "-c:v", encoder_name,
            "-f", "null", "-"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=4,
                **get_subprocess_kwargs()
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def detect_gpu(cls, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Dò tìm GPU tối ưu kèm kiểm thử thực tế.
        Trả về kết quả có cache.
        """
        if cls._cached_info is not None and not force_refresh:
            return cls._cached_info

        logger = get_logger()
        encoders = cls.get_supported_encoders()

        has_nvenc = ("h264_nvenc" in encoders) and cls.test_encoder("h264_nvenc")
        has_qsv = ("h264_qsv" in encoders) and cls.test_encoder("h264_qsv")
        has_amf = ("h264_amf" in encoders) and cls.test_encoder("h264_amf")

        if has_nvenc:
            best_h264 = "h264_nvenc"
            best_hevc = "hevc_nvenc" if "hevc_nvenc" in encoders and cls.test_encoder("hevc_nvenc") else "libx265"
            accel_name = "NVIDIA NVENC (Tăng tốc phần cứng)"
            accel_type = "nvidia"
        elif has_qsv:
            best_h264 = "h264_qsv"
            best_hevc = "hevc_qsv" if "hevc_qsv" in encoders and cls.test_encoder("hevc_qsv") else "libx265"
            accel_name = "Intel QuickSync (QSV)"
            accel_type = "intel"
        elif has_amf:
            best_h264 = "h264_amf"
            best_hevc = "hevc_amf" if "hevc_amf" in encoders and cls.test_encoder("hevc_amf") else "libx265"
            accel_name = "AMD AMF (Tăng tốc phần cứng)"
            accel_type = "amd"
        else:
            best_h264 = "libx264"
            best_hevc = "libx265"
            accel_name = "CPU Software (libx264 - Tương thích chuẩn)"
            accel_type = "cpu"

        logger.info(f"Kết quả nhận diện GPU: {accel_name}")

        cls._cached_info = {
            "has_nvenc": has_nvenc,
            "has_qsv": has_qsv,
            "has_amf": has_amf,
            "accel_type": accel_type,
            "acceleration_name": accel_name,
            "best_h264": best_h264,
            "best_hevc": best_hevc,
            "all_encoders": encoders
        }
        return cls._cached_info

    @classmethod
    def get_best_encoder(cls, codec: str = "h264") -> Dict[str, Any]:
        """
        Trả về thông tin bộ mã hóa tốt nhất (ưu tiên GPU rời NVENC/QSV/AMF, tự động fallback CPU).
        """
        info = cls.detect_gpu()
        is_hevc = codec.lower() in ["hevc", "h265", "x265"]

        if info["has_nvenc"]:
            encoder = "hevc_nvenc" if is_hevc else "h264_nvenc"
            name = "NVIDIA GeForce (NVENC)"
            return {"available": True, "encoder": encoder, "name": name, "codec": codec, "type": "nvidia"}
        elif info["has_qsv"]:
            encoder = "hevc_qsv" if is_hevc else "h264_qsv"
            name = "Intel QuickSync (QSV)"
            return {"available": True, "encoder": encoder, "name": name, "codec": codec, "type": "intel"}
        elif info["has_amf"]:
            encoder = "hevc_amf" if is_hevc else "h264_amf"
            name = "AMD Radeon (AMF)"
            return {"available": True, "encoder": encoder, "name": name, "codec": codec, "type": "amd"}
        else:
            encoder = "libx265" if is_hevc else "libx264"
            return {"available": False, "encoder": encoder, "name": "CPU Software (libx264)", "codec": codec, "type": "cpu"}

    @classmethod
    def get_hardware_profile(cls) -> Dict[str, Any]:
        """
        Đánh giá năng lực phần cứng của máy tính và đưa ra chiến lược tối ưu thích ứng:
        - Tier 'high': Có GPU rời (RTX 3060, NVENC/QSV/AMF). Tốc độ 300 - 600+ fps.
        - Tier 'medium': CPU tiêu chuẩn (>= 6 cores, RAM >= 8GB). libx264 preset veryfast.
        - Tier 'low': Máy yếu (CPU <= 4 cores hoặc RAM < 8GB). libx264 preset ultrafast, giới hạn số luồng để không đơ máy.
        """
        import os
        import psutil

        info = cls.detect_gpu()
        cpu_cores = os.cpu_count() or 2
        try:
            ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        except Exception:
            ram_gb = 8.0

        has_gpu = info["has_nvenc"] or info["has_qsv"] or info["has_amf"]

        if has_gpu:
            tier = "high"
            best = cls.get_best_encoder("h264")
            rec_encoder = best["encoder"]
            rec_preset = "p4" if info["has_nvenc"] else ("medium" if info["has_qsv"] else "balanced")
            threads = 0
            advice = f"⚡ Máy tính mạnh (GPU: {best['name']}). Ưu tiên xử lý bằng phần cứng với tốc độ 300 - 600+ FPS!"
        elif cpu_cores >= 6 and ram_gb >= 8.0:
            tier = "medium"
            rec_encoder = "libx264"
            rec_preset = "veryfast"
            threads = 0
            advice = f"💻 Máy tính tiêu chuẩn (CPU {cpu_cores} nhân, RAM {ram_gb}GB). Sử dụng CPU đa luồng với preset 'veryfast' tối ưu tốc độ."
        else:
            tier = "low"
            rec_encoder = "libx264"
            rec_preset = "ultrafast"
            threads = max(1, cpu_cores - 1)
            advice = f"⚠️ Máy tính cấu hình cơ bản (CPU {cpu_cores} nhân, RAM {ram_gb}GB). Kích hoạt chế độ Tiết kiệm tài nguyên (UltraFast, {threads} threads) để tránh treo máy."

        return {
            "tier": tier,
            "cpu_cores": cpu_cores,
            "ram_gb": ram_gb,
            "has_gpu": has_gpu,
            "gpu_name": info["acceleration_name"],
            "recommended_encoder": rec_encoder,
            "recommended_preset": rec_preset,
            "recommended_threads": threads,
            "advice": advice
        }

    @classmethod
    def get_encoder(cls, codec: str = "h264", preference: str = "auto") -> str:
        """
        Lấy encoder theo mong muốn của người dùng (preference: 'auto', 'nvidia', 'intel', 'amd', 'cpu').
        Tự động fallback về CPU an toàn nếu GPU yêu cầu không khả dụng.
        """
        info = cls.detect_gpu()
        is_hevc = codec.lower() in ["hevc", "h265", "x265"]

        if preference == "auto":
            return info["best_hevc"] if is_hevc else info["best_h264"]
        elif preference == "nvidia" and info["has_nvenc"]:
            return "hevc_nvenc" if is_hevc else "h264_nvenc"
        elif preference == "intel" and info["has_qsv"]:
            return "hevc_qsv" if is_hevc else "h264_qsv"
        elif preference == "amd" and info["has_amf"]:
            return "hevc_amf" if is_hevc else "h264_amf"
        else:
            return "libx265" if is_hevc else "libx264"

