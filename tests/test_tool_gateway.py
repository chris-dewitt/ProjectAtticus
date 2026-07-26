from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import AppConfig
from atticus.core.permissions import PermissionClass
from atticus.policy.dispatch import DispatchDenied, ToolGateway
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import PolicyInput
from atticus.policy.service import PolicyService
from atticus.policy.store import ApprovalStore


def _approved_echo(tmp_path: Path) -> tuple[PolicyService, ToolGateway, str]:
    cfg = AppConfig()
    cfg.tools.enabled = True
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    service = PolicyService(PolicyEngine(cfg), store, approval_ttl_seconds=300)
    gateway = ToolGateway(cfg, store)
    result = service.evaluate(
        PolicyInput(
            tool_name="local_echo",
            permission_class=PermissionClass.WRITE,
            action_summary="Echo a test message",
            inputs={"message": "steady as she goes"},
            actor="speaker",
        ),
        create_approval=True,
    )
    assert result.approval is not None
    approval = result.approval
    decided = store.decide(
        approval.id,
        approve=True,
        actor="speaker",
        action_digest=approval.action_digest,
        confirmation=f"APPROVE {approval.confirmation_hint}",
    )
    assert decided.status.value == "approved"
    return service, gateway, approval.id


def test_idempotent_dispatch_replays(tmp_path: Path) -> None:
    _service, gateway, approval_id = _approved_echo(tmp_path)
    first = gateway.execute(approval_id, idempotency_key="echo-1", actor="atticus")
    assert first.replayed is False
    assert first.result["echo"] == "steady as she goes"
    second = gateway.execute(approval_id, idempotency_key="echo-1", actor="atticus")
    assert second.replayed is True
    assert second.result == first.result


def test_unapproved_cannot_dispatch(tmp_path: Path) -> None:
    cfg = AppConfig()
    cfg.tools.enabled = True
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    service = PolicyService(PolicyEngine(cfg), store)
    gateway = ToolGateway(cfg, store)
    result = service.evaluate(
        PolicyInput(
            tool_name="local_echo",
            permission_class=PermissionClass.WRITE,
            action_summary="Echo",
            inputs={"message": "nope"},
        ),
        create_approval=True,
    )
    assert result.approval is not None
    with pytest.raises(DispatchDenied, match="only approved"):
        gateway.execute(result.approval.id, idempotency_key="k", actor="atticus")


def test_file_write_dispatch_under_approved_path(tmp_path: Path) -> None:
    cfg = AppConfig()
    cfg.tools.enabled = True
    cfg.tools.files.enabled = True
    cfg.tools.approved_paths = [str(tmp_path)]
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    service = PolicyService(PolicyEngine(cfg), store)
    gateway = ToolGateway(cfg, store)
    target = tmp_path / "out.txt"
    result = service.evaluate(
        PolicyInput(
            tool_name="file_write",
            permission_class=PermissionClass.WRITE,
            action_summary=f"Write {target.name}",
            inputs={"path": str(target), "content": "hello speaker"},
            resource=str(target),
        ),
        create_approval=True,
    )
    assert result.approval is not None
    store.decide(
        result.approval.id,
        approve=True,
        actor="speaker",
        action_digest=result.approval.action_digest,
        confirmation=f"APPROVE {result.approval.confirmation_hint}",
    )
    dispatched = gateway.execute(
        result.approval.id,
        idempotency_key="write-1",
        actor="atticus",
    )
    assert dispatched.replayed is False
    assert target.read_text(encoding="utf-8").startswith("hello speaker")
