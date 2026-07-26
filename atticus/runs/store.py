"""SQLite persistence for Track B conversations and bounded runs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atticus.core.errors import AtticusError
from atticus.runs.models import (
    CheckpointRecord,
    ConversationRecord,
    MessageRecord,
    MessageRole,
    RunRecord,
    RunStatus,
)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class RunNotFound(AtticusError):
    code = "run_not_found"
    status_code = 404


class ConversationNotFound(AtticusError):
    code = "conversation_not_found"
    status_code = 404


class RunStore:
    """Local SQLite store for conversations, messages, and runs."""

    def __init__(self, sqlite_path: Path) -> None:
        self._path = sqlite_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
              id TEXT PRIMARY KEY,
              title TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
              ON messages (conversation_id, created_at);

            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              status TEXT NOT NULL,
              provider TEXT NOT NULL,
              mode TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              input_messages_json TEXT NOT NULL,
              output_text TEXT,
              error_code TEXT,
              error_message TEXT,
              cancel_requested INTEGER NOT NULL DEFAULT 0,
              checkpoints_json TEXT NOT NULL DEFAULT '[]',
              correlation_id TEXT,
              idempotency_key TEXT UNIQUE,
              FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_runs_conversation
              ON runs (conversation_id, created_at);
            """
        )
        self._conn.commit()

    def create_conversation(self, *, title: str | None = None) -> ConversationRecord:
        now = _utc_now()
        record = ConversationRecord(
            id=_new_id("conv"),
            created_at=now,
            updated_at=now,
            title=title,
        )
        self._conn.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (record.id, record.title, record.created_at, record.updated_at),
        )
        self._conn.commit()
        return record

    def get_conversation(self, conversation_id: str) -> ConversationRecord:
        row = self._conn.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            raise ConversationNotFound(
                f"Conversation not found: {conversation_id}",
                safe_details={"conversation_id": conversation_id},
            )
        return ConversationRecord(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_message(
        self,
        conversation_id: str,
        *,
        role: MessageRole,
        content: str,
    ) -> MessageRecord:
        self.get_conversation(conversation_id)
        now = _utc_now()
        record = MessageRecord(
            id=_new_id("msg"),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
        )
        self._conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (record.id, record.conversation_id, record.role, record.content, record.created_at),
        )
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        self._conn.commit()
        return record

    def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        self.get_conversation(conversation_id)
        rows = self._conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (conversation_id,),
        ).fetchall()
        return [
            MessageRecord(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],  # type: ignore[arg-type]
                content=row["content"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_run(
        self,
        *,
        conversation_id: str,
        provider: str,
        mode: str,
        input_messages: list[dict[str, str]],
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> RunRecord:
        self.get_conversation(conversation_id)
        if idempotency_key:
            existing = self.get_run_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing
        now = _utc_now()
        record = RunRecord(
            id=_new_id("run"),
            conversation_id=conversation_id,
            status=RunStatus.QUEUED,
            provider=provider,
            mode=mode,
            created_at=now,
            updated_at=now,
            input_messages=list(input_messages),
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            checkpoints=[CheckpointRecord(name="queued", at=now, detail={})],
        )
        self._insert_run(record)
        return record

    def get_run_by_idempotency_key(self, key: str) -> RunRecord | None:
        row = self._conn.execute(
            "SELECT id FROM runs WHERE idempotency_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return self.get_run(row["id"])

    def get_run(self, run_id: str) -> RunRecord:
        row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise RunNotFound(
                f"Run not found: {run_id}",
                safe_details={"run_id": run_id},
            )
        return self._row_to_run(row)

    def save_run(self, run: RunRecord) -> RunRecord:
        run.updated_at = _utc_now()
        self._conn.execute(
            """
            UPDATE runs SET
              status = ?,
              provider = ?,
              mode = ?,
              updated_at = ?,
              input_messages_json = ?,
              output_text = ?,
              error_code = ?,
              error_message = ?,
              cancel_requested = ?,
              checkpoints_json = ?,
              correlation_id = ?
            WHERE id = ?
            """,
            (
                run.status.value,
                run.provider,
                run.mode,
                run.updated_at,
                json.dumps(run.input_messages),
                run.output_text,
                run.error_code,
                run.error_message,
                1 if run.cancel_requested else 0,
                json.dumps(
                    [{"name": c.name, "at": c.at, "detail": c.detail} for c in run.checkpoints]
                ),
                run.correlation_id,
                run.id,
            ),
        )
        self._conn.commit()
        return run

    def _insert_run(self, run: RunRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO runs (
              id, conversation_id, status, provider, mode, created_at, updated_at,
              input_messages_json, output_text, error_code, error_message,
              cancel_requested, checkpoints_json, correlation_id, idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.id,
                run.conversation_id,
                run.status.value,
                run.provider,
                run.mode,
                run.created_at,
                run.updated_at,
                json.dumps(run.input_messages),
                run.output_text,
                run.error_code,
                run.error_message,
                1 if run.cancel_requested else 0,
                json.dumps(
                    [{"name": c.name, "at": c.at, "detail": c.detail} for c in run.checkpoints]
                ),
                run.correlation_id,
                run.idempotency_key,
            ),
        )
        self._conn.commit()

    def _row_to_run(self, row: sqlite3.Row) -> RunRecord:
        checkpoints_raw: list[dict[str, Any]] = json.loads(row["checkpoints_json"] or "[]")
        return RunRecord(
            id=row["id"],
            conversation_id=row["conversation_id"],
            status=RunStatus(row["status"]),
            provider=row["provider"],
            mode=row["mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            input_messages=list(json.loads(row["input_messages_json"] or "[]")),
            output_text=row["output_text"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            cancel_requested=bool(row["cancel_requested"]),
            checkpoints=[
                CheckpointRecord(
                    name=str(item.get("name", "")),
                    at=str(item.get("at", "")),
                    detail=dict(item.get("detail") or {}),
                )
                for item in checkpoints_raw
            ],
            correlation_id=row["correlation_id"],
            idempotency_key=row["idempotency_key"],
        )
