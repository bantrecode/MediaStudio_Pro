"""
Unit tests cho core/ytdlp_engine.py
Kiểm tra: clean_filename, build_cli_arguments cho video, audio-only, phụ đề, giới hạn tốc độ.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

from core.ytdlp_engine import YtDlpEngine, clean_filename


def test_clean_filename_vietnamese():
    name = "Bài Ca Hy Vọng - Ca sĩ Ánh Tuyết [Full HD] : 2026?.mp4"
    cleaned = clean_filename(name)
    assert "Hy Vong" in cleaned or "Hy_Vong" in cleaned
    assert "Ánh" not in cleaned
    for invalid in [":", "?", "[", "]", "*", "<", ">", "|", "/", "\\"]:
        assert invalid not in cleaned


def test_build_cli_arguments_video():
    args = YtDlpEngine.build_cli_arguments(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        output_dir="/downloads",
        quality="1080p",
        download_subs=True
    )
    assert "--no-playlist" in args
    assert "--write-subs" in args
    assert "--merge-output-format" in args
    assert "mp4" in args
    assert args[-1] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_build_cli_arguments_audio_only():
    args = YtDlpEngine.build_cli_arguments(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        output_dir="/downloads",
        audio_only=True,
        audio_format="mp3",
        limit_rate="2M"
    )
    assert "-x" in args
    assert "--audio-format" in args
    assert "mp3" in args
    assert "--limit-rate" in args
    assert "2M" in args


def test_build_cli_arguments_playlist():
    args = YtDlpEngine.build_cli_arguments(
        url="https://www.youtube.com/playlist?list=PL123",
        output_dir="/downloads",
        is_playlist=True
    )
    assert "--yes-playlist" in args

