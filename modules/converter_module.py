"""
Converter Module (Module 4) - Phase 1 Implementation
Chuyển đổi định dạng và Nén media (H.264/H.265 CRF, Remux, GPU Acceleration, Presets).
Kế thừa BaseModule để tự động tích hợp vào Shell và Job Queue.
"""

import os
from typing import Dict, Any, Tuple, Optional
from PySide6.QtWidgets import QWidget
from modules.base_module import BaseModule
from core.converter_engine import ConverterEngine
from core.ffmpeg_runner import FFmpegRunner
from core.job_queue.job_model import Job
from ui.views.converter_widget import ConverterWidget


class ConverterModule(BaseModule):
    @property
    def module_id(self) -> str:
        return "converter"

    @property
    def display_name(self) -> str:
        return "Chuyển Đổi & Nén"

    @property
    def icon(self) -> str:
        return "🔄"

    @property
    def description(self) -> str:
        return "Chuyển đổi MOV, MP4, MKV, AVI, tách nhạc MP3, Smart Compress CRF và Remux siêu tốc."

    def create_widget(self, parent: Optional[QWidget], bridge: Any) -> QWidget:
        return ConverterWidget(bridge, parent)

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        input_path = params.get("input_path")
        if not input_path or not os.path.exists(input_path):
            return False, f"File đầu vào không tồn tại: {input_path}"

        output_path = params.get("output_path")
        if not output_path:
            return False, "Thiếu đường dẫn file đầu ra."

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
        Thực thi chuyển đổi/nén media bằng FFmpegRunner.
        Hàm này chạy hoàn toàn trên worker thread của Job Queue.
        """
        p = job.params
        input_path = p.get("input_path")
        output_path = p.get("output_path")
        target_format = p.get("target_format", "mp4")
        mode = p.get("mode", "reencode")
        preset_name = p.get("preset_name", "custom")
        codec = p.get("codec", "h264")
        crf = p.get("crf", 23)
        resolution = p.get("resolution", "original")
        gpu_pref = p.get("gpu_pref", "auto")
        duration = p.get("duration", 0.0)

        # Lấy lại duration từ ffprobe nếu chưa có
        if duration <= 0:
            try:
                probe_data = FFmpegRunner.probe(input_path)
                duration = probe_data.get("duration", 0.0)
            except Exception:
                pass

        log_callback(f"Bắt đầu chuyển đổi: {os.path.basename(input_path)} ➔ {os.path.basename(output_path)} (Chế độ: {mode})")

        # Xây dựng các tham số FFmpeg
        cmd_args = ConverterEngine.build_conversion_args(
            input_path=input_path,
            output_path=output_path,
            target_format=target_format,
            mode=mode,
            preset_name=preset_name,
            codec=codec,
            crf=crf,
            resolution=resolution,
            gpu_pref=gpu_pref,
            duration=duration
        )

        runner = FFmpegRunner(cmd_args=cmd_args, total_duration=duration, output_path=output_path)
        job._runner_handle = runner

        # Hook log và progress
        success, message = runner.run(
            on_progress=progress_callback,
            on_log=log_callback
        )

        if success:
            log_callback(f"[SUCCESS] Đã lưu file kết quả tại: {output_path}")
            return True, output_path, ""
        else:
            return False, "", message
