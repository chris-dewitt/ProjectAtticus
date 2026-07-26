"""Telemetry hooks with optional OTLP-shaped JSON file / stderr exporter.

Emits structured, privacy-preserving events to an in-process sink and optional
exporters. Secrets and common credential field names are redacted.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

_correlation_id: ContextVar[str | None] = ContextVar("atticus_correlation_id", default=None)

DEFAULT_REDACT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "client_secret",
        "openai_api_key",
        "anthropic_api_key",
        "gemini_api_key",
        "github_token",
    }
)


@dataclass
class TelemetryEvent:
    """One structured telemetry event."""

    name: str
    timestamp: str
    correlation_id: str | None
    service_name: str
    environment: str
    attributes: dict[str, Any] = field(default_factory=dict)


class Telemetry:
    """In-process telemetry recorder with optional stderr/file JSON emission."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        service_name: str = "project-atticus",
        environment: str = "local",
        emit_stderr: bool = False,
        otel_exporter: str = "none",
        otel_file_path: str | Path | None = None,
        redact_keys: frozenset[str] | set[str] | None = None,
        max_events: int = 500,
    ) -> None:
        self.enabled = enabled
        self.service_name = service_name
        self.environment = environment
        self.emit_stderr = emit_stderr
        self.otel_exporter = (otel_exporter or "none").lower()
        self.otel_file_path = Path(otel_file_path) if otel_file_path else Path("data/telemetry/otel.jsonl")
        self.redact_keys = frozenset(k.lower() for k in (redact_keys or DEFAULT_REDACT_KEYS))
        self.max_events = max_events
        self._events: list[TelemetryEvent] = []

    def clear(self) -> None:
        self._events.clear()

    @property
    def events(self) -> list[TelemetryEvent]:
        return list(self._events)

    def emit(self, name: str, **attributes: Any) -> TelemetryEvent | None:
        if not self.enabled:
            return None
        event = TelemetryEvent(
            name=name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=get_correlation_id(),
            service_name=self.service_name,
            environment=self.environment,
            attributes=self.redact(attributes),
        )
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events :]
        payload = event_to_dict(event)
        if self.emit_stderr or self.otel_exporter == "stderr":
            sys.stderr.write(json.dumps(payload, default=str) + "\n")
        if self.otel_exporter == "file":
            self._export_file(payload)
        return event

    def _export_file(self, payload: dict[str, Any]) -> None:
        """Write an OTel-inspired JSON log record (no secrets)."""
        try:
            self.otel_file_path.parent.mkdir(parents=True, exist_ok=True)
            otel_record = {
                "resource": {
                    "service.name": self.service_name,
                    "deployment.environment": self.environment,
                },
                "body": payload.get("name"),
                "timestamp": payload.get("timestamp"),
                "trace_id": payload.get("correlation_id"),
                "attributes": payload.get("attributes") or {},
            }
            with self.otel_file_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(otel_record, default=str) + "\n")
        except OSError:
            # Telemetry must never break request paths.
            return

    def redact(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            out: dict[str, Any] = {}
            for key, item in value.items():
                if str(key).lower() in self.redact_keys or _looks_secret_key(str(key)):
                    out[str(key)] = "[redacted]"
                else:
                    out[str(key)] = self.redact(item)
            return out
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)
        return value

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[dict[str, Any]]:
        """Context manager that records duration_ms for a named span."""
        started = time.perf_counter()
        bag: dict[str, Any] = dict(attributes)
        try:
            yield bag
        finally:
            bag["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
            self.emit(name, **bag)


_default_telemetry = Telemetry(
    enabled=os.environ.get("ATTICUS_TELEMETRY", "1") not in {"0", "false", "False"},
    emit_stderr=os.environ.get("ATTICUS_TELEMETRY_STDERR", "0") in {"1", "true", "True"},
)


def get_telemetry() -> Telemetry:
    return _default_telemetry


def set_telemetry(telemetry: Telemetry) -> None:
    global _default_telemetry
    _default_telemetry = telemetry


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None) -> None:
    _correlation_id.set(correlation_id)


@contextmanager
def bind_correlation_id(correlation_id: str | None = None) -> Iterator[str]:
    token = _correlation_id.set(correlation_id or new_correlation_id())
    try:
        current = _correlation_id.get()
        assert current is not None
        yield current
    finally:
        _correlation_id.reset(token)


def event_to_dict(event: TelemetryEvent) -> dict[str, Any]:
    return {
        "name": event.name,
        "timestamp": event.timestamp,
        "correlation_id": event.correlation_id,
        "service_name": event.service_name,
        "environment": event.environment,
        "attributes": event.attributes,
    }


def _looks_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in ("secret", "password", "token", "api_key", "apikey"))
