from __future__ import annotations

import os
from typing import Any

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from atticus.core.config import ProviderOpenAIConfig
from atticus.core.errors import ProviderError


class OpenAIProvider:
    """OpenAI Chat Completions via the official SDK."""

    name = "openai"

    def __init__(self, cfg: ProviderOpenAIConfig) -> None:
        self._cfg = cfg
        key = os.environ.get(cfg.api_key_env, "").strip()
        if not key:
            raise ProviderError(
                f"Missing API key: set {cfg.api_key_env} in your environment or .env file "
                "before using the OpenAI provider."
            )
        self._client = OpenAI(api_key=key, timeout=cfg.timeout_seconds)

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        del mode  # reserved for future routing hints
        try:
            kwargs: dict[str, Any] = {
                "model": self._cfg.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
            response = self._client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            raise ProviderError("OpenAI rate limit exceeded. Try again shortly.") from exc
        except APITimeoutError as exc:
            raise ProviderError("OpenAI request timed out.") from exc
        except APIError as exc:
            raise ProviderError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise ProviderError(f"Unexpected OpenAI error: {exc}") from exc

        choice = response.choices[0].message
        text = choice.content or ""
        return text.strip()
