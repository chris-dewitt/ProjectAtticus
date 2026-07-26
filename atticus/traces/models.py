"""Trace span models for inspectable runs (Track B M4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanKind(str, Enum):
    RUN = "run"
    PROVIDER = "provider"
    TOOL = "tool"
    POLICY = "policy"
    APPROVAL = "approval"
    DISPATCH = "dispatch"
    SANDBOX = "sandbox"
    MEMORY = "memory"
    EVAL = "eval"
    DEMO = "demo"
    OTHER = "other"


@dataclass
class TraceSpan:
    """One inspectable span in a run trace."""

    id: str
    run_id: str
    name: str
    kind: SpanKind
    started_at: str
    ended_at: str | None = None
    status: str = "ok"
    parent_span_id: str | None = None
    correlation_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "name": self.name,
            "kind": self.kind.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "parent_span_id": self.parent_span_id,
            "correlation_id": self.correlation_id,
            "attributes": dict(self.attributes),
            "events": list(self.events),
        }
