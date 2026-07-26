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
    draw.rectangle((8, 8, 56, 56), outline=(184, 149, 108, 255), width=2)
    draw.text((22, 16), "A", fill=(224, 201, 160, 255))
    return image


def _launch_desk() -> None:
    subprocess.Popen(
        [sys.executable, "-m", "atticus.desktop", "desk"],
        cwd=str(Path.cwd()),
        close_fds=True,
    )


def _launch_ui() -> None:
    subprocess.Popen(
        [sys.executable, "-m", "atticus.desktop", "ui"],
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

    def open_ui(_icon: Any, _item: Any) -> None:
        _launch_ui()

    def open_desk(_icon: Any, _item: Any) -> None:
        _launch_desk()

    def open_cli(_icon: Any, _item: Any) -> None:
        _launch_cli()

    def quit_tray(current: Any, _item: Any) -> None:
        current.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open Atticus Terminal", open_ui, default=True),
        pystray.MenuItem("Open Status Desk", open_desk),
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
