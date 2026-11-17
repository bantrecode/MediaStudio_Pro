"""
Unit tests for MergerEngine (Phase 3)
100% pure Python tests, zero PySide6 imports.
"""

import os
import tempfile
import pytest
from core.merger_engine import MergerEngine


def test_compatibility_compatible():
    videos = [
        {
            "filename": "clip1.mp4",
            "video_codec": "h264",
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "has_audio": True,
            "audio_codec": "aac",
            "sample_rate": 48000
        },
        {
            "filename": "clip2.mp4",
            "video_codec": "h264",
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "has_audio": True,
            "audio_codec": "aac",
            "sample_rate": 48000
        }
    ]
    compatible, msg = MergerEngine.check_compatibility(videos)
    assert compatible is True
    assert "Copy Mode" in msg


def test_compatibility_resolution_mismatch():
    videos = [
        {"filename": "1.mp4", "video_codec": "h264", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": False},
        {"filename": "2.mp4", "video_codec": "h264", "width": 1280, "height": 720, "fps": 30.0, "has_audio": False}
    ]
    compatible, msg = MergerEngine.check_compatibility(videos)
    assert compatible is False
    assert "độ phân giải" in msg


def test_compatibility_fps_mismatch():
    videos = [
        {"filename": "1.mp4", "video_codec": "h264", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": False},
        {"filename": "2.mp4", "video_codec": "h264", "width": 1920, "height": 1080, "fps": 60.0, "has_audio": False}
    ]
    compatible, msg = MergerEngine.check_compatibility(videos)
    assert compatible is False
    assert "khung hình" in msg


def test_compatibility_vp9_rejection():
    videos = [
        {"filename": "1.webm", "video_codec": "vp9", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": False},
        {"filename": "2.webm", "video_codec": "vp9", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": False}
    ]
    compatible, msg = MergerEngine.check_compatibility(videos)
    assert compatible is False
    assert "VP9" in msg


def test_compatibility_audio_mismatch():
    videos = [
        {"filename": "1.mp4", "video_codec": "h264", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": True, "audio_codec": "aac", "sample_rate": 48000},
        {"filename": "2.mp4", "video_codec": "h264", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": False}
    ]
    compatible, msg = MergerEngine.check_compatibility(videos)
    assert compatible is False
    assert "âm thanh" in msg


def test_write_concat_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        list_txt = os.path.join(tmp_dir, "concat_list.txt")
        files = ["D:/video 1.mp4", "D:/video's 2.mp4"]
        res = MergerEngine.write_concat_file(files, list_txt)
        assert os.path.exists(res)

        with open(res, "r", encoding="utf-8") as f:
            content = f.read()

        assert "file 'D:/video 1.mp4'" in content
        assert "file 'D:/video'\\''s 2.mp4'" in content


def test_build_copy_args():
    args = MergerEngine.build_copy_args("C:/temp/list.txt", "C:/temp/out.mp4")
    assert "-f" in args
    assert "concat" in args
    assert "-c" in args
    assert "copy" in args
    assert "C:/temp/out.mp4" in args


def test_build_reencode_args_basic():
    videos = [
        {"file_path": "C:/v1.mp4", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": True, "duration": 5.0},
        {"file_path": "C:/v2.mp4", "width": 1280, "height": 720, "fps": 24.0, "has_audio": False, "duration": 10.0}
    ]
    cmd = MergerEngine.build_reencode_args(
        videos_info=videos,
        output_path="C:/out.mp4",
        target_resolution=(1920, 1080),
        aspect_ratio_mode="letterbox",
        use_gpu=False
    )

    assert "-i" in cmd
    assert "C:/v1.mp4" in cmd
    assert "C:/v2.mp4" in cmd
    assert "-filter_complex" in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd
    assert "C:/out.mp4" in cmd


def test_build_reencode_args_with_bgm():
    videos = [
        {"file_path": "C:/v1.mp4", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": True, "duration": 5.0},
        {"file_path": "C:/v2.mp4", "width": 1920, "height": 1080, "fps": 30.0, "has_audio": True, "duration": 10.0}
    ]
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        bgm_path = f.name

    try:
        cmd = MergerEngine.build_reencode_args(
            videos_info=videos,
            output_path="C:/out.mp4",
            bgm_path=bgm_path,
            bgm_volume=0.25,
            orig_volume=0.8,
            loop_bgm=True,
            use_gpu=False
        )

        cmd_str = " ".join(cmd)
        assert "-stream_loop" in cmd
        assert bgm_path in cmd
        assert "amix=inputs=2" in cmd_str
        assert "volume=0.25" in cmd_str
        assert "volume=0.80" in cmd_str
    finally:
        if os.path.exists(bgm_path):
            os.remove(bgm_path)

