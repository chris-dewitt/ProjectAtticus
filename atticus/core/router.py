from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atticus.core.config import AppConfig
from atticus.core.errors import ProviderError
from atticus.core.telemetry import get_telemetry
from atticus.providers.anthropic_provider import AnthropicProvider
from atticus.providers.base import LLMProvider
from atticus.providers.gemini_provider import GeminiProvider
from atticus.providers.openai_provider import OpenAIProvider


@dataclass
class RoutingDecision:
    selected: str
    reason: str
    attempted: list[str] = field(default_factory=list)
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": self.selected,
            "reason": self.reason,
            "attempted": list(self.attempted),
            "fallback_used": self.fallback_used,
        }


class ProviderRouter:
    """Selects the active LLM provider with optional recorded fallback."""

    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg
        self._openai: OpenAIProvider | None = None
        self._anthropic: AnthropicProvider | None = None
        self._gemini: GeminiProvider | None = None
        self._current = cfg.providers.routing.default_provider.lower()
        self.last_decision: RoutingDecision | None = None

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
        if key == "openai" and not self._cfg.providers.openai.enabled:
            raise ValueError("OpenAI provider is disabled in config.")
        if key == "anthropic" and not self._cfg.providers.anthropic.enabled:
            raise ValueError("Anthropic provider is disabled in config.")
        if key == "gemini" and not self._cfg.providers.gemini.enabled:
            raise ValueError("Gemini provider is disabled in config.")
        self._current = key
        if key == "openai":
            self._openai = None
        elif key == "anthropic":
            self._anthropic = None
        else:
            self._gemini = None
        self.last_decision = RoutingDecision(
            selected=key,
            reason="manual_override",
            attempted=[key],
            fallback_used=False,
        )
        if self._cfg.providers.routing.record_routing_decisions:
            get_telemetry().emit("router.manual_override", **self.last_decision.to_dict())

    def _provider_for(self, key: str) -> LLMProvider:
        if key == "openai":
            if not self._cfg.providers.openai.enabled:
                raise ProviderError("OpenAI provider is disabled in config.")
            if self._openai is None:
                self._openai = OpenAIProvider(self._cfg.providers.openai)
            return self._openai
        if key == "anthropic":
            if not self._cfg.providers.anthropic.enabled:
                raise ProviderError("Anthropic provider is disabled in config.")
            if self._anthropic is None:
                self._anthropic = AnthropicProvider(self._cfg.providers.anthropic)
            return self._anthropic
        if key == "gemini":
            if not self._cfg.providers.gemini.enabled:
                raise ProviderError("Gemini provider is disabled in config.")
            if self._gemini is None:
                self._gemini = GeminiProvider(self._cfg.providers.gemini)
            return self._gemini
        raise ProviderError(f"Unknown provider: {key}")

    def active_provider(self) -> LLMProvider:
        return self._provider_for(self._current)

    def resolve_with_fallback(self, preferred: str | None = None) -> LLMProvider:
        """Pick preferred/current provider, falling back through configured order."""
        order: list[str] = []
        preferred_key = (preferred or self._current).lower()
        order.append(preferred_key)
        if self._cfg.providers.routing.automatic:
            for name in self._cfg.providers.routing.fallback_order:
                key = name.lower()
                if key not in order:
                    order.append(key)

        attempted: list[str] = []
        errors: list[str] = []
        for key in order:
            attempted.append(key)
            try:
                provider = self._provider_for(key)
                # Probe credential presence without calling a paid API.
                if hasattr(provider, "ensure_ready"):
                    provider.ensure_ready()  # type: ignore[attr-defined]
                self._current = key
                self.last_decision = RoutingDecision(
                    selected=key,
                    reason="preferred" if key == preferred_key else "fallback",
                    attempted=attempted,
                    fallback_used=key != preferred_key,
                )
                if self._cfg.providers.routing.record_routing_decisions:
                    get_telemetry().emit("router.selected", **self.last_decision.to_dict())
                return provider
            except Exception as exc:  # noqa: BLE001 — try next provider
                errors.append(f"{key}:{exc.__class__.__name__}")
                continue

        self.last_decision = RoutingDecision(
            selected="",
            reason="all_providers_failed",
            attempted=attempted,
            fallback_used=True,
        )
        if self._cfg.providers.routing.record_routing_decisions:
            get_telemetry().emit("router.failed", attempted=attempted, errors=errors)
        raise ProviderError(
            "No provider available after fallback",
            code="provider_routing_failed",
            status_code=503,
            safe_details={"attempted": attempted, "errors": errors},
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        """Generate with the selected provider; on failure, try configured fallbacks."""
        try:
            provider = self.active_provider()
            text = provider.generate(messages, tools=tools, mode=mode)
            self.last_decision = RoutingDecision(
                selected=self._current,
                reason="active_provider",
                attempted=[self._current],
                fallback_used=False,
            )
            return text
        except ProviderError as first_error:
            if not self._cfg.providers.routing.automatic:
                raise
            order = [
                n.lower()
                for n in self._cfg.providers.routing.fallback_order
                if n.lower() != self._current
            ]
            attempted = [self._current]
            for key in order:
                attempted.append(key)
                try:
                    provider = self._provider_for(key)
                    text = provider.generate(messages, tools=tools, mode=mode)
                    self._current = key
                    self.last_decision = RoutingDecision(
                        selected=key,
                        reason="fallback_after_error",
                        attempted=attempted,
                        fallback_used=True,
                    )
                    if self._cfg.providers.routing.record_routing_decisions:
                        get_telemetry().emit(
                            "router.fallback_used",
                            **self.last_decision.to_dict(),
                        )
                    return text
                except Exception:  # noqa: BLE001 — try next
                    continue
            raise first_error
