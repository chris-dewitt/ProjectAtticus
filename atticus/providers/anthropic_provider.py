from __future__ import annotations

from typing import Any

from atticus.core.config import ProviderAnthropicConfig
from atticus.core.errors import ProviderError
from atticus.core.secrets import get_credential
from atticus.providers.message_convert import anthropic_messages, split_system_and_turns


class AnthropicProvider:
    """Anthropic Messages API via the official SDK (optional ``anthropic`` package)."""

    name = "anthropic"

    def __init__(self, cfg: ProviderAnthropicConfig) -> None:
        self._cfg = cfg
        if not cfg.enabled:
            raise ProviderError("Anthropic provider is disabled in config (providers.anthropic.enabled=false).")
        key = get_credential(cfg.api_key_env)
        if not key:
            raise ProviderError(
                f"Missing API key: set {cfg.api_key_env} in your environment or .env file "
                "(or OS keyring via `pip install -e \".[secrets]\"`) before using Claude."
            )
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ProviderError(
                'Anthropic SDK is not installed. Run: pip install -e ".[providers]"'
            ) from exc
        self._client = Anthropic(api_key=key, timeout=cfg.timeout_seconds)

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        del mode
        system, turns = split_system_and_turns(messages)
        api_messages = anthropic_messages(turns)
        kwargs: dict[str, Any] = {
            "model": self._cfg.model,
            "max_tokens": 4096,
            "messages": api_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            # Future: map OpenAI-style tools; ignore for now so chat stays reliable.
            pass
        try:
            from anthropic import APIError, APITimeoutError, RateLimitError
        except ImportError:
            APIError = Exception  # type: ignore[misc, assignment]
            APITimeoutError = Exception  # type: ignore[misc, assignment]
            RateLimitError = Exception  # type: ignore[misc, assignment]
        try:
            response = self._client.messages.create(**kwargs)
        except RateLimitError as exc:
            raise ProviderError("Anthropic rate limit exceeded. Try again shortly.") from exc
        except APITimeoutError as exc:
            raise ProviderError("Anthropic request timed out.") from exc
        except APIError as exc:
            raise ProviderError(f"Anthropic API error: {exc}") from exc
        except Exception as exc:
            raise ProviderError(f"Unexpected Anthropic error: {exc}") from exc

        parts: list[str] = []
        for block in getattr(response, "content", None) or []:
            text = getattr(block, "text", None)
            if isinstance(text, str) and text:
                parts.append(text)
        return "\n".join(parts).strip()


# Backward-compatible alias for older imports/tests.
AnthropicProviderStub = AnthropicProvider
