"""
Help & User Guide Dialog (Hướng Dẫn Sử Dụng & Trợ Giúp)
Cung cấp tài liệu hướng dẫn chi tiết, hướng dẫn bắt đầu nhanh và các lưu ý quan trọng.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTextBrowser, QFrame
)
from PySide6.QtCore import Qt
from ui.theme import ThemeManager


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📖 Hướng Dẫn Sử Dụng - All-in-One Media Studio")
        self.resize(780, 560)
        self.setMinimumSize(680, 480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        lbl_icon = QLabel("🎬")
        lbl_icon.setStyleSheet("font-size: 26px;")
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Hướng Dẫn Sử Dụng & Sổ Tay Vận Hành")
        lbl_title.setProperty("class", "heading")
        lbl_sub = QLabel("Cẩm nang nhanh cho người mới bắt đầu và các lưu ý quan trọng khi xử lý video")
        lbl_sub.setProperty("class", "label-muted")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)

        header.addWidget(lbl_icon)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Tabs hướng dẫn
        tabs = QTabWidget()

        # Tab 1: Bắt đầu nhanh
        tabs.addTab(self._create_quickstart_tab(), "🚀 Bắt Đầu Nhanh")
        # Tab 2: Tải video đa nền tảng
        tabs.addTab(self._create_downloader_tab(), "📥 Tải Video Đa Nền Tảng")
        # Tab 3: Cắt & Ghép video
        tabs.addTab(self._create_editing_tab(), "✂️ Cắt & Ghép Video")
        # Tab 4: Nén & Chuyển đổi
        tabs.addTab(self._create_compressor_tab(), "🔄 Nén & Chuyển Đổi")
        # Tab 5: Lưu ý quan trọng
        tabs.addTab(self._create_warnings_tab(), "⚠️ Lưu Ý Quan Trọng")

        layout.addWidget(tabs, 1)

        # Footer
        footer = QHBoxLayout()
        lbl_tip = QLabel("💡 Mẹo: Kéo thả file video trực tiếp vào cửa sổ để bắt đầu xử lý nhanh chóng.")
        lbl_tip.setProperty("class", "label-muted")
        footer.addWidget(lbl_tip)
        footer.addStretch()

        btn_close = QPushButton("Đã Hiểu")
        btn_close.setProperty("class", "btn-primary")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)

        layout.addLayout(footer)

    def _create_browser(self, html_content: str) -> QTextBrowser:
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        tokens = ThemeManager.get_instance().get_tokens()
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {tokens["bg_surface"]};
                border: 1px solid {tokens["border"]};
                border-radius: 8px;
                padding: 14px;
                color: {tokens["text_main"]};
                font-size: 12px;
                line-height: 1.6;
            }}
        """)
        css = f"""
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: {tokens["text_main"]}; line-height: 1.6; }}
            h3 {{ color: {tokens["accent"]}; margin-top: 0; font-size: 15px; border-bottom: 1px solid {tokens["border"]}; padding-bottom: 6px; }}
            h4 {{ color: {tokens["text_main"]}; margin-bottom: 4px; font-size: 13px; }}
            p {{ margin-top: 4px; margin-bottom: 10px; }}
            ul, ol {{ margin-top: 4px; margin-bottom: 12px; padding-left: 20px; }}
            li {{ margin-bottom: 6px; }}
            b {{ color: {tokens["text_main"]}; }}
            .badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; background: {tokens["bg_hover"]}; color: {tokens["accent"]}; }}
            .step-box {{ background: {tokens["bg_card"]}; border-left: 3px solid {tokens["accent"]}; padding: 8px 12px; margin-bottom: 10px; border-radius: 0 6px 6px 0; }}
            .warn-box {{ background: {tokens["warning_bg"]}; border-left: 3px solid {tokens["warning"]}; padding: 8px 12px; margin-bottom: 10px; border-radius: 0 6px 6px 0; color: {tokens["warning_text"]}; }}
            .danger-box {{ background: {tokens["danger_bg"]}; border-left: 3px solid {tokens["danger"]}; padding: 8px 12px; margin-bottom: 10px; border-radius: 0 6px 6px 0; color: {tokens["danger_text"]}; }}
            .success-box {{ background: {tokens["success_bg"]}; border-left: 3px solid {tokens["success"]}; padding: 8px 12px; margin-bottom: 10px; border-radius: 0 6px 6px 0; color: {tokens["success_text"]}; }}
            code {{ background: {tokens["bg_hover"]}; padding: 2px 5px; border-radius: 3px; font-family: Consolas, monospace; color: {tokens["accent"]}; font-size: 11px; }}
        </style>
        """
        browser.setHtml(css + html_content)
        return browser

    def _create_quickstart_tab(self) -> QTextBrowser:
        html = """
        <h3>🚀 Hướng Dẫn Bắt Đầu Nhanh Trong 3 Bước</h3>
        <p><b>Media Studio</b> là ứng dụng máy trạm tất cả trong một (All-in-One), chạy độc lập 100% không cần cài thêm Python hay FFmpeg từ bên ngoài.</p>
        
        <div class="step-box">
            <b>Bước 1: Chọn Tính Năng</b><br/>
            Nhấp chuột vào danh mục ở thanh menu bên trái (Sidebar):
            <ul>
                <li><b>📥 Tải Video:</b> Tải video từ YouTube, TikTok không logo, Facebook Reels, Douyin...</li>
                <li><b>✂️ Cắt Video:</b> Cắt ngắn, trích đoạn hoặc tự động chia nhỏ video cho TikTok / Shorts.</li>
                <li><b>🔗 Ghép & Nối:</b> Ghép nối nhiều clip, tự động tương thích kích thước và chèn nhạc nền.</li>
                <li><b>🔄 Nén & Đổi Đuôi:</b> Nén dung lượng chuẩn gửi Zalo (&lt;25MB), Discord (&lt;10MB), đổi MOV sang MP4 trong 2 giây.</li>
            </ul>
        </div>

        <div class="step-box">
            <b>Bước 2: Thiết Lập Tham Số</b><br/>
            Dán đường link hoặc kéo thả file video trực tiếp vào khung ứng dụng. Chọn chất lượng và định dạng mong muốn.
        </div>

        <div class="step-box">
            <b>Bước 3: Nhấn Bắt Đầu & Theo Dõi Tiến Độ</b><br/>
            Bấm nút <b>"Bắt Đầu"</b> hoặc <b>"Thêm vào Hàng Đợi"</b>. Tiến độ xử lý theo thời gian thực (%, FPS, tốc độ) sẽ hiển thị ngay tại bảng <b>Hàng Đợi Tác Vụ</b> bên dưới màn hình. Bạn có thể tạm dừng, hủy hoặc chạy nhiều tác vụ cùng lúc.
        </div>
        """
        return self._create_browser(html)

    def _create_downloader_tab(self) -> QTextBrowser:
        html = """
        <h3>📥 Trình Tải Video Đa Nền Tảng</h3>
        <div class="success-box">
            <b>🌐 Nền tảng được hỗ trợ:</b> YouTube, TikTok (Video không logo / No-Watermark), Facebook (Reels & Watch), Instagram, Twitter/X, Douyin (TikTok Trung Quốc), Bilibili, Vimeo, Soundcloud...
        </div>

        <h4>1. Tải Video TikTok Không Logo (No-Watermark):</h4>
        <ul>
            <li>Hệ thống <b>tự động trích xuất luồng video gốc chất lượng cao nhất</b> từ máy chủ TikTok, hoàn toàn sạch không bị dính logo chìm hay watermark ở cuối clip.</li>
            <li>Hỗ trợ cả link rút gọn <code>vt.tiktok.com/...</code> và link đầy đủ <code>tiktok.com/@user/video/...</code>.</li>
        </ul>

        <h4>2. Tải Video Facebook (Reels & Watch):</h4>
        <ul>
            <li>Dán link bài viết video hoặc link Facebook Reels công khai (Public).</li>
            <li>Hệ thống sẽ tự động ghép luồng hình ảnh độ nét cao HD/1080p và luồng âm thanh tốt nhất.</li>
        </ul>

        <h4>3. Tải Hàng Loạt (Batch Mode) & Playlist:</h4>
        <ul>
            <li>Chuyển sang tab <b>"Tải Hàng Loạt"</b>, dán danh sách link (mỗi dòng một đường link).</li>
            <li>Hỗ trợ tự động nhận diện Playlist YouTube và tải toàn bộ danh sách phát.</li>
        </ul>

        <h4>4. Bắt Link Tự Động Từ Clipboard:</h4>
        <ul>
            <li>Khi tính năng <b>"Bắt link Clipboard"</b> được bật, bạn chỉ cần sao chép (Ctrl+C) link video từ trình duyệt web, ứng dụng sẽ tự động dán và phân tích thông tin ngay lập tức.</li>
        </ul>
        """
        return self._create_browser(html)

    def _create_editing_tab(self) -> QTextBrowser:
        html = """
        <h3>✂️ Cắt Video & 🔗 Ghép Nối Video</h3>

        <h4>1. Trình Cắt Video - Chọn đúng chế độ:</h4>
        <ul>
            <li><b>⚡ Chế độ Cắt Nhanh (Stream Copy):</b> Tốc độ hoàn thành chỉ trong <b>1 - 2 giây</b>! FFmpeg không nén lại dữ liệu, bảo toàn chất lượng gốc 100%. Phù hợp khi bạn cần cắt nhanh đoạn video dài mà không thay đổi độ phân giải.</li>
            <li><b>🎯 Chế độ Cắt Chuẩn Xác (Re-encode):</b> Cắt chính xác đến từng mili-giây (Frame-accurate). Sử dụng card đồ họa GPU rời để nén lại nhanh chóng.</li>
            <li><b>📱 Tự Động Chia Nhỏ (Auto-split):</b> Tự động cắt một video dài thành các clip 60 giây, 90 giây hoặc 3 phút để đăng tải lên TikTok, YouTube Shorts và Facebook Reels.</li>
        </ul>

        <h4>2. Ghép & Nối Video Đa Định Dạng:</h4>
        <ul>
            <li><b>Tự động kiểm tra độ tương thích:</b> Nếu các video có cùng kích thước, cùng FPS và chuẩn nén, ứng dụng sẽ ghép siêu tốc (Copy Mode).</li>
            <li><b>Tự động bù viền (Letterbox):</b> Nếu bạn ghép các video khác kích thước (ví dụ 1 video ngang và 1 video dọc), ứng dụng tự động cân chỉnh thêm viền đen sang trọng để video không bị méo hình.</li>
            <li><b>Lồng nhạc nền (BGM):</b> Hỗ trợ chọn file nhạc MP3 làm nhạc nền, tự động lặp lại nếu video dài hơn nhạc và kiểm soát âm lượng tách biệt giữa tiếng gốc và nhạc nền.</li>
        </ul>
        """
        return self._create_browser(html)

    def _create_compressor_tab(self) -> QTextBrowser:
        html = """
        <h3>🔄 Nén Dung Lượng & Chuyển Đổi Định Dạng</h3>

        <h4>1. Bộ Preset Nén Nhanh Cho Mạng Xã Hội:</h4>
        <ul>
            <li><b>💬 Nén cho Zalo (&lt; 25MB):</b> Zalo giới hạn kích thước file gửi trực tiếp là 25MB. Chế độ này tự động tính toán bitrate thông minh để nén video xuống dưới 24MB, gửi mượt mà không lo bị báo lỗi dung lượng.</li>
            <li><b>🎮 Nén cho Discord (&lt; 10MB):</b> Tối ưu dung lượng cho tài khoản Discord tiêu chuẩn không Nitro.</li>
            <li><b>📧 Nén gửi Email / Web (&lt; 50MB):</b> Thu nhỏ kích thước tối đa mà vẫn giữ được độ nét rõ ràng.</li>
        </ul>

        <h4>2. Remux Siêu Tốc (MOV sang MP4):</h4>
        <ul>
            <li>Các thiết bị iPhone / iPad thường quay video định dạng <code>.MOV</code>.</li>
            <li>Thay vì mất 5 - 10 phút render lại, tính năng <b>Remux</b> chỉ trích xuất và đóng gói lại vùng chứa (container) sang <code>.MP4</code> trong vòng <b>2 giây</b>, không suy hao chất lượng.</li>
        </ul>

        <h4>3. Trích Xuất Âm Thanh Sang MP3:</h4>
        <ul>
            <li>Chuyển đổi bất kỳ file video nào sang file âm thanh MP3 (192kbps hoặc 320kbps chất lượng cao) để nghe nhạc hoặc làm tư liệu lồng tiếng.</li>
        </ul>
        """
        return self._create_browser(html)

    def _create_warnings_tab(self) -> QTextBrowser:
        html = """
        <h3>⚠️ Lưu Ý Quan Trọng Cần Tránh Khi Sử Dụng</h3>

        <div class="danger-box">
            <b>1. Tránh Tải Dồn Dập Quá Nhanh (Tránh Bị Chặn IP / Bot Detection):</b><br/>
            YouTube và các nền tảng mạng xã hội có cơ chế chống bot tự động. Nếu bạn gửi hàng chục yêu cầu tải liên tục trong vài giây từ cùng 1 địa chỉ IP, server có thể trả về lỗi <code>HTTP 429 Too Many Requests</code> hoặc yêu cầu đăng nhập.<br/>
            <b>Khắc phục:</b> Hãy tải từng video hoặc chia danh sách hàng loạt thành các đợt nhỏ; trong trường hợp bị chặn tạm thời, hãy đợi 10 - 15 phút hoặc chuyển sang kết nối mạng khác (như 4G).
        </div>

        <div class="warn-box">
            <b>2. Video Riêng Tư & Video Nhóm Kín:</b><br/>
            Ứng dụng hỗ trợ tải các video được đăng tải ở chế độ <b>Công Khai (Public)</b>. Các video trong Group kín Facebook, video cần trả phí hoặc video bị khóa quyền riêng tư sẽ không thể tải được nếu không có quyền truy cập trực tiếp.
        </div>

        <div class="warn-box">
            <b>3. Hiện Tượng Khựng Hình Ở Đầu Khi Cắt Nhanh (Stream Copy):</b><br/>
            Chế độ Cắt nhanh (Stream Copy <code>-c copy</code>) chỉ có thể cắt tại các khung hình khóa chính (Keyframe / I-frame). Nếu điểm bắt đầu cắt không trùng với Keyframe, 0.5 giây đầu của video có thể xuất hiện hiện tượng đứng hình trước khi chạy tiếp.<br/>
            <b>Khắc phục:</b> Nếu bạn cần độ chuẩn xác tuyệt đối đến từng khung hình, hãy tick chọn chế độ <b>"Mã hóa lại (Re-encode)"</b>.
        </div>

        <div class="warn-box">
            <b>4. Kiểm Tra Dung Lượng Ổ Cứng Khả Dụng:</b><br/>
            Khi tải video 4K hoặc ghép nối các tập tin video có thời lượng dài, tệp tạm thời và file thành phẩm có thể chiếm dung lượng lớn. Hãy đảm bảo ổ cứng lưu trữ còn <b>tối thiểu 5GB - 10GB dung lượng trống</b> để quá trình render không bị gián đoạn giữa chừng.
        </div>

        <div class="step-box">
            <b>5. Tuân Thủ Bản Quyền Nội Dung:</b><br/>
            Hãy luôn tôn trọng quyền tác giả và quyền sở hữu trí tuệ của người sáng tạo nội dung. Chỉ tải và sử dụng các tài liệu bạn có quyền hợp pháp hoặc phục vụ mục đích học tập, lưu trữ cá nhân phi thương mại.
        </div>
        """
        return self._create_browser(html)

