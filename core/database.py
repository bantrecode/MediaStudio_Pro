"""
Database Core Module
Quản lý cơ sở dữ liệu SQLite lưu trữ lịch sử tác vụ và danh sách link đã tải (chống trùng lặp).
Vị trí: %APPDATA%\\MediaStudio\\history.db.
TUYỆT ĐỐI KHÔNG IMPORT PYSIDE6.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.system import get_appdata_dir


class HistoryDB:
    _instance = None

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_appdata_dir() / "history.db"
        self._init_tables()

    @classmethod
    def get_instance(cls) -> "HistoryDB":
        if cls._instance is None:
            cls._instance = HistoryDB()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Khởi tạo cấu trúc các bảng dữ liệu và quản lý version schema."""
        CURRENT_DB_VERSION = 1

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version")
            current_ver = cursor.fetchone()[0]

            if current_ver < 1:
                # Bảng lưu lịch sử tác vụ
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS jobs_history (
                        id TEXT PRIMARY KEY,
                        module_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        finished_at TEXT,
                        error_message TEXT,
                        output_path TEXT
                    )
                """)
                # Bảng lưu trữ link đã tải để chống tải trùng
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS downloaded_urls (
                        url TEXT PRIMARY KEY,
                        title TEXT,
                        downloaded_at TEXT NOT NULL
                    )
                """)
                cursor.execute(f"PRAGMA user_version = {CURRENT_DB_VERSION}")
                conn.commit()

    def record_job(self, job_id: str, module_id: str, name: str, status: str, output_path: str = ""):
        """Ghi nhận một job mới."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO jobs_history
                (id, module_id, name, status, created_at, output_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job_id, module_id, name, status, now, output_path))
            conn.commit()

    def update_job_status(self, job_id: str, status: str, error_message: str = "", output_path: str = ""):
        """Cập nhật trạng thái kết thúc của job."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs_history
                SET status = ?, finished_at = ?, error_message = ?,
                    output_path = CASE WHEN ? != '' THEN ? ELSE output_path END
                WHERE id = ?
            """, (status, now, error_message, output_path, output_path, job_id))
            conn.commit()

    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lấy danh sách các job gần nhất."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM jobs_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def record_downloaded_url(self, url: str, title: str):
        """Lưu vết đường link đã tải thành công."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO downloaded_urls (url, title, downloaded_at)
                VALUES (?, ?, ?)
            """, (url.strip(), title.strip(), now))
            conn.commit()

    def is_url_downloaded(self, url: str) -> bool:
        """Kiểm tra xem link này đã từng được tải thành công chưa."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM downloaded_urls WHERE url = ?", (url.strip(),))
            return cursor.fetchone() is not None

    def clear_history(self):
        """Xóa sạch lịch sử job và cache link."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs_history")
            cursor.execute("DELETE FROM downloaded_urls")
            conn.commit()

