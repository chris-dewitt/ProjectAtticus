from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atticus.core.permissions import PermissionClass


@dataclass(frozen=True)
class ToolCallRequest:
    """Structured tool intent for permission checks and audit logging."""

    tool_name: str
    permission_class: PermissionClass
    action_summary: str
    inputs: dict[str, Any] = field(default_factory=dict)
    external_data: bool = False
    destructive: bool = False
