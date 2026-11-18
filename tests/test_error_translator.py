"""
Unit tests for Error Translator (core/error_translator.py)
Kiểm thử tính năng phân tích và dịch lỗi FFmpeg / yt-dlp sang tiếng Việt dễ hiểu.
"""

from core.error_translator import translate_error


def test_translate_ffmpeg_errors():
    err1 = "No space left on device while writing frame"
    trans1 = translate_error(err1, module_id="converter")
    assert "hết dung lượng" in trans1.lower()

    err2 = "Permission denied: 'C:\\output.mp4'"
    trans2 = translate_error(err2, module_id="converter")
    assert "quyền" in trans2.lower()

    err3 = "Unknown encoder 'libx265'"
    trans3 = translate_error(err3, module_id="converter")
    assert "bộ mã hóa" in trans3.lower()

    err4 = "moov atom not found"
    trans4 = translate_error(err4, module_id="cutter")
    assert "moov atom" in trans4.lower() or "video nguồn" in trans4.lower()


def test_translate_ytdlp_errors():
    err1 = "ERROR: [youtube] 12345: HTTP Error 403: Forbidden"
    trans1 = translate_error(err1, module_id="downloader")
    assert "403" in trans1 or "từ chối" in trans1.lower()

    err2 = "Sign in to confirm you’re not a bot"
    trans2 = translate_error(err2, module_id="downloader")
    assert "bot" in trans2.lower() or "đăng nhập" in trans2.lower()

    err3 = "ERROR: Video unavailable. This video has been removed."
    trans3 = translate_error(err3, module_id="downloader")
    assert "không khả dụng" in trans3.lower() or "xóa" in trans3.lower()

    err4 = "Unsupported URL: https://invalid.site/xyz"
    trans4 = translate_error(err4, module_id="downloader")
    assert "hỗ trợ" in trans4.lower() or "hợp lệ" in trans4.lower()


def test_translate_fallback():
    err = "Some completely unknown error code 9999"
    trans = translate_error(err)
    assert "Lỗi xử lý" in trans
    assert "Sao chép log" in trans
