"""
Downloader View Component (Module 1 - Phase 2)
Giao diện người dùng Trình Tải Video Đa Năng:
- Tự động bắt link từ Clipboard khi copy
- Kiểm tra link trùng lặp với SQLite Database
- Trích xuất thông tin video (Tiêu đề, Kênh, Thời lượng, Định dạng)
- Hỗ trợ tải đơn link, tải cả Playlist và tải hàng loạt (Batch Mode)
- Đẩy tác vụ vào Job Queue dùng chung
- Dòng Disclaimer miễn trừ trách nhiệm bản quyền
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QFrame, QFileDialog, QMessageBox,
    QTabWidget, QTextEdit, QRadioButton, QButtonGroup, QApplication
)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from core.ytdlp_engine import YtDlpEngine
from core.database import HistoryDB
from core.config import ConfigManager
from core.system import clean_unicode_filename
from core.job_queue.job_model import Job


class InfoExtractorWorker(QThread):
    """Luồng phụ lấy nhanh metadata video để không đơ UI."""
    info_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, url: str, proxy: str = ""):
        super().__init__()
        self.url = url
        self.proxy = proxy

    def run(self):
        try:
            info = YtDlpEngine.extract_info(self.url, proxy=self.proxy)
            self.info_ready.emit(info)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloaderView(QWidget):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.config_mgr = ConfigManager.get_instance()
        self.db = HistoryDB.get_instance()
        self.info_worker: Optional[InfoExtractorWorker] = None
        self.last_clipboard_url = ""
        self.current_video_info: Optional[Dict[str, Any]] = None

        self._setup_ui()
        self._init_clipboard_monitor()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. Header Module
        header = QHBoxLayout()
        lbl_title = QLabel("📥 Trình Tải Video Đa Năng")
        lbl_title.setProperty("class", "heading")

        lbl_platforms = QLabel("🌐 Hỗ trợ: YouTube • TikTok (Không logo) • Facebook Reels • Instagram • Bilibili • X")
        lbl_platforms.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 500; margin-left: 10px;")

        self.chk_clipboard = QCheckBox("⚡ Bắt link Clipboard")
        self.chk_clipboard.setChecked(self.config_mgr.get("auto_clipboard", True))
        self.chk_clipboard.setStyleSheet("color: #818CF8; font-weight: 500;")

        header.addWidget(lbl_title)
        header.addWidget(lbl_platforms)
        header.addStretch()
        header.addWidget(self.chk_clipboard)
        main_layout.addLayout(header)

        # 2. Tabs: Tải Đơn Link vs Tải Hàng Loạt (Batch)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2D333E; border-radius: 8px; background: #181B20; }
            QTabBar::tab { background: #121418; color: #94A3B8; padding: 7px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-weight: 500; }
            QTabBar::tab:selected { background: #181B20; color: #FFFFFF; font-weight: bold; border: 1px solid #2D333E; border-bottom: none; }
        """)

        # --- Tab 1: Tải Đơn Link / Playlist ---
        tab_single = QWidget()
        single_layout = QVBoxLayout(tab_single)
        single_layout.setContentsMargins(14, 14, 14, 14)
        single_layout.setSpacing(10)

        row_input = QHBoxLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Dán đường link YouTube, TikTok, Facebook Reels, Douyin, X, Bilibili vào đây...")
        self.txt_url.textChanged.connect(self._on_url_text_changed)

        btn_paste = QPushButton("📋 Dán")
        btn_paste.setProperty("class", "btn-secondary")
        btn_paste.setCursor(Qt.PointingHandCursor)
        btn_paste.clicked.connect(self._paste_clipboard)

        self.btn_inspect = QPushButton("🔍 Lấy Thông Tin")
        self.btn_inspect.setProperty("class", "btn-secondary")
        self.btn_inspect.setCursor(Qt.PointingHandCursor)
        self.btn_inspect.clicked.connect(self._inspect_video)

        row_input.addWidget(self.txt_url, 1)
        row_input.addWidget(btn_paste)
        row_input.addWidget(self.btn_inspect)
        single_layout.addLayout(row_input)

        # Card Thông Tin Video
        self.card_info = QFrame()
        self.card_info.setProperty("class", "card")
        self.card_info.setStyleSheet("background: #121418; padding: 10px;")
        info_layout = QVBoxLayout(self.card_info)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        self.lbl_video_title = QLabel("🎬 Chưa có thông tin video. Hãy dán link và bấm 'Lấy Thông Tin'.")
        self.lbl_video_title.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 13px;")
        self.lbl_video_title.setWordWrap(True)

        self.lbl_video_meta = QLabel("⏱️ Thời lượng: --:--  |  👤 Kênh: --")
        self.lbl_video_meta.setStyleSheet("font-size: 11px; color: #94A3B8;")

        self.lbl_dedup_warning = QLabel("")
        self.lbl_dedup_warning.setStyleSheet("font-size: 11px; color: #FBBF24; font-weight: bold;")
        self.lbl_dedup_warning.setVisible(False)

        info_layout.addWidget(self.lbl_video_title)
        info_layout.addWidget(self.lbl_video_meta)
        info_layout.addWidget(self.lbl_dedup_warning)
        single_layout.addWidget(self.card_info)

        self.tabs.addTab(tab_single, "Tải Đơn Link / Playlist")

        # --- Tab 2: Tải Hàng Loạt (Batch Links) ---
        tab_batch = QWidget()
        batch_layout = QVBoxLayout(tab_batch)
        batch_layout.setContentsMargins(14, 14, 14, 14)
        batch_layout.setSpacing(6)

        lbl_batch_hint = QLabel("Nhập danh sách link video (mỗi link nằm trên một dòng):")
        lbl_batch_hint.setStyleSheet("color: #94A3B8; font-size: 11px;")

        self.txt_batch_urls = QTextEdit()
        self.txt_batch_urls.setPlaceholderText("https://www.youtube.com/watch?v=...\nhttps://www.tiktok.com/@.../video/...\nhttps://fb.watch/...")
        self.txt_batch_urls.setFixedHeight(95)

        batch_layout.addWidget(lbl_batch_hint)
        batch_layout.addWidget(self.txt_batch_urls)
        self.tabs.addTab(tab_batch, "Tải Hàng Loạt (Batch Links)")

        main_layout.addWidget(self.tabs)

        # 3. Card Tuỳ Chọn Tải Xuống
        card_opts = QFrame()
        card_opts.setProperty("class", "card")
        opts_layout = QVBoxLayout(card_opts)
        opts_layout.setSpacing(10)

        # Chế độ: Video vs Chỉ Tách Nhạc
        row_type = QHBoxLayout()
        self.rad_video = QRadioButton("Tải Video + Audio")
        self.rad_video.setChecked(True)
        self.rad_audio = QRadioButton("Chỉ Tách Âm Thanh (Audio Only)")
        
        type_group = QButtonGroup(self)
        type_group.addButton(self.rad_video)
        type_group.addButton(self.rad_audio)
        self.rad_video.toggled.connect(self._on_type_changed)

        row_type.addWidget(self.rad_video)
        row_type.addWidget(self.rad_audio)
        row_type.addStretch()
        opts_layout.addLayout(row_type)

        # Dropdown chất lượng / định dạng
        row_qual = QHBoxLayout()
        lbl_qual = QLabel("Chất Lượng:")
        lbl_qual.setStyleSheet("color: #94A3B8; font-weight: 500;")

        self.cbo_quality = QComboBox()
        self._populate_video_qualities()

        lbl_limit = QLabel("Giới Hạn Tốc Độ:")
        lbl_limit.setStyleSheet("color: #94A3B8; font-weight: 500; margin-left: 12px;")
        self.cbo_speed_limit = QComboBox()
        self.cbo_speed_limit.addItem("Không giới hạn", "")
        self.cbo_speed_limit.addItem("10 MB/s", "10M")
        self.cbo_speed_limit.addItem("5 MB/s", "5M")
        self.cbo_speed_limit.addItem("2 MB/s", "2M")
        self.cbo_speed_limit.addItem("1 MB/s", "1M")

        self.chk_subtitles = QCheckBox("Tải kèm phụ đề (vi/en nếu có)")
        self.chk_playlist = QCheckBox("Tải toàn bộ Playlist (nếu link là playlist)")

        row_qual.addWidget(lbl_qual)
        row_qual.addWidget(self.cbo_quality, 1)
        row_qual.addWidget(lbl_limit)
        row_qual.addWidget(self.cbo_speed_limit)
        row_qual.addWidget(self.chk_subtitles)
        row_qual.addWidget(self.chk_playlist)
        opts_layout.addLayout(row_qual)

        main_layout.addWidget(card_opts)

        # 4. Khu vực Lưu & Nút Submit Job
        action_row = QHBoxLayout()
        lbl_dest = QLabel("Lưu Tại:")
        lbl_dest.setStyleSheet("color: #94A3B8; font-weight: 500;")

        default_dir = self.config_mgr.get("default_output_dir", str(Path.home() / "Downloads"))
        self.txt_dest = QLineEdit(default_dir)

        btn_browse_dest = QPushButton("📁")
        btn_browse_dest.setToolTip("Chọn thư mục lưu")
        btn_browse_dest.setProperty("class", "btn-secondary")
        btn_browse_dest.clicked.connect(self._browse_dest)

        self.btn_submit = QPushButton("🚀 Thêm Vào Hàng Đợi (Job Queue)")
        self.btn_submit.setProperty("class", "btn-primary")
        self.btn_submit.setMinimumHeight(38)
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.clicked.connect(self._submit_to_queue)

        action_row.addWidget(lbl_dest)
        action_row.addWidget(self.txt_dest, 1)
        action_row.addWidget(btn_browse_dest)
        action_row.addWidget(self.btn_submit, 1)
        main_layout.addLayout(action_row)

        # Disclaimer bản quyền
        lbl_disclaimer = QLabel("⚖️ Miễn trừ trách nhiệm: Ứng dụng chỉ cung cấp công cụ kỹ thuật. Bạn hoàn toàn tự chịu trách nhiệm về bản quyền đối với các video được tải về.")
        lbl_disclaimer.setStyleSheet("color: #64748B; font-size: 10px; font-style: italic;")
        main_layout.addWidget(lbl_disclaimer)

    def _populate_video_qualities(self):
        self.cbo_quality.clear()
        self.cbo_quality.addItem("Cao Nhất Tự Động (Best Quality)", "best")
        self.cbo_quality.addItem("4K Ultra HD (2160p)", "4K")
        self.cbo_quality.addItem("Full HD (1080p)", "1080p")
        self.cbo_quality.addItem("HD (720p)", "720p")
        self.cbo_quality.addItem("SD (480p)", "480p")
        self.cbo_quality.setCurrentIndex(2)

    def _populate_audio_qualities(self):
        self.cbo_quality.clear()
        self.cbo_quality.addItem("MP3 (Chất lượng cao 192kbps)", "mp3")
        self.cbo_quality.addItem("M4A (Chuẩn AAC)", "m4a")
        self.cbo_quality.addItem("WAV (Âm thanh gốc Lossless)", "wav")

    def _on_type_changed(self):
        if self.rad_video.isChecked():
            self._populate_video_qualities()
            self.chk_subtitles.setEnabled(True)
        else:
            self._populate_audio_qualities()
            self.chk_subtitles.setEnabled(False)

    def _browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Lưu Video", self.txt_dest.text())
        if folder:
            self.txt_dest.setText(folder)

    def _paste_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.txt_url.setText(text)

    def _init_clipboard_monitor(self):
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self._on_clipboard_changed)

    def _on_clipboard_changed(self):
        if not self.chk_clipboard.isChecked():
            return

        text = QApplication.clipboard().text().strip()
        if not text or text == self.last_clipboard_url:
            return

        video_pattern = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be|tiktok\.com|facebook\.com|fb\.watch|douyin\.com|instagram\.com|bilibili\.com)/.+'
        if re.match(video_pattern, text, re.IGNORECASE):
            self.last_clipboard_url = text
            self.txt_url.setText(text)
            self._inspect_video()

    def _on_url_text_changed(self, text: str):
        url = text.strip()
        if not url:
            self.lbl_video_title.setText("🎬 Chưa có thông tin video.")
            self.lbl_video_meta.setText("⏱️ Thời lượng: --:--  |  👤 Kênh: --")
            self.lbl_dedup_warning.setVisible(False)
            self.current_video_info = None
        else:
            # Kiểm tra xem link đã từng được tải chưa
            if self.db.is_url_downloaded(url):
                self.lbl_dedup_warning.setText("⚠️ Link này đã được bạn tải thành công trước đó trong lịch sử.")
                self.lbl_dedup_warning.setVisible(True)
            else:
                self.lbl_dedup_warning.setVisible(False)

    def _inspect_video(self):
        url = self.txt_url.text().strip()
        if not url:
            return

        self.btn_inspect.setEnabled(False)
        self.lbl_video_title.setText("⏳ Đang phân tích thông tin đường link...")

        proxy = self.config_mgr.get("proxy", "")
        self.info_worker = InfoExtractorWorker(url, proxy=proxy)
        self.info_worker.info_ready.connect(self._on_info_ready)
        self.info_worker.error_occurred.connect(self._on_info_error)
        self.info_worker.start()

    def _on_info_ready(self, info: dict):
        self.btn_inspect.setEnabled(True)
        self.current_video_info = info
        if info.get('is_playlist'):
            self.lbl_video_title.setText(f"📑 Danh sách phát: {info.get('title')} ({info.get('count')} video)")
            self.lbl_video_meta.setText("⚡ Hãy tích chọn 'Tải toàn bộ Playlist' nếu muốn tải tất cả.")
            self.chk_playlist.setChecked(True)
        else:
            self.lbl_video_title.setText(f"🎬 {info.get('title')}")
            self.lbl_video_meta.setText(f"⏱️ Thời lượng: {info.get('duration_str')}  |  👤 Kênh: {info.get('uploader')}")

    def _on_info_error(self, err: str):
        self.btn_inspect.setEnabled(True)
        self.lbl_video_title.setText("⚠️ Không đọc trước được thông tin, nhưng vẫn có thể bấm tải xuống.")

    def _submit_to_queue(self):
        output_dir = self.txt_dest.text().strip()
        if not output_dir or not os.path.exists(output_dir):
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn thư mục lưu hợp lệ!")
            return

        urls = []
        is_playlist = False
        if self.tabs.currentIndex() == 0:
            single_url = self.txt_url.text().strip()
            if not single_url:
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đường link video!")
                return
            urls = [single_url]
            is_playlist = self.chk_playlist.isChecked()
        else:
            batch_text = self.txt_batch_urls.toPlainText().strip()
            if not batch_text:
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập danh sách link hàng loạt!")
                return
            urls = [line.strip() for line in batch_text.splitlines() if line.strip()]

        audio_only = self.rad_audio.isChecked()
        quality_or_format = self.cbo_quality.currentData()
        quality = quality_or_format if not audio_only else "1080p"
        audio_format = quality_or_format if audio_only else "mp3"
        download_subs = self.chk_subtitles.isChecked()
        limit_rate = self.cbo_speed_limit.currentData()
        proxy = self.config_mgr.get("proxy", "")

        submitted_count = 0
        for idx, url in enumerate(urls, 1):
            title = self.current_video_info.get("title", f"Video_{idx}") if (self.current_video_info and len(urls) == 1) else f"Video_{idx}"
            clean_title = clean_unicode_filename(title)
            ext = audio_format if audio_only else "mp4"
            expected_out = os.path.join(output_dir, f"{clean_title}.{ext}")

            job = Job(
                module_id="downloader",
                name=f"Download: {title[:40]}",
                output_path=expected_out,
                params={
                    "url": url,
                    "title": title,
                    "output_dir": output_dir,
                    "quality": quality,
                    "audio_only": audio_only,
                    "audio_format": audio_format,
                    "download_subs": download_subs,
                    "is_playlist": is_playlist,
                    "limit_rate": limit_rate,
                    "proxy": proxy
                }
            )
            self.bridge.submit_job(job)
            submitted_count += 1

        QMessageBox.information(
            self, "Thành Công",
            f"Đã thêm thành công {submitted_count} tác vụ tải vào Hàng Đợi (Job Queue)!\nBạn có thể theo dõi tiến độ ở bảng bên dưới."
        )
        if self.tabs.currentIndex() == 0:
            self.txt_url.clear()
        else:
            self.txt_batch_urls.clear()
