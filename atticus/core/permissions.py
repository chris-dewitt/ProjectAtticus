from __future__ import annotations

from enum import Enum

from atticus.core.config import AppConfig
from atticus.core.errors import PermissionDenied


class PermissionClass(str, Enum):
    """Permission buckets for tools and risky operations."""

    SAFE_READ = "safe_read"
    SENSITIVE_READ = "sensitive_read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL_SEND = "external_send"
    EXECUTE = "execute"


def ensure_tools_enabled(cfg: AppConfig) -> None:
    """Central gate: tools are off by default in Phase 1."""
    if not cfg.tools.enabled:
        raise PermissionDenied(
            "Tools are disabled in configuration (tools.enabled=false). "
            "No shell, file, browser, email, or calendar actions are available until enabled."
        )


def ensure_shell_allowed(cfg: AppConfig) -> None:
    ensure_tools_enabled(cfg)
    raise PermissionDenied("Shell execution is not wired up yet.")


def ensure_file_write_allowed(cfg: AppConfig) -> None:
    ensure_tools_enabled(cfg)
    raise PermissionDenied("File write tools are not wired up yet.")
