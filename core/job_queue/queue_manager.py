"""
Queue Manager Core Module
Hàng đợi tác vụ dùng chung, đa luồng thuần Python:
- Giới hạn số lượng tác vụ chạy song song (max_concurrent)
- Hỗ trợ Tạm dừng (Pause), Tiếp tục (Resume), Hủy (Cancel), Thử lại (Retry)
- Kiểm tra dung lượng ổ đĩa trước khi chạy
- Tự động ghi nhận lịch sử vào SQLite (core.database)
- Cung cấp event callbacks để UI (PySide6) lắng nghe thread-safe.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from core.job_queue.job_model import Job, JobStatus
from core.system import check_disk_space
from core.database import HistoryDB
from core.logger import get_logger


class QueueManager:
    _instance = None

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max(1, max_concurrent)
        self.jobs: Dict[str, Job] = {}
        self.pending_queue: List[str] = []
        self._lock = threading.RLock()
        self._executors: Dict[str, Callable] = {}

        # Callbacks nối sang UI
        self.on_job_added: Optional[Callable[[Job], None]] = None
        self.on_job_updated: Optional[Callable[[Job], None]] = None
        self.on_job_progress: Optional[Callable[[Job], None]] = None
        self.on_job_log: Optional[Callable[[Job, str], None]] = None
        self.on_job_finished: Optional[Callable[[Job], None]] = None
        self.on_all_finished: Optional[Callable[[], None]] = None

        self._is_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    @classmethod
    def get_instance(cls, max_concurrent: int = 2) -> "QueueManager":
        if cls._instance is None:
            cls._instance = QueueManager(max_concurrent=max_concurrent)
        return cls._instance

    def register_executor(self, module_id: str, executor_func: Callable):
        """
        Đăng ký hàm thực thi nghiệp vụ cho từng module:
        executor_func(job, progress_callback, log_callback, cancel_event, pause_event) -> (success: bool, output_path: str, error_msg: str)
        """
        with self._lock:
            self._executors[module_id] = executor_func

    def submit(self, job: Job) -> str:
        """Đưa một Job mới vào hàng đợi."""
        logger = get_logger()
        with self._lock:
            self.jobs[job.id] = job
            self.pending_queue.append(job.id)
            job.status = JobStatus.PENDING

        logger.info(f"Đã thêm Job vào hàng đợi: [{job.id}] {job.name} (Module: {job.module_id})")

        # Ghi nhận vào SQLite (Lịch sử & Hàng đợi bền vững)
        try:
            hdb = HistoryDB.get_instance()
            hdb.record_job(
                job_id=job.id,
                module_id=job.module_id,
                name=job.name,
                status=job.status.value,
                output_path=job.output_path
            )
            hdb.save_queue_job(job.to_dict(), priority=len(self.pending_queue))
        except Exception:
            pass

        if self.on_job_added:
            self.on_job_added(job)
        return job.id

    def pause(self, job_id: str) -> bool:
        """Tạm dừng một Job đang chạy hoặc đang chờ."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job.status == JobStatus.PENDING:
                if job_id in self.pending_queue:
                    self.pending_queue.remove(job_id)
                job.status = JobStatus.PAUSED
                if self.on_job_updated:
                    self.on_job_updated(job)
                return True

            if job.status == JobStatus.RUNNING and job._pause_event:
                job._pause_event.clear()  # Báo dừng luồng
                job.status = JobStatus.PAUSED
                if self.on_job_updated:
                    self.on_job_updated(job)
                return True
        return False

    def resume(self, job_id: str) -> bool:
        """Tiếp tục một Job đang bị tạm dừng."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.status != JobStatus.PAUSED:
                return False

            if job._pause_event:
                job._pause_event.set()  # Đánh thức luồng
                job.status = JobStatus.RUNNING
            else:
                job.status = JobStatus.PENDING
                self.pending_queue.append(job_id)

            if self.on_job_updated:
                self.on_job_updated(job)
            return True

    def cancel(self, job_id: str) -> bool:
        """Hủy một Job."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job.status == JobStatus.PENDING:
                if job_id in self.pending_queue:
                    self.pending_queue.remove(job_id)
                job.status = JobStatus.CANCELLED
                job.append_log("Tác vụ đã bị hủy khi đang chờ.")
                self._update_db_status(job)
                if self.on_job_updated:
                    self.on_job_updated(job)
                return True

            if job.status in [JobStatus.RUNNING, JobStatus.PAUSED]:
                if job._cancel_event:
                    job._cancel_event.set()
                if job._pause_event:
                    job._pause_event.set()
                if job._runner_handle and hasattr(job._runner_handle, "cancel"):
                    job._runner_handle.cancel()

                job.status = JobStatus.CANCELLED
                job.append_log("Đã phát tín hiệu hủy tác vụ.")
                self._update_db_status(job)
                if self.on_job_updated:
                    self.on_job_updated(job)
                return True
        return False

    def retry(self, job_id: str) -> bool:
        """Chạy lại một Job đã hoàn thành, lỗi hoặc bị hủy."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                return False

            job.status = JobStatus.PENDING
            job.progress = 0
            job.speed = "--"
            job.eta = "--:--"
            job.error_message = ""
            job.logs.clear()
            job.append_log("Đã đưa lại tác vụ vào hàng đợi để thử lại.")
            self.pending_queue.append(job_id)

            if self.on_job_updated:
                self.on_job_updated(job)
            return True

    def set_max_concurrent(self, n: int):
        with self._lock:
            self.max_concurrent = max(1, n)

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[Job]:
        with self._lock:
            return list(self.jobs.values())

    def _get_running_count(self) -> int:
        return sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)

    def load_persisted_jobs(self):
        """Khôi phục các job dang dở từ SQLite khi khởi động ứng dụng."""
        try:
            persisted = HistoryDB.get_instance().get_persisted_queue_jobs()
            with self._lock:
                for item in persisted:
                    st_str = item.get("status", JobStatus.PENDING.value)
                    status = JobStatus(st_str) if st_str in [s.value for s in JobStatus] else JobStatus.PENDING

                    # Nếu job đang RUNNING lúc app tắt -> chuyển thành PAUSED để người dùng bấm chạy tiếp
                    if status == JobStatus.RUNNING:
                        status = JobStatus.PAUSED

                    job = Job(
                        module_id=item["module_id"],
                        name=item["name"],
                        params=item.get("params", {}),
                        id=item["id"],
                        status=status,
                        progress=item.get("progress", 0),
                        speed=item.get("speed", "--"),
                        eta=item.get("eta", "--:--"),
                        error_message=item.get("error_message", ""),
                        output_path=item.get("output_path", ""),
                        created_at=item.get("created_at", datetime.now().isoformat()),
                        finished_at=item.get("finished_at", "")
                    )
                    job.append_log("Khôi phục tác vụ từ phiên làm việc trước.")
                    self.jobs[job.id] = job
                    if status == JobStatus.PENDING:
                        self.pending_queue.append(job.id)

                    if self.on_job_added:
                        self.on_job_added(job)
        except Exception as e:
            get_logger().error(f"Lỗi khi khôi phục hàng đợi từ SQLite: {e}")

    def reorder_jobs(self, job_ids: List[str]):
        """Cập nhật thứ tự các job đang chờ trong hàng đợi."""
        with self._lock:
            new_pending = [jid for jid in job_ids if jid in self.pending_queue]
            for jid in self.pending_queue:
                if jid not in new_pending:
                    new_pending.append(jid)
            self.pending_queue = new_pending
            try:
                HistoryDB.get_instance().update_queue_order(self.pending_queue)
            except Exception:
                pass

    def clear_finished_jobs(self):
        """Xóa các job đã hoàn thành, lỗi hoặc bị hủy."""
        with self._lock:
            to_remove = [
                jid for jid, j in self.jobs.items()
                if j.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            ]
            for jid in to_remove:
                del self.jobs[jid]
            try:
                HistoryDB.get_instance().clear_finished_jobs()
            except Exception:
                pass

    def _update_db_status(self, job: Job):
        try:
            hdb = HistoryDB.get_instance()
            hdb.update_job_status(
                job_id=job.id,
                status=job.status.value,
                error_message=job.error_message,
                output_path=job.output_path
            )
            hdb.update_queue_job_status(
                job_id=job.id,
                status=job.status.value,
                progress=job.progress,
                speed=job.speed,
                eta=job.eta,
                error_message=job.error_message,
                output_path=job.output_path
            )
        except Exception:
            pass

    def _scheduler_loop(self):
        """Vòng lặp ngầm điều phối các job sang Worker thread."""
        while self._is_running:
            job_to_run = None
            with self._lock:
                if self._get_running_count() < self.max_concurrent and self.pending_queue:
                    job_id = self.pending_queue.pop(0)
                    job_to_run = self.jobs.get(job_id)

            if job_to_run:
                worker_t = threading.Thread(target=self._run_job_worker, args=(job_to_run,), daemon=True)
                worker_t.start()
            else:
                time.sleep(0.15)

    def _run_job_worker(self, job: Job):
        logger = get_logger()
        with self._lock:
            job.status = JobStatus.RUNNING
            job._cancel_event = threading.Event()
            job._pause_event = threading.Event()
            job._pause_event.set()  # Mặc định không pause

        logger.info(f"Bắt đầu chạy Job: [{job.id}] {job.name}")
        job.append_log("Bắt đầu thực thi tác vụ...")
        if self.on_job_updated:
            self.on_job_updated(job)

        executor = self._executors.get(job.module_id)
        if not executor:
            err = f"Chưa đăng ký bộ xử lý cho module '{job.module_id}'"
            job.status = JobStatus.FAILED
            job.error_message = err
            job.append_log(f"[ERROR] {err}")
            self._update_db_status(job)
            if self.on_job_finished:
                self.on_job_finished(job)
            return

        # Kiểm tra dung lượng ổ đĩa
        target_dir = job.params.get("output_dir") or job.params.get("output_path") or "."
        has_space, free_bytes, _ = check_disk_space(target_dir, required_bytes=100 * 1024 * 1024)
        if not has_space:
            err = f"Dung lượng ổ đĩa còn lại quá thấp ({free_bytes // 1024 // 1024} MB). Yêu cầu tối thiểu 100 MB."
            job.status = JobStatus.FAILED
            job.error_message = err
            job.append_log(f"[ERROR] {err}")
            self._update_db_status(job)
            if self.on_job_finished:
                self.on_job_finished(job)
            return

        # Callbacks tiến độ & log riêng của job
        def progress_cb(percent: int, speed: str, eta: str):
            job.progress = percent
            job.speed = speed
            job.eta = eta
            if self.on_job_progress:
                self.on_job_progress(job)

        def log_cb(text: str):
            job.append_log(text)
            if self.on_job_log:
                self.on_job_log(job, text)

        try:
            success, output_path, err_msg = executor(
                job=job,
                progress_callback=progress_cb,
                log_callback=log_cb,
                cancel_event=job._cancel_event,
                pause_event=job._pause_event
            )

            job.finished_at = datetime.now().isoformat()
            if job._cancel_event.is_set():
                job.status = JobStatus.CANCELLED
                job.append_log("Tác vụ đã bị hủy bởi người dùng.")
            elif success:
                job.status = JobStatus.COMPLETED
                job.progress = 100
                job.output_path = output_path or job.output_path
                job.append_log("Tác vụ hoàn thành thành công!")
            else:
                job.status = JobStatus.FAILED
                job.error_message = err_msg or "Lỗi xử lý không xác định"
                job.append_log(f"[ERROR] {job.error_message}")

        except Exception as e:
            job.finished_at = datetime.now().isoformat()
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.append_log(f"[EXCEPTION] {e}")
            logger.exception(f"Lỗi ngoại lệ khi thực thi Job {job.id}: {e}")

        self._update_db_status(job)

        if self.on_job_finished:
            self.on_job_finished(job)

        # Kiểm tra nếu tất cả job đều đã xong
        with self._lock:
            if not self.pending_queue and self._get_running_count() == 0:
                if self.on_all_finished:
                    self.on_all_finished()

