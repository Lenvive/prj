"""SQLite persistence for files, receivers, and download logs."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pylocalsend.core.utils.config import APP_DIR


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path | None = None) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path or (APP_DIR / "pylocalsend.db")
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    is_dir INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ready'
                );
                CREATE TABLE IF NOT EXISTS receivers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pin TEXT NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS download_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    receiver_id TEXT,
                    downloader TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    bytes_sent INTEGER DEFAULT 0,
                    FOREIGN KEY (file_id) REFERENCES files(id)
                );
                CREATE TABLE IF NOT EXISTS download_grants (
                    file_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    PRIMARY KEY (file_id, relative_path),
                    FOREIGN KEY (file_id) REFERENCES files(id)
                );
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            backfill = conn.execute(
                "SELECT 1 FROM schema_meta WHERE key = 'grants_backfill'"
            ).fetchone()
            if backfill is None:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO download_grants (file_id, relative_path)
                    SELECT id, '' FROM files
                    WHERE id NOT IN (SELECT file_id FROM download_grants)
                    """
                )
                conn.execute(
                    "INSERT INTO schema_meta (key, value) VALUES ('grants_backfill', '1')"
                )

    def add_file(
        self,
        file_id: str,
        path: str,
        name: str,
        is_dir: bool,
        size: int,
        mtime: float,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO files
                (id, path, name, is_dir, size, mtime, uploaded_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ready')
                """,
                (file_id, path, name, int(is_dir), size, mtime, _utcnow()),
            )
            conn.execute(
                "DELETE FROM download_grants WHERE file_id = ?",
                (file_id,),
            )
            conn.execute(
                "INSERT INTO download_grants (file_id, relative_path) VALUES (?, '')",
                (file_id,),
            )

    def remove_file_by_path(self, path: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM files WHERE path = ?", (path,))
            return cur.rowcount > 0

    def remove_file_by_id(self, file_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM download_grants WHERE file_id = ?", (file_id,))
            cur = conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            return cur.rowcount > 0

    def list_files(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM files ORDER BY uploaded_at DESC").fetchall()
        return [dict(r) for r in rows]

    def get_file(self, file_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        return dict(row) if row else None

    def get_file_by_path(self, path: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
        return dict(row) if row else None

    def add_receiver(
        self, receiver_id: str, name: str, pin: str, token: str
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO receivers (id, name, pin, token, status, created_at)
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (receiver_id, name, pin, token, _utcnow()),
            )

    def disable_receiver(self, receiver_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE receivers SET status = 'disabled'
                WHERE id = ? AND status = 'active'
                """,
                (receiver_id,),
            )
            return cur.rowcount > 0

    def enable_receiver(self, receiver_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE receivers SET status = 'active'
                WHERE id = ? AND status = 'disabled'
                """,
                (receiver_id,),
            )
            return cur.rowcount > 0

    def remove_receiver(self, receiver_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE receivers SET status = 'removed' WHERE id = ?", (receiver_id,)
            )
            if cur.rowcount:
                return True
            cur = conn.execute("DELETE FROM receivers WHERE id = ?", (receiver_id,))
            return cur.rowcount > 0

    def list_receivers(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM receivers WHERE status != 'removed' ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_receiver(self, receiver_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM receivers WHERE id = ?", (receiver_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_receiver_by_token(self, token: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM receivers
                WHERE token = ? AND status IN ('active', 'disabled')
                """,
                (token,),
            ).fetchone()
        return dict(row) if row else None

    def log_download_start(
        self,
        file_id: str,
        downloader: str,
        receiver_id: str | None = None,
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO download_logs
                (file_id, receiver_id, downloader, started_at, status, bytes_sent)
                VALUES (?, ?, ?, ?, 'in_progress', 0)
                """,
                (file_id, receiver_id, downloader, _utcnow()),
            )
            return int(cur.lastrowid)

    def log_download_finish(
        self, log_id: int, status: str, bytes_sent: int
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE download_logs
                SET finished_at = ?, status = ?, bytes_sent = ?
                WHERE id = ?
                """,
                (_utcnow(), status, bytes_sent, log_id),
            )

    def list_downloads_for_file(self, file_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM download_logs WHERE file_id = ? ORDER BY started_at DESC",
                (file_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_download_grants(self, file_id: str) -> set[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT relative_path FROM download_grants WHERE file_id = ?",
                (file_id,),
            ).fetchall()
        return {str(row["relative_path"]) for row in rows}

    def set_download_grants(self, file_id: str, relative_paths: set[str]) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM download_grants WHERE file_id = ?", (file_id,))
            for path in relative_paths:
                conn.execute(
                    "INSERT INTO download_grants (file_id, relative_path) VALUES (?, ?)",
                    (file_id, path),
                )

    def has_download_grants(self, file_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM download_grants WHERE file_id = ? LIMIT 1",
                (file_id,),
            ).fetchone()
        return row is not None

    def get_download_catalog_version(self) -> str:
        with self._conn() as conn:
            grant_rows = conn.execute(
                """
                SELECT file_id, relative_path
                FROM download_grants
                ORDER BY file_id, relative_path
                """
            ).fetchall()
            file_rows = conn.execute(
                "SELECT id, name, size, mtime FROM files ORDER BY id"
            ).fetchall()
        payload = repr([tuple(row) for row in grant_rows]) + repr([tuple(row) for row in file_rows])
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def list_downloads_for_receiver(self, receiver_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT dl.*, f.name AS file_name
                FROM download_logs dl
                LEFT JOIN files f ON f.id = dl.file_id
                WHERE dl.receiver_id = ?
                ORDER BY dl.started_at DESC
                """,
                (receiver_id,),
            ).fetchall()
        return [dict(r) for r in rows]
