from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import load_app_config, resolve_repo_root
from atticus.core.errors import ConfigurationError


def test_load_app_config_from_example(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    assert cfg.assistant.name == "Atticus"
    assert cfg.providers.routing.default_provider == "openai"
    assert path.name == "atticus.example.yaml"


def test_resolve_repo_root_from_config_path(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    root = resolve_repo_root(cfg, config_file=path)
    assert (root / "prompts" / "atticus_system_prompt.md").is_file()


def test_invalid_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    bad = tmp_path / "bad.yaml"
    bad.write_text("{ not: valid yaml [[", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_app_config(config_path=bad)
