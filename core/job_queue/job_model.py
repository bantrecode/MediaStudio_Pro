"""
Job Model Module
Định nghĩa cấu trúc dữ liệu cho một tác vụ trong hàng đợi (Job Queue).
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


class JobStatus(str, Enum):
    PENDING = "PENDING"        # Đang chờ trong hàng đợi
    RUNNING = "RUNNING"        # Đang thực thi
    PAUSED = "PAUSED"          # Tạm dừng
    COMPLETED = "COMPLETED"    # Hoàn thành thành công
    FAILED = "FAILED"          # Thất bại (có lỗi)
    CANCELLED = "CANCELLED"    # Người dùng hủy


@dataclass
class Job:
    module_id: str
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    progress: int = 0          # 0 - 100%
    speed: str = "--"
    eta: str = "--:--"
    error_message: str = ""
    output_path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""
    logs: List[str] = field(default_factory=list)

    # Đối tượng nội bộ để điều khiển tác vụ (runner_instance, cancel_flag, thread,...)
    _cancel_event: Any = None
    _pause_event: Any = None
    _runner_handle: Any = None

    def append_log(self, text: str):
        now = datetime.now().strftime("%H:%M:%S")
        line = f"[{now}] {text}"
        self.logs.append(line)
        # Giữ tối đa 500 dòng log cho mỗi job để tiết kiệm RAM
        if len(self.logs) > 500:
            self.logs.pop(0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "module_id": self.module_id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "error_message": self.error_message,
            "output_path": self.output_path,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "params": self.params,
        }

