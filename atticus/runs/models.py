"""Domain models for Track B conversations and bounded runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}


MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class MessageRecord:
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: str


@dataclass(frozen=True)
class ConversationRecord:
    id: str
    created_at: str
    updated_at: str
    title: str | None = None


@dataclass
class CheckpointRecord:
    name: str
    at: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunRecord:
    id: str
    conversation_id: str
    status: RunStatus
    provider: str
    mode: str
    created_at: str
    updated_at: str
    input_messages: list[dict[str, str]] = field(default_factory=list)
    output_text: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    cancel_requested: bool = False
    checkpoints: list[CheckpointRecord] = field(default_factory=list)
    correlation_id: str | None = None
    idempotency_key: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "status": self.status.value,
            "provider": self.provider,
            "mode": self.mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "input_messages": list(self.input_messages),
            "output_text": self.output_text,
            "error": (
                None
                if not self.error_code
                else {"code": self.error_code, "message": self.error_message or ""}
            ),
            "cancel_requested": self.cancel_requested,
            "checkpoints": [
                {"name": c.name, "at": c.at, "detail": dict(c.detail)} for c in self.checkpoints
            ],
            "correlation_id": self.correlation_id,
        }
