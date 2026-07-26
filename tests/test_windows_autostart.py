from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.errors import WorkspaceError
from atticus.services import windows_autostart as startup


def test_non_windows_status_is_unsupported() -> None:
    result = startup.status(platform="linux")
    assert not result.supported
    assert not result.enabled
    assert result.path is None


def test_startup_directory_requires_appdata() -> None:
    with pytest.raises(WorkspaceError, match="APPDATA"):
        startup.startup_directory(env={}, platform="win32")


def test_enable_status_disable_roundtrip(tmp_path: Path) -> None:
    env = {"APPDATA": str(tmp_path / "AppData" / "Roaming")}
    bin_dir = tmp_path / "venv" / "Scripts"
    bin_dir.mkdir(parents=True)
    python = bin_dir / "python.exe"
    pythonw = bin_dir / "pythonw.exe"
    python.write_bytes(b"")
    pythonw.write_bytes(b"")

    path = startup.enable(
        python_executable=python,
        env=env,
        platform="win32",
    )
    assert path.name == startup.AUTOSTART_FILENAME
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert str(pythonw.resolve()) in text
    assert "-m atticus.desktop tray" in text

    current = startup.status(env=env, platform="win32")
    assert current.supported
    assert current.enabled
    assert current.path == path

    assert startup.disable(env=env, platform="win32")
    assert not path.exists()
    assert not startup.disable(env=env, platform="win32")
