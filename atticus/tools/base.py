from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from atticus.core.config import AppConfig
from atticus.core.errors import PermissionDenied
from atticus.core.permissions import PermissionClass, ensure_tools_enabled


@dataclass(frozen=True)
class ToolContext:
    cfg: AppConfig


class Tool(Protocol):
    name: str
    permission: PermissionClass

    def run(self, ctx: ToolContext, **kwargs: Any) -> str:
        ...


def deny_unless_tools_enabled(ctx: ToolContext, action: str) -> None:
    """Default guard for any tool entrypoint."""
    try:
        ensure_tools_enabled(ctx.cfg)
    except PermissionDenied:
        raise PermissionDenied(f"{action} is unavailable while tools are disabled.") from None
