from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.errors import ConfigurationError
from atticus.core.persona import build_system_prompt


def test_build_system_prompt_contains_atticus(repo_root: Path) -> None:
    text = build_system_prompt(repo_root, "default")
    assert "Atticus" in text
    assert "The Speaker" in text


def test_unknown_mode(repo_root: Path) -> None:
    with pytest.raises(ConfigurationError):
        build_system_prompt(repo_root, "not_a_real_mode")
