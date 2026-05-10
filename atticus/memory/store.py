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
    confidence: float = 1.0


@dataclass(frozen=True)
class Preference:
    id: int
    key: str
    value: str
    source: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ConversationSummary:
    id: int
    summary: str
    mode: str | None
    provider: str | None
    created_at: str


@dataclass(frozen=True)
class ToolApprovalRow:
    id: int
    tool_name: str
    permission_class: str
    action_summary: str
    approved: bool
    created_at: str


class MemoryStore:
    """SQLite-backed preferences, notes, summaries, and tool audit entries."""

    def __init__(self, sqlite_path: Path) -> None:
        self._path = sqlite_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _migrate_memory_items(self) -> None:
        cols = {str(r[1]) for r in self._conn.execute("PRAGMA table_info(memory_items)").fetchall()}
        if "confidence" not in cols:
            self._conn.execute("ALTER TABLE memory_items ADD COLUMN confidence REAL NOT NULL DEFAULT 1.0")

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL DEFAULT 'note',
              content TEXT NOT NULL,
              tags TEXT,
              confidence REAL NOT NULL DEFAULT 1.0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_memory_items_active
              ON memory_items (deleted_at);

            CREATE TABLE IF NOT EXISTS preferences (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              key TEXT NOT NULL UNIQUE,
              value TEXT NOT NULL,
              source TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation_summaries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              summary TEXT NOT NULL,
              mode TEXT,
              provider TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tool_approvals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tool_name TEXT NOT NULL,
              permission_class TEXT NOT NULL,
              action_summary TEXT NOT NULL,
              approved INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tool_approvals_created
              ON tool_approvals (created_at);
            """
        )
        self._migrate_memory_items()
        self._conn.commit()

    # --- memory_items -------------------------------------------------
    def add_item(self, content: str, *, kind: str = "note", tags: str | None = None, confidence: float = 1.0) -> int:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO memory_items (kind, content, tags, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, content, tags, confidence, now, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_items(self, *, limit: int = 50) -> Sequence[MemoryItem]:
        rows = self._conn.execute(
            """
            SELECT id, kind, content, created_at, confidence
            FROM memory_items
            WHERE deleted_at IS NULL
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            MemoryItem(
                id=int(r["id"]),
                kind=str(r["kind"]),
                content=str(r["content"]),
                created_at=str(r["created_at"]),
                confidence=float(r["confidence"]),
            )
            for r in rows
        )

    def search_items(self, query: str, *, limit: int = 20) -> Sequence[MemoryItem]:
        q = f"%{query.strip()}%"
        rows = self._conn.execute(
            """
            SELECT id, kind, content, created_at, confidence
            FROM memory_items
            WHERE deleted_at IS NULL AND (content LIKE ? OR IFNULL(tags, '') LIKE ?)
            ORDER BY id DESC
            LIMIT ?
            """,
            (q, q, limit),
        ).fetchall()
        return tuple(
            MemoryItem(
                id=int(r["id"]),
                kind=str(r["kind"]),
                content=str(r["content"]),
                created_at=str(r["created_at"]),
                confidence=float(r["confidence"]),
            )
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

    def forget_items_matching(self, substring: str) -> int:
        """Soft-delete items whose content or tags contains substring (case-insensitive)."""
        now = _utc_now()
        q = f"%{substring.strip()}%"
        cur = self._conn.execute(
            """
            UPDATE memory_items
            SET deleted_at = ?, updated_at = ?
            WHERE deleted_at IS NULL AND (LOWER(content) LIKE LOWER(?) OR LOWER(IFNULL(tags, '')) LIKE LOWER(?))
            """,
            (now, now, q, q),
        )
        self._conn.commit()
        return cur.rowcount

    # --- preferences --------------------------------------------------
    def upsert_preference(self, key: str, value: str, *, source: str | None = "cli") -> None:
        now = _utc_now()
        self._conn.execute(
            """
            INSERT INTO preferences (key, value, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              source = excluded.source,
              updated_at = excluded.updated_at
            """,
            (key, value, source, now, now),
        )
        self._conn.commit()

    def get_preference(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key = ?",
            (key,),
        ).fetchone()
        return None if row is None else str(row["value"])

    def list_preferences(self, *, limit: int = 100) -> Sequence[Preference]:
        rows = self._conn.execute(
            """
            SELECT id, key, value, source, created_at, updated_at
            FROM preferences
            ORDER BY key ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            Preference(
                id=int(r["id"]),
                key=str(r["key"]),
                value=str(r["value"]),
                source=str(r["source"]) if r["source"] is not None else None,
                created_at=str(r["created_at"]),
                updated_at=str(r["updated_at"]),
            )
            for r in rows
        )

    def delete_preference(self, key: str) -> bool:
        cur = self._conn.execute("DELETE FROM preferences WHERE key = ?", (key,))
        self._conn.commit()
        return cur.rowcount > 0

    # --- conversation summaries --------------------------------------
    def add_conversation_summary(self, summary: str, *, mode: str | None, provider: str | None) -> int:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO conversation_summaries (summary, mode, provider, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (summary, mode, provider, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_summaries(self, *, limit: int = 30) -> Sequence[ConversationSummary]:
        rows = self._conn.execute(
            """
            SELECT id, summary, mode, provider, created_at
            FROM conversation_summaries
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            ConversationSummary(
                id=int(r["id"]),
                summary=str(r["summary"]),
                mode=str(r["mode"]) if r["mode"] is not None else None,
                provider=str(r["provider"]) if r["provider"] is not None else None,
                created_at=str(r["created_at"]),
            )
            for r in rows
        )

    def forget_summary_id(self, summary_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM conversation_summaries WHERE id = ?", (summary_id,))
        self._conn.commit()
        return cur.rowcount > 0

    # --- audit --------------------------------------------------------
    def record_tool_approval(
        self,
        *,
        tool_name: str,
        permission_class: str,
        action_summary: str,
        approved: bool,
    ) -> int:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO tool_approvals (tool_name, permission_class, action_summary, approved, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tool_name, permission_class, action_summary, 1 if approved else 0, now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def count_active_items(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(1) AS c FROM memory_items WHERE deleted_at IS NULL",
        ).fetchone()
        return int(row["c"])

    def count_preferences(self) -> int:
        row = self._conn.execute("SELECT COUNT(1) AS c FROM preferences").fetchone()
        return int(row["c"])

    def count_summaries(self) -> int:
        row = self._conn.execute("SELECT COUNT(1) AS c FROM conversation_summaries").fetchone()
        return int(row["c"])

    def count_tool_approvals(self) -> int:
        row = self._conn.execute("SELECT COUNT(1) AS c FROM tool_approvals").fetchone()
        return int(row["c"])

    def list_tool_approvals(self, *, limit: int = 30) -> Sequence[ToolApprovalRow]:
        rows = self._conn.execute(
            """
            SELECT id, tool_name, permission_class, action_summary, approved, created_at
            FROM tool_approvals
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return tuple(
            ToolApprovalRow(
                id=int(r["id"]),
                tool_name=str(r["tool_name"]),
                permission_class=str(r["permission_class"]),
                action_summary=str(r["action_summary"]),
                approved=bool(r["approved"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        )
