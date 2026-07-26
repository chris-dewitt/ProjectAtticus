"""Desktop / phone-adjacent shell for the classical terminal UI.

Starts the local API (if needed) and opens either:
- a native window via optional ``pywebview``, or
- the system browser (always available).

Phone installs use the PWA at ``/ui/`` after ``atticus-api --lan``.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _ui_ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=1.0) as response:  # noqa: S310 — local loopback only
            return 200 <= int(getattr(response, "status", 200)) < 500
    except (URLError, OSError, ValueError):
        return False


def _start_api_subprocess(*, host: str, port: int, config_path: Path | None) -> subprocess.Popen[Any]:
    cmd = [
        sys.executable,
        "-m",
        "atticus.api_server",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    return subprocess.Popen(
        cmd,
        cwd=str(Path.cwd()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def _wait_for_ui(url: str, *, timeout_seconds: float = 12.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _ui_ready(url):
            return True
        time.sleep(0.25)
    return False


def open_terminal_ui(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    config_path: Path | None = None,
    prefer_webview: bool = True,
    start_server: bool = True,
) -> int:
    """Open the classical terminal UI; return process exit code semantics (0 ok)."""
    bind_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    base = f"http://{bind_host}:{port}"
    ui_url = f"{base}/ui/"
    server: subprocess.Popen[Any] | None = None

    if start_server and not _port_open(bind_host, port):
        server = _start_api_subprocess(host=bind_host, port=port, config_path=config_path)
        if not _wait_for_ui(ui_url):
            if server.poll() is None:
                server.terminate()
            print(
                f"Could not start Atticus API at {ui_url}. "
                'Try: python -m atticus.api_server',
                file=sys.stderr,
            )
            return 1
    elif not _ui_ready(ui_url) and not _wait_for_ui(ui_url, timeout_seconds=2.0):
        print(
            f"No Atticus API responding at {ui_url}. "
            "Start it with: python -m atticus.api_server",
            file=sys.stderr,
        )
        return 1

    if prefer_webview:
        try:
            import webview  # type: ignore[import-not-found]

            window = webview.create_window(
                "Atticus",
                ui_url,
                width=1100,
                height=760,
                background_color="#0b0a09",
            )
            # Keep a reference for type checkers / future hooks.
            _ = window
            webview.start()
            if server is not None and server.poll() is None:
                server.terminate()
            return 0
        except ImportError:
            pass

    opened = webbrowser.open(ui_url)
    print(f"Opened Atticus terminal: {ui_url}")
    if not opened:
        print("Browser open failed; visit the URL manually.", file=sys.stderr)
        return 1
    if server is not None:
        # Detach: leave API running for the browser session.
        print("API left running in the background. Stop it from Task Manager or the tray.")
    return 0


def open_terminal_ui_async(**kwargs: Any) -> None:
    """Fire-and-forget launcher for tray menus."""
    thread = threading.Thread(target=open_terminal_ui, kwargs=kwargs, daemon=True)
    thread.start()
