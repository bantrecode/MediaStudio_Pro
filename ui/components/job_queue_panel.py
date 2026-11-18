"""
Job Queue Panel Component
Bảng điều khiển hàng đợi tác vụ ở đáy màn hình chính:
- Hiển thị danh sách các Job đang xử lý / đang chờ / hoàn thành / lỗi
- Hỗ trợ Tạm dừng, Tiếp tục, Thử lại, Hủy tác vụ
- Hỗ trợ đổi thứ tự ưu tiên (Lên / Xuống) cho các tác vụ đang chờ
- Dịch lỗi FFmpeg/yt-dlp sang tiếng Việt dễ hiểu và cung cấp nút 'Sao chép log'
- Ước tính thời gian còn lại (ETA) và dung lượng đầu ra dự kiến
"""

import os
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QScrollArea, QFrame, QStackedWidget, QApplication, QToolTip
)
from PySide6.QtCore import Qt, Slot, QPoint
from core.job_queue.job_model import Job, JobStatus
from core.error_translator import translate_error
from core.system import format_bytes
from ui.bridge import JobQueueBridge
from ui.components.empty_state import EmptyStateWidget


class JobItemWidget(QFrame):
    """Widget đại diện cho 1 dòng tác vụ trong hàng đợi."""

    def __init__(self, job: Job, bridge: JobQueueBridge, on_move_up=None, on_move_down=None, parent=None):
        super().__init__(parent)
        self.job = job
        self.bridge = bridge
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.setObjectName("JobItemWidget")
        self._setup_ui()
        self.update_data(job)

    def _setup_ui(self):
        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(10, 6, 10, 6)
        main_vbox.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # 0. Nút Đổi thứ tự (Lên / Xuống)
        self.reorder_box = QVBoxLayout()
        self.reorder_box.setSpacing(1)
        self.btn_up = QPushButton("▲")
        self.btn_up.setToolTip("Đẩy lên trên trong hàng đợi")
        self.btn_up.setFixedSize(20, 14)
        self.btn_up.setCursor(Qt.PointingHandCursor)
        self.btn_up.clicked.connect(self._handle_move_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setToolTip("Đẩy xuống dưới trong hàng đợi")
        self.btn_down.setFixedSize(20, 14)
        self.btn_down.setCursor(Qt.PointingHandCursor)
        self.btn_down.clicked.connect(self._handle_move_down)

        self.reorder_box.addWidget(self.btn_up)
        self.reorder_box.addWidget(self.btn_down)
        top_row.addLayout(self.reorder_box)

        # 1. Tên tác vụ và module
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_name = QLabel(self.job.name)
        self.lbl_name.setStyleSheet("font-weight: 600; font-size: 12px;")
        self.lbl_meta = QLabel(f"Module: {self.job.module_id.upper()}")
        self.lbl_meta.setProperty("class", "label-muted")
        title_box.addWidget(self.lbl_name)
        title_box.addWidget(self.lbl_meta)
        top_row.addLayout(title_box, 3)

        # 2. Thanh tiến trình và tốc độ / ETA / Dự tính dung lượng
        progress_box = QVBoxLayout()
        progress_box.setSpacing(2)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setValue(self.job.progress)

        self.lbl_stats = QLabel("Tốc độ: -- | ETA: --")
        self.lbl_stats.setProperty("class", "label-accent")
        self.lbl_stats.setStyleSheet("font-size: 10px;")
        progress_box.addWidget(self.progress_bar)
        progress_box.addWidget(self.lbl_stats)
        top_row.addLayout(progress_box, 4)

        # 3. Huy hiệu trạng thái
        self.lbl_status = QLabel("PENDING")
        self.lbl_status.setProperty("class", "status-badge status-queued")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        top_row.addWidget(self.lbl_status, 1)

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

        self.btn_copy_log = QPushButton("📋 Sao chép log")
        self.btn_copy_log.setProperty("class", "btn-secondary")
        self.btn_copy_log.setToolTip("Sao chép chi tiết log lỗi vào bộ nhớ tạm")
        self.btn_copy_log.setCursor(Qt.PointingHandCursor)
        self.btn_copy_log.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        self.btn_copy_log.clicked.connect(self._copy_log)
        self.btn_copy_log.setVisible(False)

        top_row.addWidget(self.btn_pause)
        top_row.addWidget(self.btn_cancel)
        top_row.addWidget(self.btn_retry)
        top_row.addWidget(self.btn_open)
        top_row.addWidget(self.btn_copy_log)
        main_vbox.addLayout(top_row)

        # Dòng cảnh báo / diễn giải lỗi tiếng Việt (nếu lỗi)
        self.lbl_error = QLabel("")
        self.lbl_error.setProperty("class", "label-danger")
        self.lbl_error.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        main_vbox.addWidget(self.lbl_error)

    def _handle_move_up(self):
        if self.on_move_up:
            self.on_move_up(self.job.id)

    def _handle_move_down(self):
        if self.on_move_down:
            self.on_move_down(self.job.id)

    def _estimate_output_size_str(self) -> str:
        """Ước tính dung lượng file đầu ra dựa trên tiến độ và kích thước file hiện tại."""
        out_p = self.job.output_path or self.job.params.get("output_path", "")
        if out_p and os.path.exists(out_p):
            try:
                cur_sz = os.path.getsize(out_p)
                if self.job.progress > 5 and cur_sz > 0:
                    projected = int(cur_sz / (self.job.progress / 100.0))
                    return f"Dự kiến: ~{format_bytes(projected)}"
                elif cur_sz > 0:
                    return f"Đã ghi: {format_bytes(cur_sz)}"
            except Exception:
                pass
        return ""

    def update_data(self, job: Job):
        self.job = job
        self.lbl_name.setText(job.name)
        self.progress_bar.setValue(job.progress)

        # Thống kê Tốc độ, ETA và Dung lượng ước tính
        est_sz = self._estimate_output_size_str()
        stats_text = f"Tốc độ: {job.speed} | Còn lại: {job.eta}"
        if est_sz:
            stats_text += f" | {est_sz}"
        self.lbl_stats.setText(stats_text)

        status = job.status
        self.lbl_status.setText(status.value)

        status_classes = {
            JobStatus.RUNNING: "status-running",
            JobStatus.PAUSED: "status-paused",
            JobStatus.COMPLETED: "status-success",
            JobStatus.FAILED: "status-failed",
            JobStatus.CANCELLED: "status-cancelled",
            JobStatus.PENDING: "status-queued",
        }
        cls_name = status_classes.get(status, "status-queued")
        self.lbl_status.setProperty("class", f"status-badge {cls_name}")
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

        # Hiển thị nút Up/Down khi job đang PENDING
        is_pending = (status == JobStatus.PENDING)
        self.btn_up.setEnabled(is_pending)
        self.btn_down.setEnabled(is_pending)

        # Xử lý hiển thị thông báo lỗi tiếng Việt
        if status == JobStatus.FAILED:
            vn_err = translate_error(job.error_message, job.module_id)
            self.lbl_error.setText(f"❌ {vn_err}")
            self.lbl_error.setVisible(True)
            self.btn_copy_log.setVisible(True)
        else:
            self.lbl_error.setVisible(False)
            self.btn_copy_log.setVisible(False)

        # Trạng thái các nút thao tác
        if status == JobStatus.RUNNING:
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("⏸️")
            self.btn_cancel.setEnabled(True)
            self.btn_retry.setEnabled(False)
            self.btn_open.setEnabled(False)
        elif status == JobStatus.PAUSED:
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("▶️")
            self.btn_cancel.setEnabled(True)
            self.btn_retry.setEnabled(False)
            self.btn_open.setEnabled(False)
        elif status == JobStatus.COMPLETED:
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_retry.setEnabled(True)
            self.btn_open.setEnabled(bool(job.output_path and os.path.exists(job.output_path)))
        elif status == JobStatus.FAILED:
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_retry.setEnabled(True)
            self.btn_open.setEnabled(False)
        elif status == JobStatus.CANCELLED:
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_retry.setEnabled(True)
            self.btn_open.setEnabled(False)
        else:  # PENDING
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("⏸️")
            self.btn_cancel.setEnabled(True)
            self.btn_retry.setEnabled(False)
            self.btn_open.setEnabled(False)

    def _copy_log(self):
        log_content = (
            f"Tác vụ: {self.job.name}\n"
            f"Module: {self.job.module_id}\n"
            f"Trạng thái: {self.job.status.value}\n"
            f"Lỗi: {self.job.error_message}\n\n"
            f"--- CHI TIẾT NHẬT KÝ (LOGS) ---\n"
            + "\n".join(self.job.logs)
        )
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(log_content)
            QToolTip.showText(self.btn_copy_log.mapToGlobal(QPoint(0, 0)), "Đã sao chép log lỗi vào bộ nhớ tạm!")

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
        self.job_widgets: Dict[str, JobItemWidget] = {}
        self.job_order: List[str] = []
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 8)
        layout.setSpacing(6)

        # Header hàng đợi
        header = QHBoxLayout()
        self.lbl_header = QLabel("⚡ Hàng Đợi Tác Vụ (0 đang chạy, 0 đang chờ)")
        self.lbl_header.setProperty("class", "heading")
        self.lbl_header.setStyleSheet("font-size: 12px;")

        self.btn_clear = QPushButton("Dọn Tác Vụ Xong")
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.setStyleSheet("padding: 2px 10px; font-size: 11px;")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_finished)

        header.addWidget(self.lbl_header)
        header.addStretch()
        header.addWidget(self.btn_clear)
        layout.addLayout(header)

        # Vùng hiển thị Stacked: Empty State vs Danh Sách Job
        self.stack = QStackedWidget()

        self.empty_state = EmptyStateWidget(
            icon="⚡",
            title="Hàng đợi tác vụ đang trống",
            subtitle="Các tác vụ chuyển đổi, cắt, ghép hoặc tải video sẽ xuất hiện ở đây khi bạn bắt đầu",
            action_text=""
        )

        # Vùng cuộn danh sách Job
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.list_container)

        self.stack.addWidget(self.empty_state)
        self.stack.addWidget(self.scroll)
        self.stack.setCurrentIndex(0)

        layout.addWidget(self.stack)

    def _connect_signals(self):
        self.bridge.job_added.connect(self._on_job_added)
        self.bridge.job_updated.connect(self._on_job_updated)
        self.bridge.job_progress.connect(self._on_job_progress)
        self.bridge.job_finished.connect(self._on_job_finished)

    def move_job_up(self, job_id: str):
        """Di chuyển một job lên phía trước trong danh sách."""
        if job_id not in self.job_order:
            return
        idx = self.job_order.index(job_id)
        if idx > 0:
            # Đổi chỗ
            self.job_order[idx], self.job_order[idx - 1] = self.job_order[idx - 1], self.job_order[idx]
            self._rebuild_layout_from_order()
            self.bridge.reorder_jobs(self.job_order)

    def move_job_down(self, job_id: str):
        """Di chuyển một job xuống phía sau trong danh sách."""
        if job_id not in self.job_order:
            return
        idx = self.job_order.index(job_id)
        if idx < len(self.job_order) - 1:
            # Đổi chỗ
            self.job_order[idx], self.job_order[idx + 1] = self.job_order[idx + 1], self.job_order[idx]
            self._rebuild_layout_from_order()
            self.bridge.reorder_jobs(self.job_order)

    def _rebuild_layout_from_order(self):
        """Sắp xếp lại thứ tự widget theo self.job_order."""
        for jid in self.job_order:
            w = self.job_widgets.get(jid)
            if w:
                self.list_layout.removeWidget(w)
        # Chèn lại theo thứ tự
        for idx, jid in enumerate(self.job_order):
            w = self.job_widgets.get(jid)
            if w:
                self.list_layout.insertWidget(idx, w)

    @Slot(object)
    def _on_job_added(self, job: Job):
        if job.id not in self.job_widgets:
            widget = JobItemWidget(
                job,
                self.bridge,
                on_move_up=self.move_job_up,
                on_move_down=self.move_job_down
            )
            self.job_widgets[job.id] = widget
            self.job_order.append(job.id)
            self.list_layout.insertWidget(len(self.job_order) - 1, widget)

        self.stack.setCurrentIndex(1)
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
        """Xóa các widget của job đã hoàn thành hoặc bị hủy và dọn trong DB."""
        jobs = self.bridge.get_all_jobs()
        for j in jobs:
            if j.status in [JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED]:
                widget = self.job_widgets.pop(j.id, None)
                if widget:
                    self.list_layout.removeWidget(widget)
                    widget.deleteLater()
                if j.id in self.job_order:
                    self.job_order.remove(j.id)

        self.bridge.clear_finished_jobs()

        if len(self.job_widgets) == 0:
            self.stack.setCurrentIndex(0)
        self._update_header_stats()
