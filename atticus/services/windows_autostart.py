"""Windows Startup-folder integration for the optional Atticus tray.

This module only performs filesystem changes when ``enable`` or ``disable`` is
called. The CLI entrypoint in ``atticus.desktop`` owns the confirmation flow.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from atticus.core.errors import WorkspaceError

AUTOSTART_FILENAME = "ProjectAtticus-Tray.cmd"


@dataclass(frozen=True)
class AutostartStatus:
    supported: bool
    enabled: bool
    path: Path | None
    detail: str


def startup_directory(
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> Path:
    """Return the current user's Windows Startup folder."""
    platform = platform or sys.platform
    if platform != "win32":
        raise WorkspaceError("Atticus autostart is currently supported on Windows only.")
    values = env if env is not None else os.environ
    appdata = values.get("APPDATA", "").strip()
    if not appdata:
        raise WorkspaceError("APPDATA is not set; cannot locate the Windows Startup folder.")
    return (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )


def autostart_path(
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> Path:
    return startup_directory(env=env, platform=platform) / AUTOSTART_FILENAME


def _pythonw_path(python_executable: str | Path) -> Path:
    """Prefer pythonw.exe beside python.exe so startup does not retain a console."""
    executable = Path(python_executable).resolve()
    if executable.name.lower() == "python.exe":
        candidate = executable.with_name("pythonw.exe")
        if candidate.is_file():
            return candidate
    return executable


def launcher_text(python_executable: str | Path) -> str:
    """Build a quoted Startup launcher for the current Python environment."""
    executable = _pythonw_path(python_executable)
    return (
        "@echo off\r\n"
        f'"{executable}" -m atticus.desktop tray\r\n'
    )


def status(
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> AutostartStatus:
    platform = platform or sys.platform
    if platform != "win32":
        return AutostartStatus(
            supported=False,
            enabled=False,
            path=None,
            detail="Windows Startup-folder autostart is unavailable on this OS.",
        )
    try:
        path = autostart_path(env=env, platform=platform)
    except WorkspaceError as exc:
        return AutostartStatus(False, False, None, str(exc))
    enabled = path.is_file()
    detail = "enabled" if enabled else "disabled"
    return AutostartStatus(True, enabled, path, detail)


def enable(
    *,
    python_executable: str | Path = sys.executable,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> Path:
    """Create the Startup launcher. Caller must obtain explicit approval first."""
    path = autostart_path(env=env, platform=platform)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(launcher_text(python_executable), encoding="utf-8", newline="")
    return path


def disable(
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> bool:
    """Remove only the Atticus-owned launcher. Caller must confirm first."""
    path = autostart_path(env=env, platform=platform)
    if not path.is_file():
        return False
    path.unlink()
    return True
