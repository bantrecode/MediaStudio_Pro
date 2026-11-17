"""
Cutter Module (Module 2) - Phase 4
Cắt & phân đoạn video:
- Tích hợp CutterWidget trực quan với trình phát video QtMultimedia
- Chế độ Cắt Nhanh Stream Copy (-c copy) siêu tốc
- Chế độ Cắt Chính Xác Re-encode từng khung hình kèm tăng tốc GPU
- Hỗ trợ cắt hàng loạt theo kịch bản Auto-Split cho Shorts/Reels/TikTok
"""

import os
from typing import Dict, Any, Tuple, Optional
from PySide6.QtWidgets import QWidget
from modules.base_module import BaseModule
from core.job_queue.job_model import Job
from core.cutter_engine import CutterEngine
from core.ffmpeg_runner import FFmpegRunner
from core.logger import get_logger
from ui.views.cutter_widget import CutterWidget


class CutterModule(BaseModule):
    @property
    def module_id(self) -> str:
        return "cutter"

    @property
    def display_name(self) -> str:
        return "Cắt Video Nhanh"

    @property
    def icon(self) -> str:
        return "✂️"

    @property
    def description(self) -> str:
        return "Cắt video trực quan với trình phát preview, stream copy siêu tốc và auto-split cho Reels/Shorts."

    def create_widget(self, parent: Optional[QWidget], bridge: Any) -> QWidget:
        return CutterWidget(bridge=bridge, parent=parent)

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        input_path = params.get("input_path")
        if not input_path or not os.path.exists(input_path):
            return False, "File video đầu vào không tồn tại hoặc không hợp lệ."

        output_path = params.get("output_path")
        if not output_path:
            return False, "Đường dẫn file đầu ra không được để trống."

        start_time = params.get("start_time", 0.0)
        end_time = params.get("end_time", 0.0)
        if end_time <= start_time:
            return False, "Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu."

        return True, ""

    def execute_job(
        self,
        job: Job,
        progress_callback: Any,
        log_callback: Any,
        cancel_event: Any,
        pause_event: Any
    ) -> Tuple[bool, str, str]:
        """
        Thực thi cắt video bằng FFmpegRunner trên worker thread của Job Queue.
        """
        logger = get_logger()
        p = job.params
        input_path = p.get("input_path")
        output_path = p.get("output_path")
        start_time = float(p.get("start_time", 0.0))
        end_time = float(p.get("end_time", 0.0))
        mode = p.get("mode", "copy")
        use_gpu = p.get("use_gpu", True)
        crf = p.get("crf", 23)

        duration = max(0.1, end_time - start_time)
        s_str = CutterEngine.format_seconds_to_time(start_time, include_ms=True)
        e_str = CutterEngine.format_seconds_to_time(end_time, include_ms=True)

        log_callback(f"Bắt đầu cắt: {os.path.basename(input_path)} từ [{s_str}] đến [{e_str}] (Thời lượng: ~{duration:.2f}s, Chế độ: {mode.upper()})")

        # Xây dựng lệnh FFmpeg
        if mode == "copy":
            cmd_args = CutterEngine.build_cut_copy_args(
                input_path=input_path,
                output_path=output_path,
                start_time=start_time,
                end_time=end_time
            )
        else:
            cmd_args = CutterEngine.build_cut_reencode_args(
                input_path=input_path,
                output_path=output_path,
                start_time=start_time,
                end_time=end_time,
                use_gpu=use_gpu,
                crf=crf,
                preset="medium"
            )

        runner = FFmpegRunner(cmd_args=cmd_args, total_duration=duration, output_path=output_path)
        job._runner_handle = runner

        success, message = runner.run(on_progress=progress_callback, on_log=log_callback)

        # Fallback nếu GPU encoder bị lỗi
        if not success and not runner.is_cancelled and mode == "reencode" and use_gpu:
            log_callback(f"Mã hóa GPU bị lỗi ({message}). Đang tự động chuyển sang CPU libx264...")
            cmd_args_cpu = CutterEngine.build_cut_reencode_args(
                input_path=input_path,
                output_path=output_path,
                start_time=start_time,
                end_time=end_time,
                use_gpu=False,
                crf=crf,
                preset="medium"
            )
            runner = FFmpegRunner(cmd_args=cmd_args_cpu, total_duration=duration, output_path=output_path)
            job._runner_handle = runner
            success, message = runner.run(on_progress=progress_callback, on_log=log_callback)

        if success:
            log_callback(f"[SUCCESS] Đã cắt thành công: {output_path}")
            return True, output_path, ""
        else:
            return False, "", message
