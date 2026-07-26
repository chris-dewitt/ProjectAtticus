"""SQLite persistence for run traces."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_correlation_id, get_telemetry
from atticus.traces.models import SpanKind, TraceSpan


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _new_id() -> str:
    return f"span_{uuid.uuid4().hex}"


class TraceNotFound(AtticusError):
    code = "trace_not_found"
    status_code = 404


class TraceStore:
    """Local SQLite store for trace spans keyed by run_id."""

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
            CREATE TABLE IF NOT EXISTS trace_spans (
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              name TEXT NOT NULL,
              kind TEXT NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT,
              status TEXT NOT NULL,
              parent_span_id TEXT,
              correlation_id TEXT,
              attributes_json TEXT NOT NULL,
              events_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trace_spans_run
              ON trace_spans (run_id, started_at);
            """
        )
        self._conn.commit()

    def start_span(
        self,
        *,
        run_id: str,
        name: str,
        kind: SpanKind | str,
        attributes: dict[str, Any] | None = None,
        parent_span_id: str | None = None,
        correlation_id: str | None = None,
    ) -> TraceSpan:
        span = TraceSpan(
            id=_new_id(),
            run_id=run_id,
            name=name,
            kind=SpanKind(kind) if not isinstance(kind, SpanKind) else kind,
            started_at=_utc_now(),
            parent_span_id=parent_span_id,
            correlation_id=correlation_id or get_correlation_id(),
            attributes=get_telemetry().redact(attributes or {}),
        )
        self._conn.execute(
            """
            INSERT INTO trace_spans (
              id, run_id, name, kind, started_at, ended_at, status,
              parent_span_id, correlation_id, attributes_json, events_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.id,
                span.run_id,
                span.name,
                span.kind.value,
                span.started_at,
                None,
                span.status,
                span.parent_span_id,
                span.correlation_id,
                json.dumps(span.attributes),
                json.dumps(span.events),
            ),
        )
        self._conn.commit()
        get_telemetry().emit(
            "trace.span_started",
            span_id=span.id,
            run_id=run_id,
            span_name=name,
            kind=span.kind.value,
        )
        return span

    def end_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        attributes: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
    ) -> TraceSpan:
        span = self.get_span(span_id)
        if attributes:
            span.attributes.update(get_telemetry().redact(attributes))
        if event:
            span.events.append(get_telemetry().redact(event))
        span.status = status
        span.ended_at = _utc_now()
        self._conn.execute(
            """
            UPDATE trace_spans
            SET ended_at = ?, status = ?, attributes_json = ?, events_json = ?
            WHERE id = ?
            """,
            (
                span.ended_at,
                span.status,
                json.dumps(span.attributes),
                json.dumps(span.events),
                span.id,
            ),
        )
        self._conn.commit()
        get_telemetry().emit(
            "trace.span_ended",
            span_id=span.id,
            run_id=span.run_id,
            status=status,
        )
        return span

    def add_event(self, span_id: str, event: dict[str, Any]) -> TraceSpan:
        span = self.get_span(span_id)
        span.events.append(get_telemetry().redact(event))
        self._conn.execute(
            "UPDATE trace_spans SET events_json = ? WHERE id = ?",
            (json.dumps(span.events), span.id),
        )
        self._conn.commit()
        return span

    def get_span(self, span_id: str) -> TraceSpan:
        row = self._conn.execute(
            "SELECT * FROM trace_spans WHERE id = ?",
            (span_id,),
        ).fetchone()
        if row is None:
            raise TraceNotFound(f"Span not found: {span_id}")
        return self._row_to_span(row)

    def list_spans(self, run_id: str) -> list[TraceSpan]:
        rows = self._conn.execute(
            """
            SELECT * FROM trace_spans
            WHERE run_id = ?
            ORDER BY started_at ASC, rowid ASC
            """,
            (run_id,),
        ).fetchall()
        return [self._row_to_span(row) for row in rows]

    def get_trace(self, run_id: str) -> dict[str, Any]:
        spans = self.list_spans(run_id)
        if not spans:
            raise TraceNotFound(f"No trace spans for run: {run_id}")
        return {
            "run_id": run_id,
            "span_count": len(spans),
            "spans": [s.to_public_dict() for s in spans],
        }

    def _row_to_span(self, row: sqlite3.Row) -> TraceSpan:
        return TraceSpan(
            id=row["id"],
            run_id=row["run_id"],
            name=row["name"],
            kind=SpanKind(row["kind"]),
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            parent_span_id=row["parent_span_id"],
            correlation_id=row["correlation_id"],
            attributes=json.loads(row["attributes_json"] or "{}"),
            events=json.loads(row["events_json"] or "[]"),
        )
