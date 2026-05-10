from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Common interface for chat completion providers."""

    name: str

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        """Return assistant text for the given OpenAI-style chat messages."""
        ...
