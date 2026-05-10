from __future__ import annotations

from pathlib import Path

from atticus.core.approvals import request_tool_approval
from atticus.core.permissions import PermissionClass
from atticus.core.tool_request import ToolCallRequest
from atticus.memory.store import MemoryStore


class _FixedAnswer:
    def __init__(self, answer: str) -> None:
        self._answer = answer

    def ask(self, prompt: str) -> str:
        del prompt
        return self._answer


def test_request_tool_approval_logs_denial(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "a.sqlite3")
    try:
        req = ToolCallRequest(
            tool_name="test_tool",
            permission_class=PermissionClass.WRITE,
            action_summary="Do something risky",
        )
        assert request_tool_approval(_FixedAnswer("n"), store, req) is False
        rows = store.list_tool_approvals(limit=1)
        assert rows[0].approved is False
        assert rows[0].tool_name == "test_tool"
    finally:
        store.close()


def test_request_tool_approval_logs_approval(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "b.sqlite3")
    try:
        req = ToolCallRequest(
            tool_name="test_tool",
            permission_class=PermissionClass.SAFE_READ,
            action_summary="Read something harmless",
        )
        assert request_tool_approval(_FixedAnswer("yes"), store, req) is True
        rows = store.list_tool_approvals(limit=1)
        assert rows[0].approved is True
    finally:
        store.close()
