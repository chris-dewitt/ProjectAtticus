"""Deterministic policy evaluation for Track B M3."""

from __future__ import annotations

from datetime import UTC, datetime

from atticus.core.config import AppConfig
from atticus.core.permissions import PermissionClass
from atticus.core.telemetry import get_correlation_id
from atticus.policy.models import (
    PolicyDecision,
    PolicyEffect,
    PolicyInput,
    RiskLevel,
    new_id,
)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class PolicyEngine:
    """Evaluate tool intent without executing it or consulting a model."""

    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def evaluate(self, intent: PolicyInput) -> PolicyDecision:
        reasons: list[str] = []

        if not self._cfg.tools.enabled:
            effect = PolicyEffect.DENY
            risk = _risk_for(intent)
            reasons.append("tools_disabled")
        elif not _tool_enabled(self._cfg, intent.tool_name):
            effect = PolicyEffect.DENY
            risk = _risk_for(intent)
            reasons.append("tool_disabled")
        elif intent.permission_class == PermissionClass.SAFE_READ:
            effect = PolicyEffect.ALLOW
            risk = RiskLevel.LOW
            reasons.append("safe_read")
        else:
            effect = PolicyEffect.REQUIRE_APPROVAL
            risk = _risk_for(intent)
            reasons.append(f"{intent.permission_class.value}_requires_approval")
            if intent.external_data:
                reasons.append("external_data")
            if intent.destructive:
                reasons.append("destructive_action")

        return PolicyDecision(
            id=new_id("pdec"),
            effect=effect,
            risk=risk,
            reasons=tuple(reasons),
            action_digest=intent.action_digest,
            tool_name=intent.tool_name,
            permission_class=intent.permission_class,
            action_summary=intent.action_summary,
            actor=intent.actor,
            created_at=_utc_now(),
            correlation_id=get_correlation_id(),
        )


def _risk_for(intent: PolicyInput) -> RiskLevel:
    if intent.destructive or intent.permission_class == PermissionClass.DESTRUCTIVE:
        return RiskLevel.CRITICAL
    if intent.permission_class in {
        PermissionClass.WRITE,
        PermissionClass.EXECUTE,
        PermissionClass.EXTERNAL_SEND,
    }:
        return RiskLevel.HIGH
    if intent.permission_class == PermissionClass.SENSITIVE_READ:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _tool_enabled(cfg: AppConfig, tool_name: str) -> bool:
    """Best-effort mapping; unknown tools remain policy-visible but denied."""
    key = tool_name.lower()
    if key.startswith(("file_", "code_search", "summarize_file")):
        return cfg.tools.files.enabled
    if key.startswith(("git", "patch", "test", "shell")):
        return cfg.tools.shell.enabled
    if key.startswith(("browse", "open_url")):
        return cfg.tools.browser.enabled
    if key.startswith(("gmail", "email")):
        return cfg.tools.email.enabled
    if key.startswith("calendar"):
        return cfg.tools.calendar.enabled
    if key.startswith("github"):
        return cfg.tools.github.enabled
    return False
