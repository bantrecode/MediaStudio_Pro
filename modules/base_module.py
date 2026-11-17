"""
Base Module Interface
Định nghĩa giao diện trừu tượng BaseModule cho mọi công cụ trong MediaStudio.
Mỗi module mới kế thừa lớp này để tự đăng ký vào Sidebar, Workspace và Job Queue
mà KHÔNG cần sửa đổi một dòng code nào của Shell giao diện.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from PySide6.QtWidgets import QWidget
from core.job_queue.job_model import Job


class BaseModule(ABC):

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Mã định danh duy nhất của module (vd: 'converter', 'downloader', 'merger', 'cutter')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Tên hiển thị trên thanh Sidebar và tiêu đề (vd: 'Chuyển Đổi & Nén')."""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Biểu tượng hiển thị (vd: '🔄', '📥', '🔗', '✂️')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Mô tả ngắn gọn về chức năng của module."""
        pass

    @abstractmethod
    def create_widget(self, parent: Optional[QWidget], bridge: Any) -> QWidget:
        """
        Khởi tạo và trả về QWidget giao diện thao tác của module.
        bridge: Đối tượng JobQueueBridge để gửi job và nhận tín hiệu.
        """
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của tham số trước khi đưa vào hàng đợi Job Queue.
        Trả về: (is_valid: bool, error_message: str)
        """
        pass

    @abstractmethod
    def execute_job(
        self,
        job: Job,
        progress_callback: Any,
        log_callback: Any,
        cancel_event: Any,
        pause_event: Any
    ) -> Tuple[bool, str, str]:
        """
        Logic thực thi cốt lõi của tác vụ (chạy trên thread của Job Queue).
        Hàm này là thuần logic, KHÔNG chứa code cập nhật GUI trực tiếp.
        Trả về: (success: bool, output_path: str, error_message: str)
        """
        pass

