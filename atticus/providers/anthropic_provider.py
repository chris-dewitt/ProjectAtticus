from __future__ import annotations

from typing import Any

from atticus.core.errors import ProviderError


class AnthropicProviderStub:
    """Phase 1 stub; full Anthropic integration arrives in a later phase."""

    name = "anthropic"

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        del messages, tools, mode
        raise ProviderError(
            "Claude (Anthropic) is wired as a stub in Phase 1. "
            "Use /provider openai for now."
        )
