"""
Cutter Widget Component (Phase 4)
Giao diện người dùng của Module 2: Cắt & Phân Đoạn Video:
- Tích hợp trình phát video trực tiếp (QMediaPlayer + QVideoWidget) kèm thanh tua seek.
- Đặt mốc thời gian Start / End trực tiếp từ trình phát hoặc nhập tay chính xác.
- Xem thử đoạn cắt (Preview Cut Segment).
- Chế độ Cắt Nhanh (Stream Copy) kèm cảnh báo keyframe trực quan.
- Chế độ Cắt Chính Xác (Re-encode) hỗ trợ GPU và CRF.
- Chế độ Tự Động Chia Nhỏ (Auto-Split):
  * Cắt hàng loạt theo thời lượng 60s (TikTok/Shorts), 90s (Reels), 3 phút, 5 phút...
  * Quản lý danh sách phân đoạn (Phần 1, Phần 2...) linh hoạt.
- Đẩy tác vụ vào Hàng Đợi (Job Queue).
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QSlider, QRadioButton, QButtonGroup, QFrame, QFileDialog,
    QMessageBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSpinBox, QTabWidget
)
from PySide6.QtCore import Qt, QUrl, Slot, QTime
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from core.cutter_engine import CutterEngine
from core.ffmpeg_runner import FFmpegRunner
from core.system import format_bytes, clean_unicode_filename
from core.config import ConfigManager
from core.gpu import GPUDetector
from core.job_queue.job_model import Job


class CutterWidget(QWidget):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.config_mgr = ConfigManager.get_instance()

        self.current_video_path: Optional[str] = None
        self.current_duration: float = 0.0
        self.multi_segments: List[Dict[str, Any]] = []

        # Trình phát Media Player
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.setAcceptDrops(True)
        self._setup_ui()
        self._connect_player_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(14)

        # 1. Header
        header = QHBoxLayout()
        lbl_title = QLabel("✂️ Cắt & Phân Đoạn Video (Video Cutter)")
        lbl_title.setProperty("class", "heading")
        header.addWidget(lbl_title)
        header.addStretch()
        container_layout.addLayout(header)

        # 2. Card Chọn Video & Trình phát Player
        card_player = QFrame()
        card_player.setProperty("class", "card")
        player_layout = QVBoxLayout(card_player)
        player_layout.setSpacing(10)

        # Thanh chọn file
        file_row = QHBoxLayout()
        self.txt_video_file = QLineEdit()
        self.txt_video_file.setPlaceholderText("Kéo thả video vào đây hoặc bấm 'Chọn Video'...")
        self.txt_video_file.setReadOnly(True)

        btn_browse_video = QPushButton("📁 Chọn Video...")
        btn_browse_video.setProperty("class", "btn-secondary")
        btn_browse_video.clicked.connect(self._browse_video)

        file_row.addWidget(self.txt_video_file)
        file_row.addWidget(btn_browse_video)
        player_layout.addLayout(file_row)

        # Khung Video Widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(240)
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 6px;")
        self.player.setVideoOutput(self.video_widget)
        player_layout.addWidget(self.video_widget)

        # Thanh tua SeekBar & Thời gian
        seek_row = QHBoxLayout()
        self.slider_seek = QSlider(Qt.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)

        self.lbl_time = QLabel("00:00:00 / 00:00:00")
        self.lbl_time.setStyleSheet("font-family: Consolas, monospace; color: #94A3B8; font-size: 13px;")

        seek_row.addWidget(self.slider_seek)
        seek_row.addWidget(self.lbl_time)
        player_layout.addLayout(seek_row)

        # Nút điều khiển phát & Đặt điểm cắt Start / End
        ctrl_row = QHBoxLayout()

        self.btn_play = QPushButton("▶️ Phát")
        self.btn_play.setProperty("class", "btn-secondary")
        self.btn_play.clicked.connect(self._toggle_playback)

        self.btn_stop = QPushButton("⏹️ Dừng")
        self.btn_stop.setProperty("class", "btn-secondary")
        self.btn_stop.clicked.connect(self._stop_playback)

        btn_set_start = QPushButton("📍 [ Đặt Điểm Đầu (Start)")
        btn_set_start.setProperty("class", "btn-secondary")
        btn_set_start.setToolTip("Lấy vị trí hiện tại của video làm mốc bắt đầu cắt")
        btn_set_start.clicked.connect(self._set_current_as_start)

        btn_set_end = QPushButton("📍 ] Đặt Điểm Cuối (End)")
        btn_set_end.setProperty("class", "btn-secondary")
        btn_set_end.setToolTip("Lấy vị trí hiện tại của video làm mốc kết thúc cắt")
        btn_set_end.clicked.connect(self._set_current_as_end)

        btn_preview_cut = QPushButton("👁️ Xem Thử Đoạn Này")
        btn_preview_cut.setProperty("class", "btn-secondary")
        btn_preview_cut.clicked.connect(self._preview_cut_segment)

        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addSpacing(12)
        ctrl_row.addWidget(btn_set_start)
        ctrl_row.addWidget(btn_set_end)
        ctrl_row.addWidget(btn_preview_cut)
        ctrl_row.addStretch()
        player_layout.addLayout(ctrl_row)

        container_layout.addWidget(card_player)

        # 3. Card Phân Đoạn Cắt (Single Cut vs Auto-Split Tabs)
        card_segments = QFrame()
        card_segments.setProperty("class", "card")
        seg_layout = QVBoxLayout(card_segments)
        seg_layout.setSpacing(12)

        self.tab_cut_mode = QTabWidget()
        self.tab_cut_mode.setStyleSheet("""
            QTabBar::tab { background: #121418; color: #94A3B8; padding: 6px 16px; font-weight: bold; }
            QTabBar::tab:selected { background: #181B20; color: #38BDF8; border-top: 2px solid #38BDF8; }
        """)

        # Tab 1: Cắt một đoạn đơn lẻ
        tab_single = QWidget()
        single_layout = QVBoxLayout(tab_single)
        single_layout.setSpacing(10)

        time_inputs_row = QHBoxLayout()
        time_inputs_row.setSpacing(16)

        vbox_s = QVBoxLayout()
        vbox_s.addWidget(QLabel("Thời điểm bắt đầu (HH:MM:SS):"))
        self.txt_start_time = QLineEdit("00:00:00")
        self.txt_start_time.setStyleSheet("font-family: Consolas, monospace;")
        self.txt_start_time.textChanged.connect(self._update_cut_duration_label)
        vbox_s.addWidget(self.txt_start_time)
        time_inputs_row.addLayout(vbox_s)

        vbox_e = QVBoxLayout()
        vbox_e.addWidget(QLabel("Thời điểm kết thúc (HH:MM:SS):"))
        self.txt_end_time = QLineEdit("00:00:00")
        self.txt_end_time.setStyleSheet("font-family: Consolas, monospace;")
        self.txt_end_time.textChanged.connect(self._update_cut_duration_label)
        vbox_e.addWidget(self.txt_end_time)
        time_inputs_row.addLayout(vbox_e)

        vbox_dur = QVBoxLayout()
        vbox_dur.addWidget(QLabel("Thời lượng đoạn cắt:"))
        self.lbl_cut_dur = QLabel("00:00:00")
        self.lbl_cut_dur.setStyleSheet("font-family: Consolas, monospace; font-size: 14px; font-weight: bold; color: #34D399; margin-top: 6px;")
        vbox_dur.addWidget(self.lbl_cut_dur)
        time_inputs_row.addLayout(vbox_dur)

        single_layout.addLayout(time_inputs_row)

        btn_add_to_multilist = QPushButton("➕ Thêm Đoạn Này Vào Danh Sách Cắt Hàng Loạt")
        btn_add_to_multilist.setProperty("class", "btn-secondary")
        btn_add_to_multilist.clicked.connect(self._add_current_cut_to_list)
        single_layout.addWidget(btn_add_to_multilist)

        self.tab_cut_mode.addTab(tab_single, "✂️ Cắt Một Đoạn")

        # Tab 2: Cắt nhiều đoạn & Tự động chia nhỏ (Auto-Split)
        tab_multi = QWidget()
        multi_layout = QVBoxLayout(tab_multi)
        multi_layout.setSpacing(10)

        # Toolbar Auto-Split
        auto_split_row = QHBoxLayout()
        auto_split_row.addWidget(QLabel("⚡ Tự động chia nhỏ theo thời lượng:"))

        self.cbo_preset_split = QComboBox()
        self.cbo_preset_split.addItem("60 giây (TikTok / YouTube Shorts)", 60.0)
        self.cbo_preset_split.addItem("90 giây (Instagram / Reels)", 90.0)
        self.cbo_preset_split.addItem("180 giây (3 phút)", 180.0)
        self.cbo_preset_split.addItem("300 giây (5 phút)", 300.0)
        self.cbo_preset_split.addItem("Tùy chỉnh...", "custom")
        self.cbo_preset_split.currentIndexChanged.connect(self._on_split_preset_changed)
        auto_split_row.addWidget(self.cbo_preset_split)

        self.spin_custom_sec = QSpinBox()
        self.spin_custom_sec.setRange(5, 7200)
        self.spin_custom_sec.setValue(60)
        self.spin_custom_sec.setSuffix(" giây")
        self.spin_custom_sec.setVisible(False)
        auto_split_row.addWidget(self.spin_custom_sec)

        btn_run_auto_split = QPushButton("🚀 Tự Động Chia Phân Đoạn")
        btn_run_auto_split.setProperty("class", "btn-secondary")
        btn_run_auto_split.clicked.connect(self._generate_auto_splits)
        auto_split_row.addWidget(btn_run_auto_split)

        btn_clear_segs = QPushButton("🧹 Xóa Hết Đoạn")
        btn_clear_segs.setProperty("class", "btn-secondary")
        btn_clear_segs.clicked.connect(self._clear_segments)
        auto_split_row.addWidget(btn_clear_segs)

        auto_split_row.addStretch()
        multi_layout.addLayout(auto_split_row)

        # Bảng danh sách phân đoạn
        self.table_segs = QTableWidget(0, 5)
        self.table_segs.setHorizontalHeaderLabels([
            "#", "Tên Phân Đoạn", "Bắt Đầu", "Kết Thúc", "Thời Lượng"
        ])
        self.table_segs.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_segs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_segs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_segs.setMinimumHeight(150)
        self.table_segs.setMaximumHeight(220)
        multi_layout.addWidget(self.table_segs)

        self.tab_cut_mode.addTab(tab_multi, "⚡ Tự Động Chia Nhỏ / Cắt Hàng Loạt")

        seg_layout.addWidget(self.tab_cut_mode)
        container_layout.addWidget(card_segments)

        # 4. Card Chế độ cắt & Tăng tốc
        card_mode = QFrame()
        card_mode.setProperty("class", "card")
        mode_layout = QVBoxLayout(card_mode)
        mode_layout.setSpacing(10)

        lbl_mode_title = QLabel("⚙️ Chế Độ Cắt & Tối Ưu")
        lbl_mode_title.setProperty("class", "subheading")
        mode_layout.addWidget(lbl_mode_title)

        mode_btn_row = QHBoxLayout()
        self.rad_copy = QRadioButton("⚡ Cắt Nhanh (Stream Copy) - Siêu tốc, giữ 100% chất lượng gốc")
        self.rad_copy.setChecked(True)
        self.rad_copy.toggled.connect(self._on_cut_mode_toggled)

        self.rad_reencode = QRadioButton("🎯 Cắt Chính Xác (Re-encode) - Chuẩn xác từng khung hình")
        self.rad_reencode.toggled.connect(self._on_cut_mode_toggled)

        mode_group = QButtonGroup(self)
        mode_group.addButton(self.rad_copy)
        mode_group.addButton(self.rad_reencode)

        mode_btn_row.addWidget(self.rad_copy)
        mode_btn_row.addWidget(self.rad_reencode)
        mode_layout.addLayout(mode_btn_row)

        # Cảnh báo Keyframe khi chọn Stream Copy
        self.lbl_keyframe_warn = QLabel(CutterEngine.get_keyframe_warning())
        self.lbl_keyframe_warn.setStyleSheet("color: #FBBF24; font-size: 13px; padding: 4px 0;")
        self.lbl_keyframe_warn.setWordWrap(True)
        mode_layout.addWidget(self.lbl_keyframe_warn)

        # Tùy chọn nâng cao khi Re-encode (Ẩn mặc định)
        self.reencode_options = QWidget()
        reenc_layout = QHBoxLayout(self.reencode_options)
        reenc_layout.setContentsMargins(0, 0, 0, 0)
        reenc_layout.setSpacing(16)

        vbox_gpu = QVBoxLayout()
        vbox_gpu.addWidget(QLabel("Bộ mã hóa (GPU/CPU):"))
        self.cbo_gpu = QComboBox()
        best_gpu = GPUDetector.get_best_encoder()
        gpu_name = best_gpu.get("name", "Không có GPU rời") if best_gpu else "Không có GPU rời"
        self.cbo_gpu.addItem(f"⚡ GPU: {gpu_name}", True)
        self.cbo_gpu.addItem("💻 Chỉ dùng CPU (libx264)", False)
        vbox_gpu.addWidget(self.cbo_gpu)
        reenc_layout.addLayout(vbox_gpu)

        vbox_crf = QVBoxLayout()
        self.lbl_crf_val = QLabel("Chất lượng CRF: 23 (Cân bằng tốt)")
        self.slider_crf = QSlider(Qt.Horizontal)
        self.slider_crf.setRange(18, 30)
        self.slider_crf.setValue(23)
        self.slider_crf.valueChanged.connect(lambda v: self.lbl_crf_val.setText(f"Chất lượng CRF: {v}"))
        vbox_crf.addWidget(self.lbl_crf_val)
        vbox_crf.addWidget(self.slider_crf)
        reenc_layout.addLayout(vbox_crf)

        mode_layout.addWidget(self.reencode_options)
        self.reencode_options.setVisible(False)

        container_layout.addWidget(card_mode)

        # 5. Card Thư mục xuất & Bắt đầu
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
        lbl_name = QLabel("Tên phim / Mẫu tên file:")
        self.txt_movie_name = QLineEdit("video_cut")
        name_row.addWidget(lbl_name)
        name_row.addWidget(self.txt_movie_name)
        out_layout.addLayout(name_row)

        self.btn_submit = QPushButton("🚀 Bắt Đầu Cắt Video (Thêm vào Hàng Đợi)")
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
    # Player & Media Signals
    # ==========================
    def _connect_player_signals(self):
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)

    def _toggle_playback(self):
        if not self.current_video_path:
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶️ Phát")
        else:
            self.player.play()
            self.btn_play.setText("⏸️ Tạm Dừng")

    def _stop_playback(self):
        self.player.stop()
        self.btn_play.setText("▶️ Phát")

    def _on_player_position_changed(self, pos_ms: int):
        if self.current_duration > 0 and not self.slider_seek.isSliderDown():
            val = int((pos_ms / (self.current_duration * 1000.0)) * 1000)
            self.slider_seek.setValue(val)

        cur_sec = pos_ms / 1000.0
        cur_str = CutterEngine.format_seconds_to_time(cur_sec)
        tot_str = CutterEngine.format_seconds_to_time(self.current_duration)
        self.lbl_time.setText(f"{cur_str} / {tot_str}")

    def _on_player_duration_changed(self, dur_ms: int):
        if dur_ms > 0 and self.current_duration <= 0:
            self.current_duration = dur_ms / 1000.0
            self.txt_end_time.setText(CutterEngine.format_seconds_to_time(self.current_duration))
            self._update_cut_duration_label()

    def _on_seek_moved(self, val: int):
        if self.current_duration > 0:
            target_ms = int((val / 1000.0) * (self.current_duration * 1000.0))
            self.player.setPosition(target_ms)

    def _set_current_as_start(self):
        cur_sec = self.player.position() / 1000.0
        self.txt_start_time.setText(CutterEngine.format_seconds_to_time(cur_sec, include_ms=True))
        self._update_cut_duration_label()

    def _set_current_as_end(self):
        cur_sec = self.player.position() / 1000.0
        self.txt_end_time.setText(CutterEngine.format_seconds_to_time(cur_sec, include_ms=True))
        self._update_cut_duration_label()

    def _update_cut_duration_label(self):
        s = CutterEngine.parse_time_to_seconds(self.txt_start_time.text())
        e = CutterEngine.parse_time_to_seconds(self.txt_end_time.text())
        dur = max(0.0, e - s)
        self.lbl_cut_dur.setText(CutterEngine.format_seconds_to_time(dur, include_ms=True))

    def _preview_cut_segment(self):
        s = CutterEngine.parse_time_to_seconds(self.txt_start_time.text())
        self.player.setPosition(int(s * 1000.0))
        self.player.play()
        self.btn_play.setText("⏸️ Tạm Dừng")

    # ==========================
    # Drag & Drop & Browse
    # ==========================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isfile(p):
                ext = Path(p).suffix.lower()
                if ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".ts", ".m4v"}:
                    self._load_video(p)
                    break

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn Video Cần Cắt", "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.webm *.flv *.ts *.m4v);;All Files (*.*)"
        )
        if path:
            self._load_video(path)

    def _load_video(self, path: str):
        self.current_video_path = path
        self.txt_video_file.setText(path)
        base_name = clean_unicode_filename(Path(path).stem)
        self.txt_movie_name.setText(base_name)

        # Lấy thông số từ ffprobe
        try:
            info = FFmpegRunner.probe(path)
            self.current_duration = info.get("duration", 0.0)
        except Exception:
            self.current_duration = 0.0

        self.txt_start_time.setText("00:00:00.000")
        self.txt_end_time.setText(CutterEngine.format_seconds_to_time(self.current_duration, include_ms=True))
        self._update_cut_duration_label()

        # Nạp vào Player
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.pause()

    # ==========================
    # Segments & Auto-Split
    # ==========================
    def _on_split_preset_changed(self):
        val = self.cbo_preset_split.currentData()
        self.spin_custom_sec.setVisible(val == "custom")

    def _generate_auto_splits(self):
        if not self.current_video_path or self.current_duration <= 0:
            QMessageBox.warning(self, "Chưa chọn video", "Vui lòng chọn video trước khi thực hiện chia phân đoạn!")
            return

        val = self.cbo_preset_split.currentData()
        seg_sec = float(self.spin_custom_sec.value()) if val == "custom" else float(val)

        movie_title = self.txt_movie_name.text().strip() or "Phim"
        self.multi_segments = CutterEngine.generate_split_segments(
            total_duration=self.current_duration,
            segment_duration=seg_sec,
            base_name="Phần"
        )

        self._refresh_segments_table()
        QMessageBox.information(
            self, "Chia Thành Công",
            f"Đã tự động chia video thành {len(self.multi_segments)} phân đoạn (mỗi đoạn ~{seg_sec:.0f}s)!"
        )

    def _add_current_cut_to_list(self):
        if not self.current_video_path:
            QMessageBox.warning(self, "Chưa chọn video", "Vui lòng chọn video trước!")
            return

        s = CutterEngine.parse_time_to_seconds(self.txt_start_time.text())
        e = CutterEngine.parse_time_to_seconds(self.txt_end_time.text())

        if e <= s:
            QMessageBox.warning(self, "Thời gian không hợp lệ", "Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu!")
            return

        idx = len(self.multi_segments) + 1
        self.multi_segments.append({
            "index": idx,
            "name": f"Đoạn {idx}",
            "start": round(s, 3),
            "end": round(e, 3),
            "duration": round(e - s, 3)
        })

        self._refresh_segments_table()
        # Chuyển sang tab multi để người dùng thấy
        self.tab_cut_mode.setCurrentIndex(1)

    def _refresh_segments_table(self):
        self.table_segs.setRowCount(len(self.multi_segments))
        for row, seg in enumerate(self.multi_segments):
            item_idx = QTableWidgetItem(str(row + 1))
            item_idx.setTextAlignment(Qt.AlignCenter)

            item_name = QTableWidgetItem(seg.get("name", ""))
            item_start = QTableWidgetItem(CutterEngine.format_seconds_to_time(seg.get("start", 0.0), include_ms=True))
            item_start.setTextAlignment(Qt.AlignCenter)

            item_end = QTableWidgetItem(CutterEngine.format_seconds_to_time(seg.get("end", 0.0), include_ms=True))
            item_end.setTextAlignment(Qt.AlignCenter)

            item_dur = QTableWidgetItem(CutterEngine.format_seconds_to_time(seg.get("duration", 0.0)))
            item_dur.setTextAlignment(Qt.AlignCenter)

            self.table_segs.setItem(row, 0, item_idx)
            self.table_segs.setItem(row, 1, item_name)
            self.table_segs.setItem(row, 2, item_start)
            self.table_segs.setItem(row, 3, item_end)
            self.table_segs.setItem(row, 4, item_dur)

    def _clear_segments(self):
        self.multi_segments.clear()
        self._refresh_segments_table()

    # ==========================
    # Settings & Submit
    # ==========================
    def _on_cut_mode_toggled(self):
        is_copy = self.rad_copy.isChecked()
        self.lbl_keyframe_warn.setVisible(is_copy)
        self.reencode_options.setVisible(not is_copy)

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Lưu", self.txt_out_dir.text())
        if folder:
            self.txt_out_dir.setText(folder)

    def _submit_to_queue(self):
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file video hợp lệ!")
            return

        out_dir = self.txt_out_dir.text().strip()
        if not out_dir or not os.path.exists(out_dir):
            QMessageBox.warning(self, "Lỗi", "Thư mục lưu không hợp lệ!")
            return

        movie_title = clean_unicode_filename(self.txt_movie_name.text().strip() or "video_cut")
        is_copy = self.rad_copy.isChecked()
        mode = "copy" if is_copy else "reencode"
        use_gpu = self.cbo_gpu.currentData()
        crf = self.slider_crf.value()

        # Kiểm tra xem đang cắt 1 đoạn hay danh sách phân đoạn
        is_single_tab = (self.tab_cut_mode.currentIndex() == 0)
        submitted_count = 0

        if is_single_tab:
            # Cắt 1 đoạn đơn lẻ
            s = CutterEngine.parse_time_to_seconds(self.txt_start_time.text())
            e = CutterEngine.parse_time_to_seconds(self.txt_end_time.text())

            if e <= s:
                QMessageBox.warning(self, "Thời gian không hợp lệ", "Thời điểm kết thúc phải lớn hơn bắt đầu!")
                return

            out_filename = f"{movie_title}_cut.mp4"
            out_file_path = os.path.join(out_dir, out_filename)

            job = Job(
                module_id="cutter",
                name=f"Cắt: {movie_title} [{CutterEngine.format_seconds_to_time(s)} ➔ {CutterEngine.format_seconds_to_time(e)}]",
                output_path=out_file_path,
                params={
                    "input_path": self.current_video_path,
                    "output_path": out_file_path,
                    "start_time": s,
                    "end_time": e,
                    "mode": mode,
                    "use_gpu": use_gpu,
                    "crf": crf
                }
            )
            self.bridge.submit_job(job)
            submitted_count += 1

        else:
            # Cắt danh sách nhiều phân đoạn (Multi-Split)
            if not self.multi_segments:
                QMessageBox.warning(self, "Trống", "Danh sách phân đoạn đang trống! Hãy bấm 'Tự Động Chia Phân Đoạn' hoặc thêm đoạn vào danh sách.")
                return

            for i, seg in enumerate(self.multi_segments, 1):
                s = seg["start"]
                e = seg["end"]
                out_filename = f"{movie_title}_Phan_{i:02d}.mp4"
                out_file_path = os.path.join(out_dir, out_filename)

                job = Job(
                    module_id="cutter",
                    name=f"Cắt {movie_title} (Phần {i}) [{CutterEngine.format_seconds_to_time(s)} ➔ {CutterEngine.format_seconds_to_time(e)}]",
                    output_path=out_file_path,
                    params={
                        "input_path": self.current_video_path,
                        "output_path": out_file_path,
                        "start_time": s,
                        "end_time": e,
                        "mode": mode,
                        "use_gpu": use_gpu,
                        "crf": crf
                    }
                )
                self.bridge.submit_job(job)
                submitted_count += 1

        QMessageBox.information(
            self, "Thành Công",
            f"Đã thêm thành công {submitted_count} tác vụ cắt video vào Hàng Đợi (Job Queue)!\n"
            f"Chế độ: {'⚡ Cắt Nhanh (Stream Copy)' if is_copy else '🎯 Cắt Chính Xác (Re-encode)'}\n"
            f"Theo dõi tiến trình ở bảng Hàng Đợi bên dưới."
        )

