"""
Unit tests cho core/database.py
Kiểm tra: Ghi nhận job, cập nhật status, lưu vết link chống trùng lặp, xóa lịch sử SQLite.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

from pathlib import Path
from core.database import HistoryDB


def test_database_jobs_history(temp_test_dir):
    db_file = temp_test_dir / "test_history.db"
    db = HistoryDB(db_path=str(db_file))

    # Kiểm tra version schema
    with db._get_connection() as conn:
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver == 1

    # Ghi nhận job
    job_id = "job-uuid-12345"
    db.record_job(job_id=job_id, module_id="converter", name="Test Video", status="PENDING")

    recent = db.get_recent_jobs()
    assert len(recent) == 1
    assert recent[0]["id"] == job_id
    assert recent[0]["status"] == "PENDING"

    # Cập nhật status
    db.update_job_status(job_id=job_id, status="COMPLETED", output_path="/output/test.mp4")
    recent2 = db.get_recent_jobs()
    assert recent2[0]["status"] == "COMPLETED"
    assert recent2[0]["output_path"] == "/output/test.mp4"


def test_database_url_deduplication(temp_test_dir):
    db_file = temp_test_dir / "test_history.db"
    db = HistoryDB(db_path=str(db_file))

    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert not db.is_url_downloaded(test_url)

    db.record_downloaded_url(test_url, title="Never Gonna Give You Up")
    assert db.is_url_downloaded(test_url)
    assert not db.is_url_downloaded("https://other-url.com")


def test_database_clear_history(temp_test_dir):
    db_file = temp_test_dir / "test_history.db"
    db = HistoryDB(db_path=str(db_file))

    db.record_job("j1", "downloader", "Video 1", "COMPLETED")
    db.record_downloaded_url("https://url.com", "Title")
    assert len(db.get_recent_jobs()) == 1

    db.clear_history()
    assert len(db.get_recent_jobs()) == 0
    assert not db.is_url_downloaded("https://url.com")

