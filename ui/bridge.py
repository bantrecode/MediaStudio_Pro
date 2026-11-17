"""
Job Queue Bridge
Cầu nối thread-safe giữa QueueManager (chạy trên thread Python) và PySide6 GUI.
Chuyển tiếp các sự kiện từ QueueManager thành Qt Signals an toàn.
"""

from PySide6.QtCore import QObject, Signal
from core.job_queue.queue_manager import QueueManager
from core.job_queue.job_model import Job


class JobQueueBridge(QObject):
    # Signals giao tiếp với giao diện PySide6
    job_added = Signal(object)              # (Job)
    job_updated = Signal(object)            # (Job)
    job_progress = Signal(object)           # (Job)
    job_log = Signal(object, str)           # (Job, log_line)
    job_finished = Signal(object)          # (Job)
    all_jobs_finished = Signal()

    def __init__(self, queue_manager: QueueManager, parent=None):
        super().__init__(parent)
        self.queue_manager = queue_manager
        self._connect_callbacks()

    def _connect_callbacks(self):
        self.queue_manager.on_job_added = lambda j: self.job_added.emit(j)
        self.queue_manager.on_job_updated = lambda j: self.job_updated.emit(j)
        self.queue_manager.on_job_progress = lambda j: self.job_progress.emit(j)
        self.queue_manager.on_job_log = lambda j, line: self.job_log.emit(j, line)
        self.queue_manager.on_job_finished = lambda j: self.job_finished.emit(j)
        self.queue_manager.on_all_finished = lambda: self.all_jobs_finished.emit()

    def submit_job(self, job: Job) -> str:
        return self.queue_manager.submit(job)

    def pause_job(self, job_id: str) -> bool:
        return self.queue_manager.pause(job_id)

    def resume_job(self, job_id: str) -> bool:
        return self.queue_manager.resume(job_id)

    def cancel_job(self, job_id: str) -> bool:
        return self.queue_manager.cancel(job_id)

    def retry_job(self, job_id: str) -> bool:
        return self.queue_manager.retry(job_id)

    def get_all_jobs(self):
        return self.queue_manager.get_all_jobs()

