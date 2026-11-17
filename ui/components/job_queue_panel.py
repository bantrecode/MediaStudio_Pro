"""
Job Queue Panel Component
Bảng quản lý hàng đợi tác vụ hiển thị phía dưới giao diện chính:
- Hiển thị danh sách các Job theo thời gian thực (Tên, Trạng thái, %, Tốc độ, ETA)
- Các nút tương tác: Tạm dừng / Tiếp tục, Hủy, Thử lại, Mở thư mục kết quả
- Nút Dọn dẹp các tác vụ đã hoàn thành
"""

import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QScrollArea, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Slot
from core.job_queue.job_model import Job, JobStatus
from ui.bridge import JobQueueBridge


class JobItemWidget(QFrame):
    """Widget đại diện cho 1 dòng tác vụ trong hàng đợi."""

    def __init__(self, job: Job, bridge: JobQueueBridge, parent=None):
        super().__init__(parent)
        self.job = job
        self.bridge = bridge
        self.setProperty("class", "card")
        self.setStyleSheet("""
            QFrame { background-color: #1A1D24; border: 1px solid #2B303C; border-radius: 8px; padding: 6px; margin-bottom: 4px; }
        """)
        self._setup_ui()
        self.update_data(job)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        # 1. Tên tác vụ và module
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_name = QLabel(self.job.name)
        self.lbl_name.setStyleSheet("font-weight: 600; color: #F1F5F9; font-size: 12px;")
        self.lbl_meta = QLabel(f"Module: {self.job.module_id.upper()}")
        self.lbl_meta.setStyleSheet("font-size: 10px; color: #94A3B8;")
        title_box.addWidget(self.lbl_name)
        title_box.addWidget(self.lbl_meta)
        layout.addLayout(title_box, 3)

        # 2. Thanh tiến trình và tốc độ / ETA
        progress_box = QVBoxLayout()
        progress_box.setSpacing(2)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setValue(self.job.progress)

        self.lbl_stats = QLabel("Tốc độ: -- | ETA: --")
        self.lbl_stats.setStyleSheet("font-size: 10px; color: #818CF8;")
        progress_box.addWidget(self.progress_bar)
        progress_box.addWidget(self.lbl_stats)
        layout.addLayout(progress_box, 4)

        # 3. Huy hiệu trạng thái
        self.lbl_status = QLabel("PENDING")
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status, 1)

        # 4. Các nút thao tác
        self.btn_pause = QPushButton("⏸️")
        self.btn_pause.setToolTip("Tạm dừng / Tiếp tục")
        self.btn_pause.setFixedSize(28, 28)
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_cancel = QPushButton("⏹️")
        self.btn_cancel.setToolTip("Hủy tác vụ")
        self.btn_cancel.setFixedSize(28, 28)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._cancel_job)

        self.btn_retry = QPushButton("🔄")
        self.btn_retry.setToolTip("Thử lại tác vụ")
        self.btn_retry.setFixedSize(28, 28)
        self.btn_retry.setCursor(Qt.PointingHandCursor)
        self.btn_retry.clicked.connect(self._retry_job)

        self.btn_open = QPushButton("📂")
        self.btn_open.setToolTip("Mở thư mục chứa file kết quả")
        self.btn_open.setFixedSize(28, 28)
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_output)

        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.btn_retry)
        layout.addWidget(self.btn_open)

    def update_data(self, job: Job):
        self.job = job
        self.lbl_name.setText(job.name)
        self.progress_bar.setValue(job.progress)
        self.lbl_stats.setText(f"Tốc độ: {job.speed} | ETA: {job.eta}")

        status = job.status
        self.lbl_status.setText(status.value)

        # Màu sắc trạng thái
        if status == JobStatus.RUNNING:
            self.lbl_status.setStyleSheet("background: #064E3B; color: #34D399; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px;")
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("⏸️")
            self.btn_cancel.setEnabled(True)
            self.btn_retry.setEnabled(False)
            self.btn_open.setEnabled(False)
        elif status == JobStatus.PAUSED:
            self.lbl_status.setStyleSheet("background: #78350F; color: #FBBF24; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px;")
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("▶️")
            self.btn_cancel.setEnabled(True)
            self.btn_retry.setEnabled(False)
            self.btn_open.setEnabled(False)
        elif status == JobStatus.COMPLETED:
            self.lbl_status.setStyleSheet("background: #14532D; color: #4ADE80; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px;")
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_retry.setEnabled(True)
            self.btn_open.setEnabled(bool(job.output_path and os.path.exists(job.output_path)))
        elif status == JobStatus.FAILED:
            self.lbl_status.setStyleSheet("background: #7F1D1D; color: #F87171; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px;")
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_retry.setEnabled(True)
            self.btn_open.setEnabled(False)
        elif status == JobStatus.CANCELLED:
            self.lbl_status.setStyleSheet("background: #374151; color: #9CA3AF; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px;")
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_retry.setEnabled(True)
            self.btn_open.setEnabled(False)
        else:  # PENDING
            self.lbl_status.setStyleSheet("background: #1E293B; color: #94A3B8; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px;")
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("⏸️")
            self.btn_cancel.setEnabled(True)
            self.btn_retry.setEnabled(False)
            self.btn_open.setEnabled(False)

    def _toggle_pause(self):
        if self.job.status == JobStatus.RUNNING:
            self.bridge.pause_job(self.job.id)
        elif self.job.status == JobStatus.PAUSED:
            self.bridge.resume_job(self.job.id)

    def _cancel_job(self):
        self.bridge.cancel_job(self.job.id)

    def _retry_job(self):
        self.bridge.retry_job(self.job.id)

    def _open_output(self):
        if self.job.output_path and os.path.exists(self.job.output_path):
            folder = os.path.dirname(self.job.output_path)
            if os.name == "nt":
                os.startfile(folder)


class JobQueuePanel(QWidget):
    """Panel hiển thị toàn bộ hàng đợi tác vụ ở đáy cửa sổ."""

    def __init__(self, bridge: JobQueueBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.job_widgets: dict[str, JobItemWidget] = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 8)
        layout.setSpacing(6)

        # Header hàng đợi
        header = QHBoxLayout()
        self.lbl_header = QLabel("⚡ Hàng Đợi Tác Vụ (0 đang chạy, 0 đang chờ)")
        self.lbl_header.setStyleSheet("font-weight: 600; color: #CBD5E1; font-size: 12px;")

        self.btn_clear = QPushButton("Dọn Tác Vụ Xong")
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setStyleSheet("padding: 2px 10px; font-size: 11px;")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_finished)

        header.addWidget(self.lbl_header)
        header.addStretch()
        header.addWidget(self.btn_clear)
        layout.addLayout(header)

        # Vùng cuộn danh sách Job
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedHeight(120)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.list_container)
        layout.addWidget(self.scroll)

    def _connect_signals(self):
        self.bridge.job_added.connect(self._on_job_added)
        self.bridge.job_updated.connect(self._on_job_updated)
        self.bridge.job_progress.connect(self._on_job_progress)
        self.bridge.job_finished.connect(self._on_job_finished)

    @Slot(object)
    def _on_job_added(self, job: Job):
        if job.id not in self.job_widgets:
            widget = JobItemWidget(job, self.bridge)
            self.job_widgets[job.id] = widget
            # Chèn vào trước stretch
            self.list_layout.insertWidget(self.list_layout.count() - 1, widget)
        self._update_header_stats()

    @Slot(object)
    def _on_job_updated(self, job: Job):
        widget = self.job_widgets.get(job.id)
        if widget:
            widget.update_data(job)
        self._update_header_stats()

    @Slot(object)
    def _on_job_progress(self, job: Job):
        widget = self.job_widgets.get(job.id)
        if widget:
            widget.update_data(job)
        self._update_header_stats()

    @Slot(object)
    def _on_job_finished(self, job: Job):
        widget = self.job_widgets.get(job.id)
        if widget:
            widget.update_data(job)
        self._update_header_stats()

    def _update_header_stats(self):
        jobs = self.bridge.get_all_jobs()
        running = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
        pending = sum(1 for j in jobs if j.status == JobStatus.PENDING)
        self.lbl_header.setText(f"⚡ Hàng Đợi Tác Vụ ({running} đang chạy, {pending} đang chờ)")

    def _clear_finished(self):
        """Xóa các widget của job đã hoàn thành hoặc bị hủy khỏi màn hình hiển thị."""
        jobs = self.bridge.get_all_jobs()
        for j in jobs:
            if j.status in [JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED]:
                widget = self.job_widgets.pop(j.id, None)
                if widget:
                    self.list_layout.removeWidget(widget)
                    widget.deleteLater()
        self._update_header_stats()

