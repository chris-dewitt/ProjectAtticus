from __future__ import annotations

from types import SimpleNamespace

import pytest

from atticus.core.config import ProviderAnthropicConfig, ProviderGeminiConfig, ProviderOpenAIConfig
from atticus.core.errors import ProviderError
from atticus.providers.anthropic_provider import AnthropicProvider
from atticus.providers.gemini_provider import GeminiProvider
from atticus.providers.openai_provider import OpenAIProvider


def test_openai_uses_get_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "atticus.providers.openai_provider.get_credential",
        lambda name: "sk-test" if name == "OPENAI_API_KEY" else None,
    )

    class _FakeCompletions:
        def create(self, **kwargs):  # noqa: ANN003
            assert kwargs["model"] == "gpt-4o-mini"
            assert kwargs["messages"][0]["role"] == "user"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok from openai"))]
            )

    class _FakeClient:
        def __init__(self, **kwargs):  # noqa: ANN003
            assert kwargs["api_key"] == "sk-test"
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setattr("atticus.providers.openai_provider.OpenAI", _FakeClient)
    p = OpenAIProvider(ProviderOpenAIConfig())
    assert p.generate([{"role": "user", "content": "hi"}]) == "ok from openai"


def test_openai_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("atticus.providers.openai_provider.get_credential", lambda name: None)
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        OpenAIProvider(ProviderOpenAIConfig())


def test_anthropic_provider_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "atticus.providers.anthropic_provider.get_credential",
        lambda name: "ant-key" if name == "ANTHROPIC_API_KEY" else None,
    )

    class _FakeMessages:
        def create(self, **kwargs):  # noqa: ANN003
            assert kwargs["model"]
            assert kwargs["system"]
            assert kwargs["messages"][0]["role"] == "user"
            return SimpleNamespace(content=[SimpleNamespace(text="ok from claude")])

    class _FakeAnthropic:
        def __init__(self, **kwargs):  # noqa: ANN003
            assert kwargs["api_key"] == "ant-key"
            self.messages = _FakeMessages()

    import sys
    import types

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _FakeAnthropic  # type: ignore[attr-defined]
    mod.APIError = Exception  # type: ignore[attr-defined]
    mod.APITimeoutError = Exception  # type: ignore[attr-defined]
    mod.RateLimitError = Exception  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", mod)

    p = AnthropicProvider(ProviderAnthropicConfig())
    out = p.generate(
        [
            {"role": "system", "content": "persona"},
            {"role": "user", "content": "hello"},
        ]
    )
    assert out == "ok from claude"


def test_anthropic_missing_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "atticus.providers.anthropic_provider.get_credential",
        lambda name: "ant-key",
    )
    import sys

    monkeypatch.setitem(sys.modules, "anthropic", None)  # force ImportError on import

    with pytest.raises(ProviderError, match=r"\[providers\]"):
        AnthropicProvider(ProviderAnthropicConfig())


def test_gemini_provider_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "atticus.providers.gemini_provider.get_credential",
        lambda name: "gem-key" if name == "GEMINI_API_KEY" else None,
    )

    class _FakeModels:
        def generate_content(self, **kwargs):  # noqa: ANN003
            assert kwargs["model"]
            assert kwargs["contents"][0]["role"] == "user"
            return SimpleNamespace(text="ok from gemini", candidates=[])

    class _FakeClient:
        def __init__(self, **kwargs):  # noqa: ANN003
            assert kwargs["api_key"] == "gem-key"
            self.models = _FakeModels()

    import sys
    import types

    genai_mod = types.ModuleType("google.genai")
    types_mod = types.ModuleType("google.genai.types")

    class GenerateContentConfig:
        def __init__(self, **kwargs):  # noqa: ANN003
            self.kwargs = kwargs

    types_mod.GenerateContentConfig = GenerateContentConfig  # type: ignore[attr-defined]
    genai_mod.types = types_mod  # type: ignore[attr-defined]
    google_mod = types.ModuleType("google")
    google_mod.genai = SimpleNamespace(Client=_FakeClient, types=types_mod)  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_mod)

    p = GeminiProvider(ProviderGeminiConfig())
    out = p.generate(
        [
            {"role": "system", "content": "persona"},
            {"role": "user", "content": "hello"},
        ]
    )
    assert out == "ok from gemini"
