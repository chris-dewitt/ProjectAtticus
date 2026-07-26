from __future__ import annotations

from atticus.core.config import AppConfig
from atticus.core.permissions import PermissionClass
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import PolicyEffect, PolicyInput, RiskLevel


def test_tools_disabled_denies() -> None:
    cfg = AppConfig()
    intent = PolicyInput(
        tool_name="file_read",
        permission_class=PermissionClass.SAFE_READ,
        action_summary="Read public fixture",
    )
    decision = PolicyEngine(cfg).evaluate(intent)
    assert decision.effect == PolicyEffect.DENY
    assert "tools_disabled" in decision.reasons


def test_safe_read_allowed_when_tool_enabled() -> None:
    cfg = AppConfig()
    cfg.tools.enabled = True
    cfg.tools.files.enabled = True
    intent = PolicyInput(
        tool_name="file_read",
        permission_class=PermissionClass.SAFE_READ,
        action_summary="Read approved fixture",
        resource="fixtures/example.txt",
    )
    decision = PolicyEngine(cfg).evaluate(intent)
    assert decision.effect == PolicyEffect.ALLOW
    assert decision.risk == RiskLevel.LOW
    assert len(decision.action_digest) == 64


def test_write_and_destructive_require_approval() -> None:
    cfg = AppConfig()
    cfg.tools.enabled = True
    cfg.tools.files.enabled = True
    write = PolicyInput(
        tool_name="file_write",
        permission_class=PermissionClass.WRITE,
        action_summary="Write output",
        inputs={"path": "out.txt", "content_sha256": "abc"},
    )
    destructive = PolicyInput(
        tool_name="file_delete",
        permission_class=PermissionClass.DESTRUCTIVE,
        action_summary="Delete output",
        destructive=True,
    )
    assert PolicyEngine(cfg).evaluate(write).effect == PolicyEffect.REQUIRE_APPROVAL
    d = PolicyEngine(cfg).evaluate(destructive)
    assert d.effect == PolicyEffect.REQUIRE_APPROVAL
    assert d.risk == RiskLevel.CRITICAL


def test_digest_changes_with_exact_action() -> None:
    base = dict(
        tool_name="file_write",
        permission_class=PermissionClass.WRITE,
        action_summary="Write output",
    )
    first = PolicyInput(**base, inputs={"path": "a.txt"})
    second = PolicyInput(**base, inputs={"path": "b.txt"})
    assert first.action_digest != second.action_digest
