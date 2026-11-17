"""
Merger Module (Module 3) - Phase 3
Ghép và nối video:
- Tích hợp MergerWidget vào giao diện chính
- Thực thi tác vụ ghép video chạy ngầm trong Job Queue
- Hỗ trợ cả 2 chế độ: Ghép nhanh Lossless Copy và Ghép chuẩn hóa Re-encode
- Tự động fallback sang Re-encode nếu Copy Mode bị lỗi định dạng
- Tự động fallback CPU nếu GPU encoder bị lỗi
- Hỗ trợ lồng nhạc nền và kiểm soát âm lượng đa nguồn
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PySide6.QtWidgets import QWidget
from modules.base_module import BaseModule
from core.job_queue.job_model import Job
from core.merger_engine import MergerEngine
from core.ffmpeg_runner import FFmpegRunner
from core.system import get_cache_dir
from core.logger import get_logger
from ui.views.merger_widget import MergerWidget


class MergerModule(BaseModule):
    @property
    def module_id(self) -> str:
        return "merger"

    @property
    def display_name(self) -> str:
        return "Ghép & Nối Video"

    @property
    def icon(self) -> str:
        return "🔗"

    @property
    def description(self) -> str:
        return "Ghép nhiều video theo thứ tự, tự động tương thích kích thước và FPS, hỗ trợ lồng nhạc nền đa kênh."

    def create_widget(self, parent: Optional[QWidget], bridge: Any) -> QWidget:
        return MergerWidget(bridge=bridge, parent=parent)

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        video_paths = params.get("video_paths", [])
        if not video_paths or len(video_paths) < 2:
            return False, "Cần tối thiểu 2 video để thực hiện ghép nối."

        output_path = params.get("output_path", "")
        if not output_path:
            return False, "Đường dẫn file đầu ra không được để trống."

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
        Thực thi ghép video bằng FFmpegRunner trên worker thread của Job Queue.
        """
        logger = get_logger()
        p = job.params
        video_paths = p.get("video_paths", [])
        videos_info = p.get("videos_info", [])
        output_path = p.get("output_path")
        mode = p.get("mode", "auto")
        target_res = p.get("target_resolution")
        target_fps = p.get("target_fps", 0.0)
        aspect_mode = p.get("aspect_ratio_mode", "letterbox")
        use_gpu = p.get("use_gpu", True)
        crf = p.get("crf", 23)
        bgm_path = p.get("bgm_path")
        bgm_volume = p.get("bgm_volume", 0.3)
        orig_volume = p.get("orig_volume", 1.0)
        loop_bgm = p.get("loop_bgm", True)
        total_duration = p.get("total_duration", 0.0)

        # Đảm bảo có metadata đầy đủ
        if not videos_info or len(videos_info) != len(video_paths):
            try:
                videos_info, dur = MergerEngine.probe_videos(video_paths)
                if total_duration <= 0:
                    total_duration = dur
            except Exception as e:
                return False, "", f"Lỗi khi đọc metadata video: {e}"

        log_callback(f"Bắt đầu ghép {len(video_paths)} video. Chế độ dự kiến: {mode.upper()}")

        # ==========================================
        # 1. Chế độ Ghép Nhanh (Copy Mode)
        # ==========================================
        if mode == "copy":
            cache_dir = get_cache_dir()
            concat_txt = os.path.join(cache_dir, f"concat_{job.id}.txt")

            try:
                MergerEngine.write_concat_file(video_paths, concat_txt)
                log_callback(f"Đã tạo file danh sách concat tạm: {concat_txt}")

                cmd_args = MergerEngine.build_copy_args(concat_txt, output_path)
                runner = FFmpegRunner(cmd_args=cmd_args, total_duration=total_duration, output_path=output_path)
                job._runner_handle = runner

                log_callback("Đang thực hiện ghép nhanh siêu tốc (-c copy)...")
                success, message = runner.run(on_progress=progress_callback, on_log=log_callback)

                # Dọn file danh sách tạm
                if os.path.exists(concat_txt):
                    try:
                        os.remove(concat_txt)
                    except Exception:
                        pass

                if success:
                    log_callback(f"[SUCCESS] Ghép nhanh thành công: {output_path}")
                    return True, output_path, ""

                # Nếu lỗi không phải do hủy và người dùng chọn chế độ tự động, thử fallback re-encode
                if not runner.is_cancelled:
                    log_callback(f"Ghép nhanh thất bại ({message}). Tự động chuyển sang chế độ Ghép Chuẩn Hóa (Mã hóa lại)...")
                    mode = "reencode"
                else:
                    return False, "", "Tác vụ đã bị hủy bởi người dùng."

            except Exception as e:
                log_callback(f"Lỗi ghép nhanh: {e}. Đang thử mã hóa lại...")
                mode = "reencode"

        # ==========================================
        # 2. Chế độ Ghép Chuẩn Hóa (Re-encode Mode)
        # ==========================================
        if mode == "reencode":
            log_callback("Đang tạo đồ thị bộ lọc filter_complex để đồng bộ kích thước, FPS và âm thanh...")

            cmd_args = MergerEngine.build_reencode_args(
                videos_info=videos_info,
                output_path=output_path,
                target_resolution=target_res,
                target_fps=target_fps,
                aspect_ratio_mode=aspect_mode,
                bgm_path=bgm_path,
                bgm_volume=bgm_volume,
                orig_volume=orig_volume,
                loop_bgm=loop_bgm,
                use_gpu=use_gpu,
                crf=crf,
                preset="medium"
            )

            runner = FFmpegRunner(cmd_args=cmd_args, total_duration=total_duration, output_path=output_path)
            job._runner_handle = runner

            success, message = runner.run(on_progress=progress_callback, on_log=log_callback)

            # Fallback nếu GPU thất bại
            if not success and not runner.is_cancelled and use_gpu:
                log_callback(f"Lỗi mã hóa GPU ({message}). Đang tự động chuyển sang mã hóa CPU (libx264)...")
                cmd_args_cpu = MergerEngine.build_reencode_args(
                    videos_info=videos_info,
                    output_path=output_path,
                    target_resolution=target_res,
                    target_fps=target_fps,
                    aspect_ratio_mode=aspect_mode,
                    bgm_path=bgm_path,
                    bgm_volume=bgm_volume,
                    orig_volume=orig_volume,
                    loop_bgm=loop_bgm,
                    use_gpu=False,
                    crf=crf,
                    preset="medium"
                )
                runner = FFmpegRunner(cmd_args=cmd_args_cpu, total_duration=total_duration, output_path=output_path)
                job._runner_handle = runner
                success, message = runner.run(on_progress=progress_callback, on_log=log_callback)

            if success:
                log_callback(f"[SUCCESS] Ghép chuẩn hóa thành công: {output_path}")
                return True, output_path, ""
            else:
                return False, "", message

        return False, "", "Không xác định được phương thức ghép hợp lệ."
