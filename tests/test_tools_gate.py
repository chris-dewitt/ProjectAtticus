from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from atticus.core.config import AppConfig
from atticus.core.errors import PermissionDenied
from atticus.core.permissions import PermissionClass
from atticus.core.tool_request import ToolCallRequest
from atticus.memory.store import MemoryStore
from atticus.tools.gate import run_tool_with_approval


def test_run_tool_with_approval_requires_tools_enabled(tmp_path: Path) -> None:
    cfg = AppConfig.model_validate({"tools": {"enabled": False}})
    store = MemoryStore(tmp_path / "g.sqlite3")
    console = Console(record=True, width=120)
    req = ToolCallRequest(
        tool_name="noop",
        permission_class=PermissionClass.SAFE_READ,
        action_summary="No-op",
    )
    try:
        with pytest.raises(PermissionDenied):
            run_tool_with_approval(
                cfg=cfg,
                store=store,
                console=console,
                request=req,
                action=lambda: "done",
            )
    finally:
        store.close()
