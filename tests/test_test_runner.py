from __future__ import annotations

import pytest

from atticus.core.errors import WorkspaceError
from atticus.services.test_runner import assert_safe_test_command


def test_pytest_allowed() -> None:
    assert assert_safe_test_command("pytest -q")[0] == "pytest"
    assert assert_safe_test_command("python -m pytest tests")[:3] == ["python", "-m", "pytest"]


def test_rejects_shell_metacharacters() -> None:
    with pytest.raises(WorkspaceError):
        assert_safe_test_command("pytest -q; rm -rf /")


def test_rejects_non_pytest() -> None:
    with pytest.raises(WorkspaceError, match="allow-listed"):
        assert_safe_test_command("python evil.py")
