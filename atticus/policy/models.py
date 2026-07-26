"""Framework-independent policy and approval domain models."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from atticus.core.permissions import PermissionClass


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"

    @property
    def terminal(self) -> bool:
        return self != ApprovalStatus.PENDING


@dataclass(frozen=True)
class PolicyInput:
    tool_name: str
    permission_class: PermissionClass
    action_summary: str
    inputs: dict[str, Any] = field(default_factory=dict)
    actor: str = "boss"
    resource: str | None = None
    external_data: bool = False
    destructive: bool = False

    @property
    def action_digest(self) -> str:
        """Stable digest over the exact proposed action."""
        canonical = json.dumps(
            {
                "tool_name": self.tool_name,
                "permission_class": self.permission_class.value,
                "action_summary": self.action_summary,
                "inputs": self.inputs,
                "actor": self.actor,
                "resource": self.resource,
                "external_data": self.external_data,
                "destructive": self.destructive,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolicyDecision:
    id: str
    effect: PolicyEffect
    risk: RiskLevel
    reasons: tuple[str, ...]
    action_digest: str
    tool_name: str
    permission_class: PermissionClass
    action_summary: str
    actor: str
    created_at: str
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["effect"] = self.effect.value
        payload["risk"] = self.risk.value
        payload["permission_class"] = self.permission_class.value
        payload["reasons"] = list(self.reasons)
        return payload


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    policy_decision_id: str
    action_digest: str
    tool_name: str
    permission_class: PermissionClass
    action_summary: str
    risk: RiskLevel
    status: ApprovalStatus
    created_at: str
    expires_at: str
    decided_at: str | None = None
    actor: str | None = None
    rationale: str | None = None
    execution_result: str | None = None
    correlation_id: str | None = None

    @property
    def confirmation_hint(self) -> str:
        return f"{self.action_digest[:12]}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["permission_class"] = self.permission_class.value
        payload["risk"] = self.risk.value
        payload["status"] = self.status.value
        payload["confirmation_hint"] = self.confirmation_hint
        return payload


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
