"""
Unit tests for Persistent Job Queue & HistoryDB v2
Kiểm thử tính năng lưu trữ hàng đợi bền vững vào SQLite, khôi phục job dang dở và đổi thứ tự ưu tiên.
"""

import tempfile
import os
from core.database import HistoryDB
from core.job_queue.job_model import Job, JobStatus
from core.job_queue.queue_manager import QueueManager


def test_sqlite_queue_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    try:
        db = HistoryDB(db_path=temp_db_path)

        # 1. Lưu job vào hàng đợi bền vững
        job1 = Job(module_id="converter", name="Convert 1", params={"format": "mp4"})
        job2 = Job(module_id="downloader", name="Download 2", params={"url": "https://youtu.be/123"})

        db.save_queue_job(job1.to_dict(), priority=0)
        db.save_queue_job(job2.to_dict(), priority=1)

        # 2. Lấy danh sách job bền vững
        persisted = db.get_persisted_queue_jobs()
        assert len(persisted) == 2
        assert persisted[0]["id"] == job1.id
        assert persisted[0]["params"]["format"] == "mp4"
        assert persisted[1]["id"] == job2.id

        # 3. Đổi thứ tự ưu tiên
        db.update_queue_order([job2.id, job1.id])
        reordered = db.get_persisted_queue_jobs()
        assert reordered[0]["id"] == job2.id
        assert reordered[1]["id"] == job1.id

        # 4. Cập nhật trạng thái
        db.update_queue_job_status(job2.id, status=JobStatus.COMPLETED.value, progress=100)
        updated = db.get_persisted_queue_jobs()
        assert updated[0]["status"] == JobStatus.COMPLETED.value

        # 5. Dọn job hoàn thành
        db.clear_finished_jobs()
        after_clear = db.get_persisted_queue_jobs()
        assert len(after_clear) == 1
        assert after_clear[0]["id"] == job1.id

    finally:
        if os.path.exists(temp_db_path):
            try:
                os.unlink(temp_db_path)
            except Exception:
                pass


def test_queue_manager_reorder_and_clear():
    qm = QueueManager.get_instance()
    id1, id2, id3 = "job-id-1", "job-id-2", "job-id-3"
    qm.pending_queue = [id1, id2, id3]
    qm.reorder_jobs([id3, id1, id2])
    assert qm.pending_queue == [id3, id1, id2]
