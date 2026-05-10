from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import AppConfig
from atticus.core.errors import WorkspaceError
from atticus.services.paths import approved_roots, resolve_under_approved


def test_resolve_under_approved(tmp_path: Path) -> None:
    inner = tmp_path / "proj" / "notes"
    inner.mkdir(parents=True)
    (inner / "a.txt").write_text("hi", encoding="utf-8")
    cfg = AppConfig.model_validate(
        {
            "tools": {
                "enabled": True,
                "files": {"enabled": True},
                "approved_paths": [str(tmp_path / "proj")],
            }
        }
    )
    p = resolve_under_approved(cfg, str(inner / "a.txt"))
    assert p.is_file()


def test_rejects_outside_approved(tmp_path: Path) -> None:
    cfg = AppConfig.model_validate(
        {
            "tools": {
                "enabled": True,
                "files": {"enabled": True},
                "approved_paths": [str(tmp_path / "a")],
            }
        }
    )
    with pytest.raises(WorkspaceError):
        resolve_under_approved(cfg, str(tmp_path / "b" / "secret.txt"))


def test_approved_roots_empty_when_none_configured() -> None:
    cfg = AppConfig.model_validate({"tools": {"enabled": True, "files": {"enabled": True}, "approved_paths": []}})
    assert approved_roots(cfg) == []
