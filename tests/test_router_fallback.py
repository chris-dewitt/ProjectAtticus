from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import load_app_config
from atticus.core.errors import ProviderError
from atticus.core.router import ProviderRouter
from atticus.core.telemetry import Telemetry, set_telemetry


def test_routing_decision_recorded_on_manual_override(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo_root)
    telemetry = Telemetry(enabled=True, emit_stderr=False)
    set_telemetry(telemetry)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    router = ProviderRouter(cfg)
    router.set_provider("anthropic")
    assert router.last_decision is not None
    assert router.last_decision.selected == "anthropic"
    assert router.last_decision.reason == "manual_override"
    assert any(e.name == "router.manual_override" for e in telemetry.events)


def test_fallback_exhausted_raises(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(repo_root)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.providers.openai.enabled = False
    cfg.providers.anthropic.enabled = False
    cfg.providers.gemini.enabled = False
    cfg.providers.routing.automatic = True
    router = ProviderRouter(cfg)
    with pytest.raises(ProviderError, match="No provider available"):
        router.resolve_with_fallback("openai")
