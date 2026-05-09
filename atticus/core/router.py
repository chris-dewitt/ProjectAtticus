from __future__ import annotations

from typing import Any

from atticus.core.config import AppConfig
from atticus.core.errors import ProviderError
from atticus.providers.anthropic_provider import AnthropicProviderStub
from atticus.providers.base import LLMProvider
from atticus.providers.gemini_provider import GeminiProviderStub
from atticus.providers.openai_provider import OpenAIProvider


class ProviderRouter:
    """Selects the active LLM provider (Phase 1: OpenAI live, others stubbed)."""

    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg
        self._openai: OpenAIProvider | None = None
        self._anthropic = AnthropicProviderStub()
        self._gemini = GeminiProviderStub()
        self._current = cfg.providers.routing.default_provider.lower()

    @property
    def current(self) -> str:
        return self._current

    def set_provider(self, name: str) -> None:
        key = name.strip().lower()
        if key not in {"openai", "anthropic", "gemini"}:
            raise ValueError("Provider must be one of: openai, anthropic, gemini")
        default = self._cfg.providers.routing.default_provider.lower()
        if not self._cfg.providers.routing.allow_manual_override and key != default:
            raise ValueError("Manual provider override is disabled in config.")
        self._current = key

    def active_provider(self) -> LLMProvider:
        if self._current == "openai":
            if self._openai is None:
                self._openai = OpenAIProvider(self._cfg.providers.openai)
            return self._openai
        if self._current == "anthropic":
            return self._anthropic
        if self._current == "gemini":
            return self._gemini
        raise ProviderError(f"Unknown provider: {self._current}")

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        provider = self.active_provider()
        return provider.generate(messages, tools=tools, mode=mode)
