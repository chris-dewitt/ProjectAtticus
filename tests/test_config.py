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
    assert cfg.api.host == "127.0.0.1"
    assert cfg.api.port == 8000
    assert cfg.api.enabled is False
    assert cfg.api.ui_enabled is True
    assert cfg.api.runs_sqlite_path.endswith("atticus_runs.sqlite3")
    assert cfg.api.max_messages_per_run == 32
    assert cfg.telemetry.service_name == "project-atticus"
    assert cfg.telemetry.enabled is True


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
