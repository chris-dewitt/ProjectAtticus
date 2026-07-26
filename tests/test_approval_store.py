from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import AppConfig
from atticus.core.permissions import PermissionClass
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import ApprovalStatus, PolicyInput
from atticus.policy.service import PolicyService
from atticus.policy.store import ApprovalConflict, ApprovalStore


def _service(tmp_path: Path) -> PolicyService:
    cfg = AppConfig()
    cfg.tools.enabled = True
    cfg.tools.files.enabled = True
    return PolicyService(
        PolicyEngine(cfg),
        ApprovalStore(tmp_path / "approvals.sqlite3"),
        approval_ttl_seconds=300,
    )


def test_approval_lifecycle_and_audit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    intent = PolicyInput(
        tool_name="file_write",
        permission_class=PermissionClass.WRITE,
        action_summary="Write generated report",
        inputs={"path": "report.md", "content_sha256": "abc123"},
    )
    result = service.evaluate(intent, create_approval=True)
    assert result.approval is not None
    approval = result.approval
    assert approval.status == ApprovalStatus.PENDING

    approved = service.store.decide(
        approval.id,
        approve=True,
        actor="speaker",
        action_digest=approval.action_digest,
        confirmation=f"APPROVE {approval.confirmation_hint}",
        rationale="Reviewed exact output digest.",
    )
    assert approved.status == ApprovalStatus.APPROVED

    executed = service.store.record_execution(
        approval.id,
        succeeded=True,
        result_summary="Wrote report.md",
        actor="atticus",
    )
    assert executed.status == ApprovalStatus.EXECUTED
    event_types = {e["event_type"] for e in service.store.list_audit_events()}
    assert {
        "policy_evaluated",
        "approval_requested",
        "approval_decided",
        "approval_execution_recorded",
    }.issubset(event_types)


def test_digest_and_exact_confirmation_required(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.evaluate(
        PolicyInput(
            tool_name="file_write",
            permission_class=PermissionClass.WRITE,
            action_summary="Write report",
        ),
        create_approval=True,
    )
    assert result.approval is not None
    approval = result.approval
    with pytest.raises(ApprovalConflict, match="digest"):
        service.store.decide(
            approval.id,
            approve=True,
            actor="speaker",
            action_digest="0" * 64,
            confirmation=f"APPROVE {approval.confirmation_hint}",
        )
    with pytest.raises(ApprovalConflict, match="Confirmation"):
        service.store.decide(
            approval.id,
            approve=True,
            actor="speaker",
            action_digest=approval.action_digest,
            confirmation="yes",
        )


def test_terminal_approval_cannot_be_replayed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.evaluate(
        PolicyInput(
            tool_name="file_write",
            permission_class=PermissionClass.WRITE,
            action_summary="Write report",
        ),
        create_approval=True,
    )
    assert result.approval is not None
    approval = result.approval
    service.store.decide(
        approval.id,
        approve=False,
        actor="speaker",
        action_digest=approval.action_digest,
        confirmation=f"DENY {approval.confirmation_hint}",
    )
    with pytest.raises(ApprovalConflict, match="already denied"):
        service.store.decide(
            approval.id,
            approve=True,
            actor="speaker",
            action_digest=approval.action_digest,
            confirmation=f"APPROVE {approval.confirmation_hint}",
        )
