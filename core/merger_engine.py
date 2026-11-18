"""
Merger Engine Core Module
Quản lý logic ghép và nối nhiều video thành một video duy nhất:
- Tự động kiểm tra tính tương thích giữa các video đầu vào (độ phân giải, fps, codec, audio).
- Chế độ Ghép nhanh Lossless (-c copy qua Concat Demuxer) khi các video cùng định dạng.
- Chế độ Ghép chuẩn hóa mã hóa lại qua Filter Complex khi video khác kích thước/fps/codec.
- Xử lý tương thích khung hình:
  * Letterbox: Thêm viền đen giữ nguyên tỉ lệ gốc, căn giữa.
  * Crop: Cắt góc phóng to vừa khít khung hình đầu ra.
  * Stretch: Kéo dãn khung hình theo độ phân giải mong muốn.
- Tự động tạo âm thanh im lặng (anullsrc) cho các video không có tiếng để tránh lệch audio.
- Tính năng lồng nhạc nền (Background Music - BGM):
  * Lặp lại nhạc nền khi video dài hơn bài hát (loop BGM).
  * Điều chỉnh âm lượng nhạc nền và âm lượng video gốc (amix filter).
  * Tùy chọn tắt tiếng video gốc (mute original audio).
- Tận dụng tăng tốc phần cứng GPU (NVIDIA NVENC, Intel QSV, AMD AMF) hoặc fallback CPU libx264.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from core.ffmpeg_runner import FFmpegRunner
from core.gpu import GPUDetector
from core.system import clean_unicode_filename
from core.logger import get_logger


class MergerEngine:

    @staticmethod
    def probe_videos(video_paths: List[str]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Phân tích thông số kỹ thuật của danh sách video và tính tổng thời lượng.
        Trả về (danh_sách_metadata, tổng_thời_lượng_giây).
        """
        meta_list = []
        total_duration = 0.0

        for path in video_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Không tìm thấy file: {path}")
            info = FFmpegRunner.probe(path)
            meta_list.append(info)
            total_duration += info.get("duration", 0.0)

        return meta_list, total_duration

    @staticmethod
    def check_compatibility(videos_info: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Kiểm tra xem các video có đủ điều kiện ghép nhanh (-c copy) hay không:
        1. Phải có tối thiểu 2 video.
        2. Không chứa video VP9 (để tránh lỗi vp9_superframe).
        3. Cùng codec video, chiều rộng (width), chiều cao (height).
        4. Cùng FPS (dung sai 0.05).
        5. Cùng có hoặc cùng không có audio; nếu có audio thì phải cùng codec và sample rate.
        """
        if len(videos_info) < 2:
            return False, "Cần tối thiểu 2 video để ghép."

        # Kiểm tra VP9
        for i, info in enumerate(videos_info):
            if info.get("video_codec", "").lower() == "vp9":
                return False, f"Video {i+1} ({info.get('filename')}) dùng codec VP9, cần mã hóa lại để tránh lỗi superframe."

        first = videos_info[0]
        f_vcodec = first.get("video_codec", "")
        f_w = first.get("width", 0)
        f_h = first.get("height", 0)
        f_fps = first.get("fps", 0.0)
        f_has_audio = first.get("has_audio", False)
        f_acodec = first.get("audio_codec", "")
        f_srate = first.get("sample_rate", 0)

        for i, curr in enumerate(videos_info[1:], 2):
            c_name = curr.get("filename", f"Video {i}")

            # Kiểm tra video stream
            if curr.get("video_codec") != f_vcodec:
                return False, f"{c_name} có video codec ({curr.get('video_codec')}) khác video đầu ({f_vcodec})."

            if curr.get("width") != f_w or curr.get("height") != f_h:
                return False, f"{c_name} có độ phân giải ({curr.get('width')}x{curr.get('height')}) khác video đầu ({f_w}x{f_h})."

            if abs(curr.get("fps", 0.0) - f_fps) > 0.05:
                return False, f"{c_name} có tốc độ khung hình ({curr.get('fps')} fps) khác video đầu ({f_fps} fps)."

            # Kiểm tra audio stream
            c_has_audio = curr.get("has_audio", False)
            if c_has_audio != f_has_audio:
                return False, f"{c_name} và video đầu không cùng trạng thái âm thanh (có/không có tiếng)."

            if f_has_audio:
                if curr.get("audio_codec") != f_acodec:
                    return False, f"{c_name} có audio codec ({curr.get('audio_codec')}) khác video đầu ({f_acodec})."
                if curr.get("sample_rate") != f_srate:
                    return False, f"{c_name} có sample rate ({curr.get('sample_rate')} Hz) khác video đầu ({f_srate} Hz)."

        return True, "Các video hoàn toàn tương thích, có thể ghép nhanh siêu tốc (Copy Mode - không mất chất lượng)!"

    @staticmethod
    def write_concat_file(video_paths: List[str], target_txt_path: str) -> str:
        """
        Tạo file danh sách text cho FFmpeg Concat Demuxer.
        Đường dẫn được chuẩn hóa slash '/' và bọc nháy đơn an toàn.
        """
        target_dir = os.path.dirname(target_txt_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        with open(target_txt_path, "w", encoding="utf-8") as f:
            for p in video_paths:
                resolved = str(Path(p).resolve()).replace("\\", "/")
                # Escape dấu nháy đơn nếu tên file có chứa '
                escaped = resolved.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        return target_txt_path

    @staticmethod
    def build_copy_args(concat_txt_path: str, output_path: str) -> List[str]:
        """Tạo đối số FFmpeg cho chế độ concat copy."""
        return [
            "-f", "concat",
            "-safe", "0",
            "-i", concat_txt_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path
        ]

    @staticmethod
    def build_reencode_args(
        videos_info: List[Dict[str, Any]],
        output_path: str,
        target_resolution: Optional[Tuple[int, int]] = None,
        target_fps: Optional[float] = None,
        aspect_ratio_mode: str = "letterbox",
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.3,
        orig_volume: float = 1.0,
        loop_bgm: bool = True,
        use_gpu: bool = True,
        crf: int = 23,
        preset: str = "medium"
    ) -> List[str]:
        """
        Tạo đối số FFmpeg cho chế độ mã hóa lại qua filter_complex:
        - Đồng bộ kích thước chẵn (even width/height)
        - Chuẩn hóa FPS và sample rate
        - Xử lý letterbox/crop/stretch
        - Lồng nhạc nền BGM (nếu có)
        - Tự động dùng GPU encoder nếu khả dụng và người dùng cho phép
        """
        if not videos_info:
            raise ValueError("Không có thông tin video đầu vào.")

        first = videos_info[0]

        # Xác định độ phân giải mục tiêu
        if target_resolution:
            out_w, out_h = target_resolution
        else:
            out_w = first.get("width", 1920) or 1920
            out_h = first.get("height", 1080) or 1080

        # libx264/nvenc yêu cầu kích thước chẵn
        out_w = (out_w // 2) * 2
        out_h = (out_h // 2) * 2

        # Xác định FPS mục tiêu
        if target_fps and target_fps > 0:
            fps_val = target_fps
        else:
            fps_val = first.get("fps", 30.0) or 30.0
            if fps_val <= 0:
                fps_val = 30.0

        n_videos = len(videos_info)

        # Xây dựng danh sách input files
        cmd: List[str] = []
        for info in videos_info:
            cmd.extend(["-i", info["file_path"]])

        has_bgm = bool(bgm_path and os.path.exists(bgm_path))
        bgm_index = n_videos if has_bgm else -1
        if has_bgm:
            if loop_bgm:
                cmd.extend(["-stream_loop", "-1", "-i", bgm_path])
            else:
                cmd.extend(["-i", bgm_path])

        # Xây dựng filter_complex
        filters: List[str] = []
        concat_segments: List[str] = []

        for i, info in enumerate(videos_info):
            # 1. Video stream filter
            v_tag = f"v{i}"
            if aspect_ratio_mode == "crop":
                # Phóng to và crop ở giữa
                scale_filter = (
                    f"[{i}:v:0]scale={out_w}:{out_h}:force_original_aspect_ratio=increase:force_divisible_by=2,"
                    f"crop={out_w}:{out_h},setsar=1,fps={fps_val:.2f},format=yuv420p[{v_tag}]"
                )
            elif aspect_ratio_mode == "stretch":
                # Kéo dãn theo kích thước
                scale_filter = (
                    f"[{i}:v:0]scale={out_w}:{out_h}:force_divisible_by=2,setsar=1,fps={fps_val:.2f},format=yuv420p[{v_tag}]"
                )
            else:
                # Default: letterbox (giữ tỉ lệ gốc, thêm viền đen căn giữa)
                scale_filter = (
                    f"[{i}:v:0]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                    f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={fps_val:.2f},format=yuv420p[{v_tag}]"
                )
            filters.append(scale_filter)

            # 2. Audio stream filter
            a_tag = f"a{i}"
            if info.get("has_audio", False):
                filters.append(f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo[{a_tag}]")
            else:
                # Tạo audio im lặng đúng bằng thời lượng video
                dur = max(0.1, info.get("duration", 1.0))
                filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={dur:.3f}[{a_tag}]")

            concat_segments.append(f"[{v_tag}][{a_tag}]")

        # 3. Nối các đoạn lại với nhau
        concat_in = "".join(concat_segments)
        filters.append(f"{concat_in}concat=n={n_videos}:v=1:a=1[merged_v][merged_a]")

        # 4. Xử lý âm thanh tổng (kết hợp BGM nếu có)
        final_v_label = "[merged_v]"
        if has_bgm:
            bgm_v = max(0.0, min(1.0, bgm_volume))
            orig_v = max(0.0, min(1.0, orig_volume))

            if orig_v <= 0.001:
                # Video gốc bị tắt tiếng: chỉ dùng BGM với âm lượng chọn
                filters.append(f"[{bgm_index}:a:0]volume={bgm_v:.2f},aresample=48000,aformat=channel_layouts=stereo[final_a]")
            else:
                # Trộn audio video gốc với BGM bằng amix
                filters.append(f"[merged_a]volume={orig_v:.2f}[orig_scaled]")
                filters.append(f"[{bgm_index}:a:0]volume={bgm_v:.2f},aresample=48000,aformat=channel_layouts=stereo[bgm_scaled]")
                filters.append(
                    "[orig_scaled][bgm_scaled]amix=inputs=2:duration=first:dropout_transition=2[final_a]"
                )
            final_a_label = "[final_a]"
        else:
            final_a_label = "[merged_a]"

        cmd.extend(["-filter_complex", ";".join(filters)])
        cmd.extend(["-map", final_v_label, "-map", final_a_label])

        # Bộ mã hóa Video (GPU hoặc CPU)
        selected_vcodec = "libx264"
        if use_gpu:
            best_gpu = GPUDetector.get_best_encoder()
            if best_gpu and best_gpu.get("available") and best_gpu.get("codec") == "h264":
                selected_vcodec = best_gpu["encoder"]

        if selected_vcodec == "h264_nvenc":
            cmd.extend(["-c:v", "h264_nvenc", "-cq", str(crf), "-preset", "p4"])
        elif selected_vcodec == "h264_qsv":
            cmd.extend(["-c:v", "h264_qsv", "-global_quality", str(crf), "-preset", "medium"])
        elif selected_vcodec == "h264_amf":
            cmd.extend(["-c:v", "h264_amf", "-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-quality", "balanced"])
        else:
            hw = GPUDetector.get_hardware_profile()
            cpu_preset = hw["recommended_preset"] if preset == "medium" else preset
            cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", cpu_preset])
            if hw.get("recommended_threads", 0) > 0:
                cmd.extend(["-threads", str(hw["recommended_threads"])])
            else:
                cmd.extend(["-threads", "0"])

        # Bộ mã hóa Audio & output settings
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ])

        return cmd

