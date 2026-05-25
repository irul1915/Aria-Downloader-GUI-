import sqlite3
import os
from utils.logger import log

class DBManager:
    def __init__(self, db_name="database/history.db"):
        os.makedirs(os.path.dirname(db_name), exist_ok=True)
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    gid TEXT PRIMARY KEY,
                    filename TEXT,
                    url TEXT,
                    save_path TEXT,
                    status TEXT,
                    total_size INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
        except Exception as e:
            log.error(f"DB Error: {str(e)}")

    def save_download(self, gid: str, filename: str, url: str, save_path: str):
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO downloads (gid, filename, url, save_path, status) VALUES (?, ?, ?, ?, 'added')",
                (gid, filename, url, save_path)
            )
            self.conn.commit()
        except Exception as e:
            log.error(f"Failed to save download: {str(e)}")