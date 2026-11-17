"""
Unit tests cho core/gpu.py
Kiểm tra: Cấu trúc dữ liệu GPU, fallback về CPU an toàn.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

from core.gpu import GPUDetector


def test_gpu_detector_structure():
    info = GPUDetector.detect_gpu()
    assert isinstance(info, dict)
    assert "has_nvenc" in info
    assert "has_qsv" in info
    assert "has_amf" in info
    assert "best_h264" in info
    assert "best_hevc" in info
    assert "acceleration_name" in info


def test_gpu_get_encoder_fallback():
    # Khi chọn CPU, phải luôn trả về libx264 hoặc libx265
    h264_cpu = GPUDetector.get_encoder("h264", preference="cpu")
    assert h264_cpu == "libx264"

    hevc_cpu = GPUDetector.get_encoder("hevc", preference="cpu")
    assert hevc_cpu == "libx265"

