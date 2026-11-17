"""
Merger Widget Component (Phase 3)
Giao diện người dùng của Module 3: Ghép & Nối Video:
- Kéo thả sắp xếp danh sách video linh hoạt (Lên/Xuống/Xóa/Xóa Hết).
- Phân tích tương thích tự động qua ffprobe ngầm (QThread không đơ UI).
- Cảnh báo trực quan: Nhận diện ghép nhanh (Copy Mode) vs Ghép chuẩn hóa (Re-encode).
- Tùy chọn xử lý tỉ lệ khung hình: Letterbox (viền đen), Crop (lấp đầy), Stretch (kéo dãn).
- Hỗ trợ preset chuẩn: 1080p, 720p, 4K, TikTok/Shorts 9:16 dọc.
- Tùy chọn lồng nhạc nền (BGM) đa năng: điều chỉnh âm lượng video gốc và nhạc nền, loop BGM, mute gốc.
- Đẩy tác vụ vào Hàng đợi (Job Queue).
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSlider, QCheckBox, QFrame, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QScrollArea
)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from core.merger_engine import MergerEngine
from core.ffmpeg_runner import FFmpegRunner
from core.system import format_bytes, clean_unicode_filename
from core.config import ConfigManager
from core.gpu import GPUDetector
from core.job_queue.job_model import Job


class MergerProbeWorker(QThread):
    """Luồng phụ đọc thông số video bằng ffprobe để không đơ giao diện."""
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
                    "fps": 0.0,
                    "video_codec": "N/A",
                    "has_audio": False,
                    "audio_codec": "N/A",
                    "sample_rate": 0
                })
        self.probe_finished.emit(results)


class MergerWidget(QWidget):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.config_mgr = ConfigManager.get_instance()
        self.video_list: List[Dict[str, Any]] = []
        self.probe_worker: Optional[MergerProbeWorker] = None

        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Scroll Area bao bọc toàn bộ nội dung
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(14)

        # 1. Header
        header = QHBoxLayout()
        lbl_title = QLabel("🔗 Ghép & Nối Video (Video Merger)")
        lbl_title.setProperty("class", "heading")
        header.addWidget(lbl_title)
        header.addStretch()
        container_layout.addLayout(header)

        # 2. Card Danh sách video
        card_list = QFrame()
        card_list.setProperty("class", "card")
        list_layout = QVBoxLayout(card_list)
        list_layout.setSpacing(10)

        # Toolbar các nút thao tác
        tb_layout = QHBoxLayout()
        btn_add_files = QPushButton("📁 Thêm Video...")
        btn_add_files.setProperty("class", "btn-secondary")
        btn_add_files.clicked.connect(self._add_files)

        btn_add_folder = QPushButton("📂 Thêm Thư Mục...")
        btn_add_folder.setProperty("class", "btn-secondary")
        btn_add_folder.clicked.connect(self._add_folder)

        btn_up = QPushButton("⬆️ Lên Trên")
        btn_up.setProperty("class", "btn-secondary")
        btn_up.clicked.connect(self._move_up)

        btn_down = QPushButton("⬇️ Xuống Dưới")
        btn_down.setProperty("class", "btn-secondary")
        btn_down.clicked.connect(self._move_down)

        btn_remove = QPushButton("🗑️ Xóa")
        btn_remove.setProperty("class", "btn-secondary")
        btn_remove.clicked.connect(self._remove_selected)

        btn_clear = QPushButton("🧹 Xóa Hết")
        btn_clear.setProperty("class", "btn-secondary")
        btn_clear.clicked.connect(self._clear_all)

        tb_layout.addWidget(btn_add_files)
        tb_layout.addWidget(btn_add_folder)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(btn_up)
        tb_layout.addWidget(btn_down)
        tb_layout.addWidget(btn_remove)
        tb_layout.addWidget(btn_clear)
        tb_layout.addStretch()
        list_layout.addLayout(tb_layout)

        # Bảng danh sách video
        self.table_videos = QTableWidget(0, 7)
        self.table_videos.setHorizontalHeaderLabels([
            "#", "Tên Video", "Thời Lượng", "Độ Phân Giải", "FPS", "Codec", "Âm Thanh"
        ])
        self.table_videos.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_videos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_videos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_videos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_videos.setMinimumHeight(180)
        self.table_videos.setMaximumHeight(260)
        list_layout.addWidget(self.table_videos)

        # Banner trạng thái tương thích
        self.lbl_compat_status = QLabel("💡 Kéo thả hoặc bấm 'Thêm Video' để bắt đầu. Cần tối thiểu 2 video để ghép.")
        self.lbl_compat_status.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 4px 0;")
        self.lbl_compat_status.setWordWrap(True)
        list_layout.addWidget(self.lbl_compat_status)

        container_layout.addWidget(card_list)

        # 3. Card Cài đặt ghép video
        card_settings = QFrame()
        card_settings.setProperty("class", "card")
        set_layout = QVBoxLayout(card_settings)
        set_layout.setSpacing(12)

        lbl_set_title = QLabel("⚙️ Cấu Hình Ghép & Tương Thích")
        lbl_set_title.setProperty("class", "subheading")
        set_layout.addWidget(lbl_set_title)

        grid1 = QHBoxLayout()
        grid1.setSpacing(16)

        # Chế độ ghép
        vbox_mode = QVBoxLayout()
        vbox_mode.addWidget(QLabel("Chế độ ghép:"))
        self.cbo_merge_mode = QComboBox()
        self.cbo_merge_mode.addItem("⚡ Tự động (Ưu tiên Ghép Nhanh nếu tương thích)", "auto")
        self.cbo_merge_mode.addItem("🚀 Bắt buộc Ghép Nhanh (Lossless Copy)", "force_copy")
        self.cbo_merge_mode.addItem("🔄 Luôn Mã Hóa Lại (Chuẩn hóa toàn bộ)", "force_reencode")
        self.cbo_merge_mode.currentIndexChanged.connect(self._on_settings_changed)
        vbox_mode.addWidget(self.cbo_merge_mode)
        grid1.addLayout(vbox_mode)

        # Tỉ lệ khung hình (Aspect Ratio)
        vbox_aspect = QVBoxLayout()
        vbox_aspect.addWidget(QLabel("Xử lý kích thước khác nhau:"))
        self.cbo_aspect = QComboBox()
        self.cbo_aspect.addItem("⬛ Letterbox (Viền đen, giữ trọn khung)", "letterbox")
        self.cbo_aspect.addItem("🔍 Crop (Phóng to cắt cạnh, lấp đầy khung)", "crop")
        self.cbo_aspect.addItem("↔️ Stretch (Kéo dãn toàn màn hình)", "stretch")
        vbox_aspect.addWidget(self.cbo_aspect)
        grid1.addLayout(vbox_aspect)

        set_layout.addLayout(grid1)

        grid2 = QHBoxLayout()
        grid2.setSpacing(16)

        # Độ phân giải xuất
        vbox_res = QVBoxLayout()
        vbox_res.addWidget(QLabel("Độ phân giải đầu ra:"))
        self.cbo_res = QComboBox()
        self.cbo_res.addItem("Gốc (Theo video đầu tiên)", "first")
        self.cbo_res.addItem("1080p Full HD (1920x1080)", "1920x1080")
        self.cbo_res.addItem("720p HD (1280x720)", "1280x720")
        self.cbo_res.addItem("4K Ultra HD (3840x2160)", "3840x2160")
        self.cbo_res.addItem("TikTok / Shorts 9:16 (1080x1920)", "1080x1920")
        vbox_res.addWidget(self.cbo_res)
        grid2.addLayout(vbox_res)

        # Tốc độ khung hình (FPS)
        vbox_fps = QVBoxLayout()
        vbox_fps.addWidget(QLabel("Tốc độ khung hình (FPS):"))
        self.cbo_fps = QComboBox()
        self.cbo_fps.addItem("Tự động (Theo video đầu tiên)", 0.0)
        self.cbo_fps.addItem("30 FPS", 30.0)
        self.cbo_fps.addItem("60 FPS", 60.0)
        self.cbo_fps.addItem("24 FPS (Phim ảnh)", 24.0)
        vbox_fps.addWidget(self.cbo_fps)
        grid2.addLayout(vbox_fps)

        # Tăng tốc GPU
        vbox_gpu = QVBoxLayout()
        vbox_gpu.addWidget(QLabel("Bộ mã hóa (GPU/CPU):"))
        self.cbo_gpu = QComboBox()
        best_gpu = GPUDetector.get_best_encoder()
        gpu_name = best_gpu.get("name", "Không có GPU rời") if best_gpu else "Không có GPU rời"
        self.cbo_gpu.addItem(f"⚡ GPU: {gpu_name}", True)
        self.cbo_gpu.addItem("💻 Chỉ dùng CPU (libx264)", False)
        vbox_gpu.addWidget(self.cbo_gpu)
        grid2.addLayout(vbox_gpu)

        set_layout.addLayout(grid2)

        # Slider CRF
        crf_row = QHBoxLayout()
        self.lbl_crf_val = QLabel("Chất lượng mã hóa (CRF): 23 (Cân bằng tốt)")
        self.slider_crf = QSlider(Qt.Horizontal)
        self.slider_crf.setRange(18, 30)
        self.slider_crf.setValue(23)
        self.slider_crf.valueChanged.connect(self._on_crf_changed)
        crf_row.addWidget(self.lbl_crf_val)
        crf_row.addWidget(self.slider_crf)
        set_layout.addLayout(crf_row)

        container_layout.addWidget(card_settings)

        # 4. Card Nhạc Nền (BGM Overlay)
        card_bgm = QFrame()
        card_bgm.setProperty("class", "card")
        bgm_layout = QVBoxLayout(card_bgm)
        bgm_layout.setSpacing(10)

        self.chk_enable_bgm = QCheckBox("🎵 Lồng Nhạc Nền (Background Music - BGM)")
        self.chk_enable_bgm.setStyleSheet("font-weight: 600; font-size: 14px; color: #38BDF8;")
        self.chk_enable_bgm.toggled.connect(self._toggle_bgm_controls)
        bgm_layout.addWidget(self.chk_enable_bgm)

        # Widget chứa các điều khiển BGM
        self.bgm_controls = QWidget()
        bgm_ctrl_layout = QVBoxLayout(self.bgm_controls)
        bgm_ctrl_layout.setContentsMargins(0, 0, 0, 0)
        bgm_ctrl_layout.setSpacing(10)

        # Dòng chọn file Audio
        bgm_file_row = QHBoxLayout()
        self.txt_bgm_file = QLineEdit()
        self.txt_bgm_file.setPlaceholderText("Chọn file âm thanh nhạc nền (MP3, WAV, M4A, AAC)...")
        btn_browse_bgm = QPushButton("📁 Chọn Nhạc...")
        btn_browse_bgm.setProperty("class", "btn-secondary")
        btn_browse_bgm.clicked.connect(self._browse_bgm_file)
        bgm_file_row.addWidget(self.txt_bgm_file)
        bgm_file_row.addWidget(btn_browse_bgm)
        bgm_ctrl_layout.addLayout(bgm_file_row)

        # Âm lượng BGM & Video gốc
        vol_row = QHBoxLayout()
        vol_row.setSpacing(16)

        # BGM Volume
        vbox_bgm_vol = QVBoxLayout()
        self.lbl_bgm_vol = QLabel("Âm lượng nhạc nền: 30%")
        self.slider_bgm_vol = QSlider(Qt.Horizontal)
        self.slider_bgm_vol.setRange(0, 100)
        self.slider_bgm_vol.setValue(30)
        self.slider_bgm_vol.valueChanged.connect(lambda v: self.lbl_bgm_vol.setText(f"Âm lượng nhạc nền: {v}%"))
        vbox_bgm_vol.addWidget(self.lbl_bgm_vol)
        vbox_bgm_vol.addWidget(self.slider_bgm_vol)
        vol_row.addLayout(vbox_bgm_vol)

        # Original Video Volume
        vbox_orig_vol = QVBoxLayout()
        self.lbl_orig_vol = QLabel("Âm lượng video gốc: 100%")
        self.slider_orig_vol = QSlider(Qt.Horizontal)
        self.slider_orig_vol.setRange(0, 100)
        self.slider_orig_vol.setValue(100)
        self.slider_orig_vol.valueChanged.connect(lambda v: self.lbl_orig_vol.setText(f"Âm lượng video gốc: {v}%"))
        vbox_orig_vol.addWidget(self.lbl_orig_vol)
        vbox_orig_vol.addWidget(self.slider_orig_vol)
        vol_row.addLayout(vbox_orig_vol)

        bgm_ctrl_layout.addLayout(vol_row)

        # Checkboxes cho BGM
        chk_row = QHBoxLayout()
        self.chk_mute_orig = QCheckBox("Tắt hẳn âm thanh video gốc (Chỉ giữ nhạc nền)")
        self.chk_mute_orig.toggled.connect(self._on_mute_orig_toggled)
        self.chk_loop_bgm = QCheckBox("Lặp lại nhạc nền nếu video dài hơn bài hát (Loop BGM)")
        self.chk_loop_bgm.setChecked(True)
        chk_row.addWidget(self.chk_mute_orig)
        chk_row.addWidget(self.chk_loop_bgm)
        chk_row.addStretch()
        bgm_ctrl_layout.addLayout(chk_row)

        bgm_layout.addWidget(self.bgm_controls)
        self.bgm_controls.setVisible(False)  # Ẩn mặc định khi chưa bật checkbox

        container_layout.addWidget(card_bgm)

        # 5. Card Thư mục xuất & Nút Bắt đầu
        card_out = QFrame()
        card_out.setProperty("class", "card")
        out_layout = QVBoxLayout(card_out)
        out_layout.setSpacing(10)

        out_row = QHBoxLayout()
        lbl_out = QLabel("Lưu file vào:")
        self.txt_out_dir = QLineEdit()
        default_dir = self.config_mgr.get("download_dir", str(Path.home() / "Downloads"))
        self.txt_out_dir.setText(default_dir)

        btn_browse_out = QPushButton("📁 Chọn Thư Mục...")
        btn_browse_out.setProperty("class", "btn-secondary")
        btn_browse_out.clicked.connect(self._browse_output_dir)

        out_row.addWidget(lbl_out)
        out_row.addWidget(self.txt_out_dir)
        out_row.addWidget(btn_browse_out)
        out_layout.addLayout(out_row)

        name_row = QHBoxLayout()
        lbl_name = QLabel("Tên file sau khi ghép:")
        self.txt_out_name = QLineEdit("merged_output.mp4")
        name_row.addWidget(lbl_name)
        name_row.addWidget(self.txt_out_name)
        out_layout.addLayout(name_row)

        self.btn_submit = QPushButton("🚀 Bắt Đầu Ghép Video (Thêm vào Hàng Đợi)")
        self.btn_submit.setProperty("class", "btn-primary")
        self.btn_submit.setMinimumHeight(44)
        self.btn_submit.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.btn_submit.clicked.connect(self._submit_to_queue)
        out_layout.addWidget(self.btn_submit)

        container_layout.addWidget(card_out)
        container_layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # ==========================
    # Drag & Drop Events
    # ==========================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isfile(p):
                ext = Path(p).suffix.lower()
                if ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".ts", ".m4v"}:
                    paths.append(p)
            elif os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in files:
                        ext = Path(f).suffix.lower()
                        if ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".ts", ".m4v"}:
                            paths.append(os.path.join(root, f))

        if paths:
            self._queue_probe_files(paths)

    # ==========================
    # File Management
    # ==========================
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn Video Cần Ghép", "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.ts *.m4v);;All Files (*.*)"
        )
        if files:
            self._queue_probe_files(files)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Chứa Video", "")
        if folder:
            paths = []
            for root, _, files in os.walk(folder):
                for f in sorted(files):
                    ext = Path(f).suffix.lower()
                    if ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".ts", ".m4v"}:
                        paths.append(os.path.join(root, f))
            if paths:
                self._queue_probe_files(paths)

    def _queue_probe_files(self, paths: List[str]):
        # Loại bỏ các file trùng đường dẫn đã có trong danh sách
        existing_paths = {v["file_path"] for v in self.video_list}
        new_paths = [p for p in paths if p not in existing_paths]

        if not new_paths:
            return

        self.lbl_compat_status.setText("⏳ Đang phân tích thông số kỹ thuật của video bằng ffprobe...")
        self.probe_worker = MergerProbeWorker(new_paths)
        self.probe_worker.probe_finished.connect(self._on_probe_finished)
        self.probe_worker.start()

    @Slot(list)
    def _on_probe_finished(self, new_infos: List[Dict[str, Any]]):
        self.video_list.extend(new_infos)
        self._refresh_table()
        self._check_and_update_compatibility()

    def _refresh_table(self):
        self.table_videos.setRowCount(len(self.video_list))
        for row, info in enumerate(self.video_list):
            item_idx = QTableWidgetItem(str(row + 1))
            item_idx.setTextAlignment(Qt.AlignCenter)

            item_name = QTableWidgetItem(info.get("filename", ""))
            item_name.setToolTip(info.get("file_path", ""))

            dur = info.get("duration", 0.0)
            mins, secs = divmod(int(dur), 60)
            item_dur = QTableWidgetItem(f"{mins:02d}:{secs:02d}")
            item_dur.setTextAlignment(Qt.AlignCenter)

            res = f"{info.get('width', 0)}x{info.get('height', 0)}"
            item_res = QTableWidgetItem(res)
            item_res.setTextAlignment(Qt.AlignCenter)

            fps = info.get("fps", 0.0)
            item_fps = QTableWidgetItem(f"{fps:.1f} fps" if fps > 0 else "N/A")
            item_fps.setTextAlignment(Qt.AlignCenter)

            item_vcodec = QTableWidgetItem(info.get("video_codec", "N/A").upper())
            item_vcodec.setTextAlignment(Qt.AlignCenter)

            audio_str = f"{info.get('audio_codec', '').upper()} ({info.get('sample_rate', 0)}Hz)" if info.get("has_audio") else "Không có tiếng"
            item_audio = QTableWidgetItem(audio_str)
            item_audio.setTextAlignment(Qt.AlignCenter)

            self.table_videos.setItem(row, 0, item_idx)
            self.table_videos.setItem(row, 1, item_name)
            self.table_videos.setItem(row, 2, item_dur)
            self.table_videos.setItem(row, 3, item_res)
            self.table_videos.setItem(row, 4, item_fps)
            self.table_videos.setItem(row, 5, item_vcodec)
            self.table_videos.setItem(row, 6, item_audio)

    def _move_up(self):
        curr_row = self.table_videos.currentRow()
        if curr_row > 0:
            self.video_list[curr_row], self.video_list[curr_row - 1] = self.video_list[curr_row - 1], self.video_list[curr_row]
            self._refresh_table()
            self.table_videos.selectRow(curr_row - 1)
            self._check_and_update_compatibility()

    def _move_down(self):
        curr_row = self.table_videos.currentRow()
        if 0 <= curr_row < len(self.video_list) - 1:
            self.video_list[curr_row], self.video_list[curr_row + 1] = self.video_list[curr_row + 1], self.video_list[curr_row]
            self._refresh_table()
            self.table_videos.selectRow(curr_row + 1)
            self._check_and_update_compatibility()

    def _remove_selected(self):
        curr_row = self.table_videos.currentRow()
        if 0 <= curr_row < len(self.video_list):
            self.video_list.pop(curr_row)
            self._refresh_table()
            self._check_and_update_compatibility()

    def _clear_all(self):
        self.video_list.clear()
        self._refresh_table()
        self._check_and_update_compatibility()

    # ==========================
    # Logic Kiểm Tra Tương Thích
    # ==========================
    def _check_and_update_compatibility(self):
        n = len(self.video_list)
        if n < 2:
            self.lbl_compat_status.setText("💡 Cần tối thiểu 2 video để ghép. Hãy thêm video vào danh sách.")
            self.lbl_compat_status.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 4px 0;")
            return

        total_dur = sum(v.get("duration", 0.0) for v in self.video_list)
        mins, secs = divmod(int(total_dur), 60)
        dur_str = f"{mins} phút {secs} giây" if mins > 0 else f"{secs} giây"

        compatible, msg = MergerEngine.check_compatibility(self.video_list)
        if compatible:
            self.lbl_compat_status.setText(
                f"✅ Đã chọn {n} video (Tổng thời lượng: ~{dur_str}).\n"
                f"⚡ {msg}"
            )
            self.lbl_compat_status.setStyleSheet("color: #34D399; font-weight: 500; font-size: 13px; padding: 4px 0;")
        else:
            self.lbl_compat_status.setText(
                f"ℹ️ Đã chọn {n} video (Tổng thời lượng: ~{dur_str}).\n"
                f"🔄 {msg}\n"
                f"App sẽ tự động áp dụng chế độ Ghép Chuẩn Hóa (Mã hóa lại) để video đồng bộ hoàn hảo."
            )
            self.lbl_compat_status.setStyleSheet("color: #FBBF24; font-size: 13px; padding: 4px 0;")

    def _on_crf_changed(self, val: int):
        desc = "Cực nét" if val <= 19 else ("Nét cao" if val <= 22 else ("Cân bằng tốt" if val <= 25 else "Dung lượng nhẹ"))
        self.lbl_crf_val.setText(f"Chất lượng mã hóa (CRF): {val} ({desc})")

    def _on_settings_changed(self):
        pass

    # ==========================
    # BGM Controls
    # ==========================
    def _toggle_bgm_controls(self, checked: bool):
        self.bgm_controls.setVisible(checked)

    def _browse_bgm_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Nhạc Nền BGM", "",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.flac *.ogg);;All Files (*.*)"
        )
        if file_path:
            self.txt_bgm_file.setText(file_path)

    def _on_mute_orig_toggled(self, checked: bool):
        self.slider_orig_vol.setEnabled(not checked)
        if checked:
            self.lbl_orig_vol.setText("Âm lượng video gốc: 0% (Đã tắt)")
        else:
            self.lbl_orig_vol.setText(f"Âm lượng video gốc: {self.slider_orig_vol.value()}%")

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Xuất", self.txt_out_dir.text())
        if folder:
            self.txt_out_dir.setText(folder)

    # ==========================
    # Submit Job to Queue
    # ==========================
    def _submit_to_queue(self):
        if len(self.video_list) < 2:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng chọn tối thiểu 2 video để ghép!")
            return

        out_dir = self.txt_out_dir.text().strip()
        if not out_dir or not os.path.exists(out_dir):
            QMessageBox.warning(self, "Lỗi", "Thư mục lưu không hợp lệ. Vui lòng chọn lại thư mục!")
            return

        out_name = self.txt_out_name.text().strip()
        if not out_name:
            out_name = "merged_output.mp4"
        if not out_name.lower().endswith(".mp4"):
            out_name += ".mp4"

        clean_name = clean_unicode_filename(Path(out_name).stem) + ".mp4"
        final_output_path = os.path.join(out_dir, clean_name)

        # Kiểm tra file BGM nếu bật
        bgm_enabled = self.chk_enable_bgm.isChecked()
        bgm_file = self.txt_bgm_file.text().strip() if bgm_enabled else None
        if bgm_enabled and (not bgm_file or not os.path.exists(bgm_file)):
            QMessageBox.warning(self, "Lỗi Nhạc Nền", "Bạn đã bật lồng nhạc nền nhưng chưa chọn file audio hợp lệ!")
            return

        # Quyết định chế độ ghép
        mode_pref = self.cbo_merge_mode.currentData()
        compatible, _ = MergerEngine.check_compatibility(self.video_list)

        # Nếu có BGM, bắt buộc phải mã hóa lại để mix audio
        if bgm_enabled:
            actual_mode = "reencode"
        elif mode_pref == "force_copy":
            actual_mode = "copy"
        elif mode_pref == "force_reencode":
            actual_mode = "reencode"
        else:  # auto
            actual_mode = "copy" if compatible else "reencode"

        # Độ phân giải
        res_data = self.cbo_res.currentData()
        target_res = None
        if res_data != "first" and "x" in str(res_data):
            w_str, h_str = res_data.split("x")
            target_res = (int(w_str), int(h_str))

        target_fps = self.cbo_fps.currentData()
        aspect_mode = self.cbo_aspect.currentData()
        use_gpu = self.cbo_gpu.currentData()
        crf = self.slider_crf.value()

        # Âm lượng
        orig_vol = 0.0 if self.chk_mute_orig.isChecked() else (self.slider_orig_vol.value() / 100.0)
        bgm_vol = self.slider_bgm_vol.value() / 100.0
        loop_bgm = self.chk_loop_bgm.isChecked()

        total_duration = sum(v.get("duration", 0.0) for v in self.video_list)

        job_params = {
            "video_paths": [v["file_path"] for v in self.video_list],
            "videos_info": self.video_list,
            "output_path": final_output_path,
            "mode": actual_mode,
            "target_resolution": target_res,
            "target_fps": target_fps,
            "aspect_ratio_mode": aspect_mode,
            "use_gpu": use_gpu,
            "crf": crf,
            "bgm_path": bgm_file,
            "bgm_volume": bgm_vol,
            "orig_volume": orig_vol,
            "loop_bgm": loop_bgm,
            "total_duration": total_duration
        }

        job = Job(
            module_id="merger",
            name=f"Ghép {len(self.video_list)} clips ➔ {clean_name}",
            output_path=final_output_path,
            params=job_params
        )

        self.bridge.submit_job(job)

        QMessageBox.information(
            self, "Thành Công",
            f"Đã thêm tác vụ ghép video vào Hàng Đợi (Job Queue)!\n"
            f"Chế độ áp dụng: {'⚡ Ghép Nhanh Copy' if actual_mode == 'copy' else '🔄 Ghép Chuẩn Hóa (Mã hóa lại)'}\n"
            f"Theo dõi tiến trình ở bảng Hàng Đợi bên dưới."
        )

