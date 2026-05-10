from __future__ import annotations

from typing import Any


class MockProvider:
    """Deterministic provider for tests (no network)."""

    name = "mock"

    def __init__(self, reply: str | None = None) -> None:
        self._reply = reply

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        del tools, mode
        if self._reply is not None:
            return self._reply
        last = messages[-1] if messages else {}
        content = last.get("content", "")
        return f"[mock] {content}"
