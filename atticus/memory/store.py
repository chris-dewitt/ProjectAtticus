from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True)
class MemoryItem:
    id: int
    kind: str
    content: str
    created_at: str


class MemoryStore:
    """SQLite-backed durable notes (not raw chat transcripts)."""

    def __init__(self, sqlite_path: Path) -> None:
        self._path = sqlite_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL DEFAULT 'note',
              content TEXT NOT NULL,
              tags TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memory_items_active
              ON memory_items (deleted_at);
            """
        )
        self._conn.commit()

    def add_item(self, content: str, *, kind: str = "note", tags: str | None = None) -> int:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO memory_items (kind, content, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (kind, content, tags, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_items(self, *, limit: int = 50) -> Sequence[MemoryItem]:
        rows = self._conn.execute(
            """
            SELECT id, kind, content, created_at
            FROM memory_items
            WHERE deleted_at IS NULL
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            MemoryItem(id=int(r["id"]), kind=str(r["kind"]), content=str(r["content"]), created_at=str(r["created_at"]))
            for r in rows
        )

    def forget_id(self, item_id: int) -> bool:
        now = _utc_now()
        cur = self._conn.execute(
            """
            UPDATE memory_items
            SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (now, now, item_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def forget_all(self) -> int:
        now = _utc_now()
        cur = self._conn.execute(
            """
            UPDATE memory_items
            SET deleted_at = ?, updated_at = ?
            WHERE deleted_at IS NULL
            """,
            (now, now),
        )
        self._conn.commit()
        return cur.rowcount
