from __future__ import annotations

from typing import Any

from atticus.core.config import ProviderGeminiConfig
from atticus.core.errors import ProviderError
from atticus.core.secrets import get_credential
from atticus.providers.message_convert import gemini_contents, split_system_and_turns


class GeminiProvider:
    """Google Gemini via the official ``google-genai`` SDK (optional extra)."""

    name = "gemini"

    def __init__(self, cfg: ProviderGeminiConfig) -> None:
        self._cfg = cfg
        if not cfg.enabled:
            raise ProviderError("Gemini provider is disabled in config (providers.gemini.enabled=false).")
        key = get_credential(cfg.api_key_env)
        if not key:
            raise ProviderError(
                f"Missing API key: set {cfg.api_key_env} in your environment or .env file "
                "(or OS keyring via `pip install -e \".[secrets]\"`) before using Gemini."
            )
        try:
            from google import genai
        except ImportError as exc:
            raise ProviderError(
                'Google GenAI SDK is not installed. Run: pip install -e ".[providers]"'
            ) from exc
        self._client = genai.Client(api_key=key)

    def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list | None = None,
        mode: str | None = None,
    ) -> str:
        del mode, tools
        system, turns = split_system_and_turns(messages)
        contents = gemini_contents(turns)
        try:
            from google.genai import types
        except ImportError as exc:
            raise ProviderError(
                'Google GenAI SDK is not installed. Run: pip install -e ".[providers]"'
            ) from exc

        config_kwargs: dict[str, Any] = {}
        if system:
            config_kwargs["system_instruction"] = system
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        try:
            response = self._client.models.generate_content(
                model=self._cfg.model,
                contents=contents,
                config=config,
                # http_options timeout is SDK-version dependent; keep simple.
            )
        except Exception as exc:
            name = type(exc).__name__
            msg = str(exc)
            if "timeout" in msg.lower() or "Timeout" in name:
                raise ProviderError("Gemini request timed out.") from exc
            if "429" in msg or "rate" in msg.lower():
                raise ProviderError("Gemini rate limit exceeded. Try again shortly.") from exc
            raise ProviderError(f"Gemini API error: {exc}") from exc

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        # Fallback: concatenate candidate parts if `.text` is empty.
        parts: list[str] = []
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                t = getattr(part, "text", None)
                if isinstance(t, str) and t:
                    parts.append(t)
        return "\n".join(parts).strip()


# Backward-compatible alias for older imports/tests.
GeminiProviderStub = GeminiProvider
