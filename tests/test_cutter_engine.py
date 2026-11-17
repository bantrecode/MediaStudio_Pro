"""
Unit tests for CutterEngine (Phase 4)
100% pure Python tests, zero PySide6 imports.
"""

import pytest
from core.cutter_engine import CutterEngine


def test_format_seconds_to_time():
    assert CutterEngine.format_seconds_to_time(0) == "00:00:00"
    assert CutterEngine.format_seconds_to_time(65) == "00:01:05"
    assert CutterEngine.format_seconds_to_time(3665) == "01:01:05"
    assert CutterEngine.format_seconds_to_time(75.5, include_ms=True) == "00:01:15.500"
    assert CutterEngine.format_seconds_to_time(-10) == "00:00:00"


def test_parse_time_to_seconds():
    assert CutterEngine.parse_time_to_seconds("00:01:05") == 65.0
    assert CutterEngine.parse_time_to_seconds("01:01:05") == 3665.0
    assert CutterEngine.parse_time_to_seconds("01:15.500") == 75.5
    assert CutterEngine.parse_time_to_seconds("45") == 45.0
    assert CutterEngine.parse_time_to_seconds("invalid") == 0.0


def test_generate_split_segments():
    # Video 150s chia mỗi đoạn 60s -> 3 đoạn (0-60, 60-120, 120-150)
    segs = CutterEngine.generate_split_segments(150.0, 60.0)
    assert len(segs) == 3
    assert segs[0]["start"] == 0.0
    assert segs[0]["end"] == 60.0
    assert segs[0]["name"] == "Phần 1"

    assert segs[1]["start"] == 60.0
    assert segs[1]["end"] == 120.0
    assert segs[1]["name"] == "Phần 2"

    assert segs[2]["start"] == 120.0
    assert segs[2]["end"] == 150.0
    assert segs[2]["name"] == "Phần 3"


def test_generate_split_segments_with_overlap():
    # Video 100s, đoạn 60s, gối đầu 10s -> (0-60), (50-100)
    segs = CutterEngine.generate_split_segments(100.0, 60.0, overlap_seconds=10.0)
    assert len(segs) == 2
    assert segs[0]["start"] == 0.0
    assert segs[0]["end"] == 60.0
    assert segs[1]["start"] == 50.0
    assert segs[1]["end"] == 100.0


def test_get_keyframe_warning():
    warn = CutterEngine.get_keyframe_warning()
    assert "Keyframe" in warn
    assert "Stream Copy" in warn


def test_build_cut_copy_args():
    cmd = CutterEngine.build_cut_copy_args("C:/in.mp4", "C:/out.mp4", 10.0, 25.0)
    assert "-ss" in cmd
    assert "10.000" in cmd
    assert "-t" in cmd
    assert "15.000" in cmd
    assert "-c" in cmd
    assert "copy" in cmd
    assert "-avoid_negative_ts" in cmd


def test_build_cut_reencode_args():
    cmd = CutterEngine.build_cut_reencode_args("C:/in.mp4", "C:/out.mp4", 5.0, 15.0, use_gpu=False)
    assert "-ss" in cmd
    assert "5.000" in cmd
    assert "-t" in cmd
    assert "10.000" in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd

