"""Application service coordinating deterministic policy and approvals."""

from __future__ import annotations

from dataclasses import dataclass

from atticus.core.telemetry import get_telemetry
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import ApprovalRequest, PolicyDecision, PolicyEffect, PolicyInput
from atticus.policy.store import ApprovalStore


@dataclass(frozen=True)
class PolicyEvaluation:
    decision: PolicyDecision
    approval: ApprovalRequest | None

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.to_dict(),
            "approval": self.approval.to_dict() if self.approval else None,
        }


class PolicyService:
    """Persist every decision and create approval requests when required."""

    def __init__(
        self,
        engine: PolicyEngine,
        store: ApprovalStore,
        *,
        approval_ttl_seconds: int = 900,
    ) -> None:
        self.engine = engine
        self.store = store
        self.approval_ttl_seconds = approval_ttl_seconds

    def evaluate(
        self,
        intent: PolicyInput,
        *,
        create_approval: bool = False,
    ) -> PolicyEvaluation:
        decision = self.store.record_decision(self.engine.evaluate(intent))
        approval = None
        if create_approval and decision.effect == PolicyEffect.REQUIRE_APPROVAL:
            approval = self.store.create_approval(
                decision,
                ttl_seconds=self.approval_ttl_seconds,
            )
        get_telemetry().emit(
            "policy.evaluated",
            decision_id=decision.id,
            effect=decision.effect.value,
            risk=decision.risk.value,
            approval_id=approval.id if approval else None,
        )
        return PolicyEvaluation(decision=decision, approval=approval)
