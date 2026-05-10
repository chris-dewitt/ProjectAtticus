from __future__ import annotations

import pytest

from atticus.core.errors import WorkspaceError
from atticus.services.git_runner import assert_safe_git_command


def test_git_allowlist_accepts_status() -> None:
    assert_safe_git_command("git status --porcelain")


def test_git_rejects_injection() -> None:
    with pytest.raises(WorkspaceError):
        assert_safe_git_command("git status; rm -rf /")
