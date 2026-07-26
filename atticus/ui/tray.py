"""Optional Windows system tray for launching Atticus surfaces.

The tray does not execute tools, read private data, or bypass approvals. It
only launches the existing CLI/desk entrypoints and exits itself.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from atticus.core.errors import AtticusError


class TrayUnavailable(AtticusError):
    """The optional tray dependencies or supported OS are unavailable."""


def _optional_dependencies() -> tuple[Any, Any, Any]:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise TrayUnavailable(
            'Tray dependencies missing. Install with: pip install -e ".[desktop]"'
        ) from exc
    return pystray, Image, ImageDraw


def _icon_image() -> Any:
    """Draw a small local icon; no bundled binary asset required."""
    _, image_module, draw_module = _optional_dependencies()
    image = image_module.new("RGBA", (64, 64), (30, 35, 42, 255))
    draw = draw_module.Draw(image)
    draw.rounded_rectangle((5, 5, 59, 59), radius=12, fill=(47, 111, 167, 255))
    draw.polygon([(32, 13), (50, 50), (42, 50), (37, 39), (27, 39), (22, 50), (14, 50)], fill="white")
    draw.rectangle((29, 32, 35, 36), fill=(47, 111, 167, 255))
    return image


def _launch_desk() -> None:
    subprocess.Popen(
        [sys.executable, "-m", "atticus.desktop", "desk"],
        cwd=str(Path.cwd()),
        close_fds=True,
    )


def _launch_cli() -> None:
    if sys.platform != "win32":
        raise TrayUnavailable("Opening a new Atticus terminal is currently Windows-only.")
    command = f'& "{sys.executable}" -m atticus'
    subprocess.Popen(
        ["powershell.exe", "-NoExit", "-Command", command],
        cwd=str(Path.cwd()),
        close_fds=True,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def run_tray() -> None:
    """Run the blocking tray event loop."""
    if sys.platform != "win32":
        raise TrayUnavailable("The Atticus system tray is currently supported on Windows only.")
    pystray, _, _ = _optional_dependencies()

    icon: Any

    def open_desk(_icon: Any, _item: Any) -> None:
        _launch_desk()

    def open_cli(_icon: Any, _item: Any) -> None:
        _launch_cli()

    def quit_tray(current: Any, _item: Any) -> None:
        current.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open Atticus Desk", open_desk, default=True),
        pystray.MenuItem("Open Atticus CLI", open_cli),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit tray", quit_tray),
    )
    icon = pystray.Icon(
        "ProjectAtticus",
        _icon_image(),
        "Atticus — local assistant",
        menu,
    )
    icon.run()
