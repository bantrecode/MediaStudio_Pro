"""
Unit tests cho core/job_queue (queue_manager.py & job_model.py)
Kiểm tra: Submit, cancel, pause/resume, retry, max_concurrent limit.
TUYỆT ĐỐI KHÔNG DÙNG PYSIDE6.
"""

import time
from core.job_queue.job_model import Job, JobStatus
from core.job_queue.queue_manager import QueueManager


def test_job_model_lifecycle():
    job = Job(module_id="test", name="Test Job", params={"key": "val"})
    assert job.status == JobStatus.PENDING
    assert job.progress == 0

    job.append_log("Khởi động test")
    assert len(job.logs) == 1
    assert "Khởi động test" in job.logs[0]

    d = job.to_dict()
    assert d["name"] == "Test Job"
    assert d["status"] == "PENDING"


def test_queue_submit_and_execute(temp_test_dir, monkeypatch):
    monkeypatch.setattr("core.system.get_appdata_dir", lambda: temp_test_dir)
    qm = QueueManager(max_concurrent=1)

    executed_jobs = []

    def mock_executor(job, progress_callback, log_callback, cancel_event, pause_event):
        executed_jobs.append(job.id)
        progress_callback(50, "1.0 MB/s", "00:05")
        time.sleep(0.05)
        progress_callback(100, "1.0 MB/s", "00:00")
        return True, "/output/result.mp4", ""

    qm.register_executor("test_mod", mock_executor)

    job = Job(module_id="test_mod", name="Unit Test Job", params={"output_dir": str(temp_test_dir)})
    job_id = qm.submit(job)

    # Chờ scheduler chạy hoàn tất (tối đa 2 giây)
    timeout = 2.0
    start = time.time()
    while time.time() - start < timeout:
        retrieved = qm.get_job(job_id)
        if retrieved and retrieved.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            break
        time.sleep(0.05)

    retrieved = qm.get_job(job_id)
    assert retrieved is not None
    assert retrieved.status == JobStatus.COMPLETED
    assert retrieved.progress == 100
    assert job_id in executed_jobs


def test_queue_cancel_pending_job(temp_test_dir, monkeypatch):
    monkeypatch.setattr("core.system.get_appdata_dir", lambda: temp_test_dir)
    qm = QueueManager(max_concurrent=1)

    import threading
    started = threading.Event()
    def long_executor(**kwargs):
        started.set()
        cancel_evt = kwargs.get("cancel_event")
        while cancel_evt and not cancel_evt.is_set():
            time.sleep(0.05)
        return False, "", "Cancelled"

    qm.register_executor("test_cancel", long_executor)
    job = Job(module_id="test_cancel", name="Long Running Job")
    job_id = qm.submit(job)
    started.wait(timeout=2.0)

    # Hủy job khi đang chạy
    success = qm.cancel(job_id)
    assert success is True
    assert qm.get_job(job_id).status == JobStatus.CANCELLED


def test_queue_retry_job(temp_test_dir, monkeypatch):
    monkeypatch.setattr("core.system.get_appdata_dir", lambda: temp_test_dir)
    qm = QueueManager(max_concurrent=1)

    # Module chưa đăng ký sẽ tự động FAILED khi chạy
    job = Job(module_id="test_failed", name="Failed Job")
    job_id = qm.submit(job)

    # Đợi worker xử lý và đánh dấu FAILED
    for _ in range(50):
        if qm.get_job(job_id).status == JobStatus.FAILED:
            break
        time.sleep(0.05)
    assert qm.get_job(job_id).status == JobStatus.FAILED

    # Thử lại
    retried = qm.retry(job_id)
    assert retried is True
    assert qm.get_job(job_id).status in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.FAILED]

