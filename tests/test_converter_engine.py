"""
Unit tests cho core/converter_engine.py
Kiểm tra: tính toán target bitrate, ước tính dung lượng đầu ra, build FFmpeg args cho Remux và Re-encode.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

from core.converter_engine import ConverterEngine


def test_target_bitrate_calculation():
    # 60 giây, ép < 24MB
    bitrate = ConverterEngine.calculate_target_bitrate_for_max_size(duration=60.0, max_size_mb=24.0)
    assert bitrate > 1000
    # Tổng dung lượng ước tính phải nhỏ hơn 24MB
    estimated_bytes = (bitrate + 128) * 1000 / 8 * 60
    assert estimated_bytes < 24 * 1024 * 1024


def test_estimate_output_size():
    # Remux trả về nguyên dung lượng gốc
    orig_size = 50 * 1024 * 1024
    remux_est = ConverterEngine.estimate_output_size(duration=60.0, is_remux=True, original_size=orig_size)
    assert remux_est == orig_size

    # CRF thấp (chất lượng cao) cho ra file nặng hơn CRF cao (nén mạnh)
    size_crf18 = ConverterEngine.estimate_output_size(duration=60.0, crf=18, resolution="1080p")
    size_crf28 = ConverterEngine.estimate_output_size(duration=60.0, crf=28, resolution="1080p")
    assert size_crf18 > size_crf28


def test_build_remux_args():
    args = ConverterEngine.build_conversion_args(
        input_path="input.mov",
        output_path="output.mp4",
        mode="remux"
    )
    assert "-c" in args
    assert "copy" in args
    assert args[-1] == "output.mp4"


def test_build_audio_extract_args():
    args = ConverterEngine.build_conversion_args(
        input_path="video.mov",
        output_path="audio.mp3",
        target_format="mp3"
    )
    assert "-vn" in args
    assert "libmp3lame" in args


def test_build_zalo_preset_args():
    args = ConverterEngine.build_conversion_args(
        input_path="video.mov",
        output_path="output.mp4",
        mode="preset",
        preset_name="zalo_25mb",
        duration=120.0
    )
    assert "-maxrate" in args
    assert "-bufsize" in args
    assert "+faststart" in args


def test_scan_directory_for_media(temp_test_dir):
    f1 = temp_test_dir / "clip1.mov"
    f2 = temp_test_dir / "clip2.mp4"
    f3 = temp_test_dir / "doc.txt"
    f1.write_text("dummy")
    f2.write_text("dummy")
    f3.write_text("dummy")

    scanned = ConverterEngine.scan_directory_for_media(str(temp_test_dir))
    assert len(scanned) == 2
    assert any("clip1.mov" in s for s in scanned)
    assert any("clip2.mp4" in s for s in scanned)

