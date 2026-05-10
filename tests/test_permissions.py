from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import AppConfig, load_app_config
from atticus.core.errors import PermissionDenied
from atticus.core.permissions import ensure_shell_allowed, ensure_tools_enabled


def test_tools_disabled_blocks_shell(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    with pytest.raises(PermissionDenied):
        ensure_shell_allowed(cfg)
    with pytest.raises(PermissionDenied):
        ensure_tools_enabled(cfg)


def test_shell_disabled_when_tools_on_but_shell_off() -> None:
    cfg = AppConfig.model_validate(
        {"tools": {"enabled": True, "shell": {"enabled": False}, "files": {"enabled": False}}}
    )
    with pytest.raises(PermissionDenied, match="shell"):
        ensure_shell_allowed(cfg)
