from __future__ import annotations

from collections.abc import Callable

from rich.console import Console

from atticus.core.approvals import ConsoleYesNoSource, request_tool_approval
from atticus.core.config import AppConfig
from atticus.core.errors import PermissionDenied
from atticus.core.tool_request import ToolCallRequest
from atticus.memory.store import MemoryStore
from atticus.tools.base import ToolContext, deny_unless_tools_enabled


def run_tool_with_approval(
    *,
    cfg: AppConfig,
    store: MemoryStore,
    console: Console,
    request: ToolCallRequest,
    action: Callable[[], str],
) -> str:
    """Run a gated tool action after interactive approval and audit logging."""
    ctx = ToolContext(cfg=cfg)
    deny_unless_tools_enabled(ctx, request.tool_name)
    source = ConsoleYesNoSource(console)
    if not request_tool_approval(source, store, request):
        raise PermissionDenied("Boss declined; Atticus will not run that tool.")
    return action()
