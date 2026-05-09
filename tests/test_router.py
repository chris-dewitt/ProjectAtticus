from __future__ import annotations

import pytest

from atticus.core.config import load_app_config
from atticus.core.errors import ProviderError
from atticus.core.router import ProviderRouter


def test_stub_providers_raise(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    router = ProviderRouter(cfg)
    router.set_provider("anthropic")
    with pytest.raises(ProviderError):
        router.generate([{"role": "user", "content": "hello"}])


def test_openai_requires_key(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    router = ProviderRouter(cfg)
    router.set_provider("openai")
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        router.generate([{"role": "user", "content": "hello"}])


def test_set_provider_invalid_name(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    router = ProviderRouter(cfg)
    with pytest.raises(ValueError):
        router.set_provider("local-llm")
