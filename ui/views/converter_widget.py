"""
Converter Widget Component
Giao diện người dùng của Module 4: Chuyển Đổi & Nén Media:
- Chọn 1 file hoặc Quét cả thư mục (Batch Mode)
- Trích xuất thông số media (Duration, Resolution, Codec, Size)
- Chế độ Remux siêu tốc (-c copy)
- Chế độ Smart Compress CRF (H.264/H.265) kèm GPU Acceleration
- Presets: TikTok, YouTube, Zalo <25MB, Discord <10MB
- Ước tính dung lượng đầu ra thời gian thực
- Đẩy tác vụ vào Job Queue đa luồng
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSlider, QRadioButton, QButtonGroup, QFrame, QFileDialog,
    QMessageBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from core.converter_engine import ConverterEngine
from core.ffmpeg_runner import FFmpegRunner
from core.system import format_bytes, clean_unicode_filename
from core.config import ConfigManager
from core.gpu import GPUDetector
from core.job_queue.job_model import Job


class MediaProbeWorker(QThread):
    """Luồng phụ đọc thông tin ffprobe của các file để không làm đơ giao diện."""
    probe_finished = Signal(list)

    def __init__(self, file_paths: List[str]):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        results = []
        for p in self.file_paths:
            try:
                info = FFmpegRunner.probe(p)
                results.append(info)
            except Exception:
                results.append({
                    "file_path": p,
                    "filename": os.path.basename(p),
                    "filesize": os.path.getsize(p) if os.path.exists(p) else 0,
                    "duration": 0.0,
                    "width": 0,
                    "height": 0,
                    "video_codec": "N/A"
                })
        self.probe_finished.emit(results)


class ConverterWidget(QWidget):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.config_mgr = ConfigManager.get_instance()
        self.selected_files_info: List[Dict[str, Any]] = []
        self.probe_worker: Optional[MediaProbeWorker] = None

        self._setup_ui()
        self._update_estimated_size()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. Header
        header = QHBoxLayout()
        lbl_title = QLabel("🔄 Chuyển Đổi & Nén Media")
        lbl_title.setProperty("class", "heading")
        header.addWidget(lbl_title)
        header.addStretch()
        main_layout.addLayout(header)

        # 2. Card Chọn file / Quét thư mục
        card_input = QFrame()
        card_input.setProperty("class", "card")
        input_layout = QVBoxLayout(card_input)
        input_layout.setSpacing(10)

        # Chế độ chọn file đơn vs Quét thư mục
        mode_row = QHBoxLayout()
        self.rad_single = QRadioButton("Chọn một hoặc nhiều file")
        self.rad_single.setChecked(True)
        self.rad_batch = QRadioButton("Quét toàn bộ thư mục (Batch Mode)")
        
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.rad_single)
        mode_group.addButton(self.rad_batch)

        btn_browse_files = QPushButton("📁 Chọn File...")
        btn_browse_files.setProperty("class", "btn-secondary")
        btn_browse_files.clicked.connect(self._browse_files)

        btn_browse_dir = QPushButton("📂 Quét Thư Mục...")
        btn_browse_dir.setProperty("class", "btn-secondary")
        btn_browse_dir.clicked.connect(self._browse_directory)

        btn_clear_list = QPushButton("🗑️ Xóa Danh Sách")
        btn_clear_list.setProperty("class", "btn-secondary")
        btn_clear_list.clicked.connect(self._clear_files)

        mode_row.addWidget(self.rad_single)
        mode_row.addWidget(self.rad_batch)
        mode_row.addStretch()
        mode_row.addWidget(btn_browse_files)
        mode_row.addWidget(btn_browse_dir)
        mode_row.addWidget(btn_clear_list)
        input_layout.addLayout(mode_row)

        # Bảng danh sách file đã chọn
        self.table_files = QTableWidget(0, 5)
        self.table_files.setHorizontalHeaderLabels(["Tên File", "Dung Lượng", "Thời Lượng", "Độ Phân Giải", "Codec"])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_files.setFixedHeight(110)
        self.table_files.setStyleSheet("""
            QTableWidget { background: #121418; border: 1px solid #2B303C; border-radius: 6px; font-size: 11px; }
            QHeaderView::section { background: #181B20; color: #CBD5E1; padding: 4px; border: none; font-weight: bold; }
        """)
        input_layout.addWidget(self.table_files)

        main_layout.addWidget(card_input)

        # 3. Card Cấu hình chuyển đổi
        card_config = QFrame()
        card_config.setProperty("class", "card")
        cfg_layout = QVBoxLayout(card_config)
        cfg_layout.setSpacing(10)

        # Hàng 1: Định dạng đích & Chế độ chuyển đổi
        row_fmt = QHBoxLayout()
        lbl_fmt = QLabel("Định Dạng Đích:")
        lbl_fmt.setStyleSheet("color: #94A3B8; font-weight: 500;")
        self.cbo_format = QComboBox()
        self.cbo_format.addItems(["MP4", "MOV", "MKV", "AVI", "MP3", "WAV"])
        self.cbo_format.currentIndexChanged.connect(self._on_format_changed)

        lbl_mode = QLabel("Chế Độ Xử Lý:")
        lbl_mode.setStyleSheet("color: #94A3B8; font-weight: 500; margin-left: 16px;")
        self.cbo_mode = QComboBox()
        self.cbo_mode.addItem("Smart Compress (CRF H.264/H.265)", "reencode")
        self.cbo_mode.addItem("Remux Siêu Tốc (-c copy, đổi container trong 1s)", "remux")
        self.cbo_mode.addItem("Preset Tối Ưu Mạng Xã Hội", "preset")
        self.cbo_mode.currentIndexChanged.connect(self._on_mode_changed)

        self.cbo_presets = QComboBox()
        self.cbo_presets.addItem("TikTok / Reels (Dọc / Chuẩn H.264)", "tiktok")
        self.cbo_presets.addItem("YouTube (Full HD 1080p)", "youtube")
        self.cbo_presets.addItem("Zalo / Messenger (Ép < 25MB)", "zalo_25mb")
        self.cbo_presets.addItem("Discord (Ép < 10MB)", "discord_10mb")
        self.cbo_presets.setVisible(False)
        self.cbo_presets.currentIndexChanged.connect(self._update_estimated_size)

        row_fmt.addWidget(lbl_fmt)
        row_fmt.addWidget(self.cbo_format)
        row_fmt.addWidget(lbl_mode)
        row_fmt.addWidget(self.cbo_mode, 1)
        row_fmt.addWidget(self.cbo_presets, 1)
        cfg_layout.addLayout(row_fmt)

        # Hàng 2: Tùy chỉnh Nén (CRF) & Độ phân giải & Tăng tốc GPU
        self.box_custom_opts = QWidget()
        box_custom_layout = QVBoxLayout(self.box_custom_opts)
        box_custom_layout.setContentsMargins(0, 0, 0, 0)
        box_custom_layout.setSpacing(8)

        row_codec = QHBoxLayout()
        lbl_codec = QLabel("Chuẩn Mã Hóa:")
        lbl_codec.setStyleSheet("color: #94A3B8;")
        self.cbo_codec = QComboBox()
        self.cbo_codec.addItem("H.264 (Độ tương thích cao)", "h264")
        self.cbo_codec.addItem("H.265 / HEVC (Nén giảm dung lượng sâu)", "hevc")

        lbl_res = QLabel("Độ Phân Giải:")
        lbl_res.setStyleSheet("color: #94A3B8; margin-left: 16px;")
        self.cbo_res = QComboBox()
        self.cbo_res.addItem("Giữ nguyên gốc (Original)", "original")
        self.cbo_res.addItem("4K Ultra HD (3840x2160)", "4k")
        self.cbo_res.addItem("Full HD (1920x1080)", "1080p")
        self.cbo_res.addItem("HD (1280x720)", "720p")
        self.cbo_res.addItem("SD (854x480)", "480p")
        self.cbo_res.currentIndexChanged.connect(self._update_estimated_size)

        lbl_gpu = QLabel("Tăng Tốc:")
        lbl_gpu.setStyleSheet("color: #94A3B8; margin-left: 16px;")
        self.cbo_gpu = QComboBox()
        self.cbo_gpu.addItem("Tự động (Auto GPU)", "auto")
        self.cbo_gpu.addItem("NVIDIA NVENC", "nvidia")
        self.cbo_gpu.addItem("Intel QSV", "intel")
        self.cbo_gpu.addItem("AMD AMF", "amd")
        self.cbo_gpu.addItem("CPU Software", "cpu")

        row_codec.addWidget(lbl_codec)
        row_codec.addWidget(self.cbo_codec)
        row_codec.addWidget(lbl_res)
        row_codec.addWidget(self.cbo_res)
        row_codec.addWidget(lbl_gpu)
        row_codec.addWidget(self.cbo_gpu)
        row_codec.addStretch()
        box_custom_layout.addLayout(row_codec)

        # Thanh trượt CRF
        row_crf = QHBoxLayout()
        lbl_crf_title = QLabel("Mức Nén (CRF):")
        lbl_crf_title.setStyleSheet("color: #94A3B8;")

        self.slider_crf = QSlider(Qt.Horizontal)
        self.slider_crf.setRange(18, 30)
        self.slider_crf.setValue(23)
        self.slider_crf.valueChanged.connect(self._on_crf_slider_changed)

        self.lbl_crf_val = QLabel("23 (Cân bằng Tốt)")
        self.lbl_crf_val.setStyleSheet("color: #818CF8; font-weight: bold; min-width: 130px;")

        row_crf.addWidget(lbl_crf_title)
        row_crf.addWidget(self.slider_crf, 1)
        row_crf.addWidget(self.lbl_crf_val)
        box_custom_layout.addLayout(row_crf)

        cfg_layout.addWidget(self.box_custom_opts)

        # Hàng hiển thị ước tính dung lượng đầu ra
        self.lbl_estimate = QLabel("📊 Ước tính dung lượng: Chưa có file nào được chọn.")
        self.lbl_estimate.setStyleSheet("font-size: 11px; color: #34D399; font-weight: 600; padding: 4px 0;")
        cfg_layout.addWidget(self.lbl_estimate)

        main_layout.addWidget(card_config)

        # 4. Card Thư mục xuất kết quả & Nút Submit Job
        action_row = QHBoxLayout()
        lbl_out = QLabel("Lưu Tại:")
        lbl_out.setStyleSheet("color: #94A3B8; font-weight: 500;")

        default_dir = self.config_mgr.get("default_output_dir", str(Path.home() / "Downloads"))
        self.txt_out_dir = QLineEdit(default_dir)

        btn_browse_out = QPushButton("📁")
        btn_browse_out.setToolTip("Chọn thư mục lưu")
        btn_browse_out.setProperty("class", "btn-secondary")
        btn_browse_out.clicked.connect(self._browse_output_dir)

        self.btn_submit = QPushButton("🚀 Thêm Vào Hàng Đợi (0 tác vụ)")
        self.btn_submit.setProperty("class", "btn-primary")
        self.btn_submit.setMinimumHeight(38)
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.clicked.connect(self._submit_to_queue)

        action_row.addWidget(lbl_out)
        action_row.addWidget(self.txt_out_dir, 1)
        action_row.addWidget(btn_browse_out)
        action_row.addWidget(self.btn_submit, 1)
        main_layout.addLayout(action_row)

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn File Media", "",
            "Media Files (*.mov *.mp4 *.mkv *.avi *.webm *.mp3 *.wav);;All Files (*.*)"
        )
        if files:
            self._load_files_into_table(files)

    def _browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Chứa Video", "")
        if dir_path:
            scanned = ConverterEngine.scan_directory_for_media(dir_path)
            if not scanned:
                QMessageBox.warning(self, "Thông Báo", f"Không tìm thấy file video/audio nào trong thư mục:\n{dir_path}")
                return
            self._load_files_into_table(scanned)

    def _load_files_into_table(self, file_paths: List[str]):
        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("⏳ Đang phân tích thông tin file...")

        self.probe_worker = MediaProbeWorker(file_paths)
        self.probe_worker.probe_finished.connect(self._on_probe_finished)
        self.probe_worker.start()

    def _on_probe_finished(self, results: List[Dict[str, Any]]):
        self.selected_files_info = results
        self.table_files.setRowCount(len(results))

        for row, info in enumerate(results):
            duration_sec = info.get("duration", 0)
            mins = int(duration_sec // 60)
            secs = int(duration_sec % 60)
            duration_str = f"{mins:02d}:{secs:02d}"

            res_str = f"{info.get('width', 0)}x{info.get('height', 0)}" if info.get('width') else "Audio"

            self.table_files.setItem(row, 0, QTableWidgetItem(info.get("filename", "")))
            self.table_files.setItem(row, 1, QTableWidgetItem(format_bytes(info.get("filesize", 0))))
            self.table_files.setItem(row, 2, QTableWidgetItem(duration_str))
            self.table_files.setItem(row, 3, QTableWidgetItem(res_str))
            self.table_files.setItem(row, 4, QTableWidgetItem(info.get("video_codec") or info.get("audio_codec", "N/A")))

        self.btn_submit.setEnabled(len(results) > 0)
        self.btn_submit.setText(f"🚀 Thêm Vào Hàng Đợi ({len(results)} tác vụ)")
        self._update_estimated_size()

    def _clear_files(self):
        self.selected_files_info.clear()
        self.table_files.setRowCount(0)
        self.btn_submit.setText("🚀 Thêm Vào Hàng Đợi (0 tác vụ)")
        self._update_estimated_size()

    def _on_format_changed(self):
        fmt = self.cbo_format.currentText().lower()
        is_audio = fmt in ["mp3", "wav"]
        self.box_custom_opts.setVisible(not is_audio and self.cbo_mode.currentData() == "reencode")
        self._update_estimated_size()

    def _on_mode_changed(self):
        mode = self.cbo_mode.currentData()
        fmt = self.cbo_format.currentText().lower()
        is_audio = fmt in ["mp3", "wav"]

        self.cbo_presets.setVisible(mode == "preset")
        self.box_custom_opts.setVisible(mode == "reencode" and not is_audio)
        self._update_estimated_size()

    def _on_crf_slider_changed(self, val: int):
        labels = {
            18: "18 (Chất lượng gốc / Cực nét)",
            20: "20 (Rất cao)",
            23: "23 (Cân bằng tốt - Khuyên dùng)",
            26: "26 (Nén cao / Dung lượng nhẹ)",
            28: "28 (Nén rất mạnh / File siêu nhỏ)",
            30: "30 (Tối đa nén)"
        }
        text = labels.get(val, f"{val} (CRF)")
        self.lbl_crf_val.setText(text)
        self._update_estimated_size()

    def _update_estimated_size(self):
        if not self.selected_files_info:
            self.lbl_estimate.setText("📊 Ước tính dung lượng: Chưa có file nào được chọn.")
            return

        total_orig_bytes = sum(f.get("filesize", 0) for f in self.selected_files_info)
        total_duration = sum(f.get("duration", 0) for f in self.selected_files_info)
        mode = self.cbo_mode.currentData()
        fmt = self.cbo_format.currentText().lower()

        if fmt in ["mp3", "wav"]:
            est_total = int(total_duration * (192 * 1000 / 8)) if fmt == "mp3" else int(total_duration * (1411 * 1000 / 8))
        elif mode == "remux":
            est_total = total_orig_bytes
        elif mode == "preset":
            p_name = self.cbo_presets.currentData()
            if p_name == "zalo_25mb":
                est_total = min(total_orig_bytes, len(self.selected_files_info) * 24 * 1024 * 1024)
            elif p_name == "discord_10mb":
                est_total = min(total_orig_bytes, len(self.selected_files_info) * 10 * 1024 * 1024)
            else:
                est_total = int(total_orig_bytes * 0.85)
        else:  # reencode
            crf = self.slider_crf.value()
            res = self.cbo_res.currentData()
            est_total = ConverterEngine.estimate_output_size(
                duration=total_duration,
                crf=crf,
                resolution=res,
                is_remux=False,
                original_size=total_orig_bytes
            )

        reduction = ""
        if total_orig_bytes > 0 and est_total < total_orig_bytes:
            pct = int((1.0 - (est_total / total_orig_bytes)) * 100)
            reduction = f" (Giảm ~{pct}% dung lượng)"

        self.lbl_estimate.setText(f"📊 Dung lượng gốc: {format_bytes(total_orig_bytes)} ➔ Ước tính sau xử lý: ~{format_bytes(est_total)}{reduction}")

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Xuất", self.txt_out_dir.text())
        if folder:
            self.txt_out_dir.setText(folder)

    def _submit_to_queue(self):
        if not self.selected_files_info:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất một file media!")
            return

        out_dir = self.txt_out_dir.text().strip()
        if not out_dir or not os.path.exists(out_dir):
            QMessageBox.warning(self, "Lỗi", "Thư mục lưu không hợp lệ. Vui lòng chọn lại!")
            return

        target_fmt = self.cbo_format.currentText().lower()
        mode = self.cbo_mode.currentData()
        preset_name = self.cbo_presets.currentData()
        codec = self.cbo_codec.currentData()
        crf = self.slider_crf.value()
        resolution = self.cbo_res.currentData()
        gpu_pref = self.cbo_gpu.currentData()

        # Tạo Job cho từng file và đẩy vào Queue
        submitted_count = 0
        for info in self.selected_files_info:
            input_path = info["file_path"]
            orig_name = Path(input_path).stem
            clean_name = clean_unicode_filename(orig_name)
            out_filename = f"{clean_name}.{target_fmt}"
            out_file_path = os.path.join(out_dir, out_filename)

            # Nếu trùng tên file gốc và cùng định dạng, thêm hậu tố
            if os.path.abspath(input_path) == os.path.abspath(out_file_path):
                out_filename = f"{clean_name}_converted.{target_fmt}"
                out_file_path = os.path.join(out_dir, out_filename)

            job = Job(
                module_id="converter",
                name=f"Convert: {info['filename']} ➔ {target_fmt.upper()}",
                output_path=out_file_path,
                params={
                    "input_path": input_path,
                    "output_path": out_file_path,
                    "output_dir": out_dir,
                    "target_format": target_fmt,
                    "mode": mode,
                    "preset_name": preset_name,
                    "codec": codec,
                    "crf": crf,
                    "resolution": resolution,
                    "gpu_pref": gpu_pref,
                    "duration": info.get("duration", 0.0)
                }
            )

            self.bridge.submit_job(job)
            submitted_count += 1

        QMessageBox.information(
            self, "Thành Công",
            f"Đã thêm thành công {submitted_count} tác vụ vào Hàng Đợi (Job Queue)!\nBạn có thể theo dõi tiến độ ở bảng bên dưới."
        )
        self._clear_files()

