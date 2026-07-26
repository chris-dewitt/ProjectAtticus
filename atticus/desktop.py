"""Phase 9 desktop/tray/autostart entrypoint."""

from __future__ import annotations

import argparse
import sys

from atticus.core.errors import AtticusError
from atticus.services import windows_autostart


def _confirm_exact(prompt: str, token: str) -> bool:
    return input(prompt).strip() == token


def _run_desk() -> None:
    try:
        from atticus.ui.textual_app import run_desktop
    except ImportError as exc:
        raise SystemExit(
            'Install the desktop extra: pip install -e ".[desktop]"'
        ) from exc
    run_desktop()


def _run_tray() -> None:
    try:
        from atticus.ui.tray import run_tray
    except ImportError as exc:
        raise SystemExit(
            'Install the desktop extra: pip install -e ".[desktop]"'
        ) from exc
    run_tray()


def _run_ui(*, port: int, browser: bool) -> int:
    from atticus.launcher import main as launcher_main

    argv = ["--port", str(port)]
    if browser:
        argv.append("--browser")
    return launcher_main(argv)


def _autostart(action: str) -> int:
    current = windows_autostart.status()
    if action == "status":
        print(f"Autostart supported: {current.supported}")
        print(f"Autostart enabled: {current.enabled}")
        print(f"Launcher: {current.path or '(unavailable)'}")
        print(current.detail)
        return 0 if current.supported else 2

    if not current.supported:
        print(current.detail)
        return 2

    if action == "enable":
        target = current.path
        print("Atticus will create this Windows Startup launcher:")
        print(f"  {target}")
        print(f"It launches: {sys.executable} -m atticus.desktop tray")
        if not _confirm_exact("Type ENABLE to create it: ", "ENABLE"):
            print("Cancelled. Nothing changed.")
            return 1
        path = windows_autostart.enable(python_executable=sys.executable)
        print(f"Autostart enabled: {path}")
        return 0

    print("Atticus will remove only its own Windows Startup launcher:")
    print(f"  {current.path}")
    if not _confirm_exact("Type DISABLE to remove it: ", "DISABLE"):
        print("Cancelled. Nothing changed.")
        return 1
    changed = windows_autostart.disable()
    print("Autostart disabled." if changed else "Autostart was already disabled.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="atticus-desktop",
        description="Atticus desktop UI, tray, and autostart manager.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("desk", help="Open the Textual status desk.")
    ui = sub.add_parser(
        "ui",
        help="Open the classical terminal UI (starts local API if needed).",
    )
    ui.add_argument("--port", type=int, default=8000, help="API port (default 8000)")
    ui.add_argument(
        "--browser",
        action="store_true",
        help="Force system browser instead of native window (pywebview).",
    )
    sub.add_parser("tray", help="Run the Windows system tray.")
    auto = sub.add_parser("autostart", help="Manage the Windows Startup launcher.")
    auto.add_argument("action", choices=("status", "enable", "disable"))
    args = parser.parse_args()

    try:
        if args.command in {None, "ui"}:
            # Default desktop entry opens the classical terminal UI.
            raise SystemExit(_run_ui(port=getattr(args, "port", 8000), browser=bool(getattr(args, "browser", False))))
        if args.command == "desk":
            _run_desk()
        elif args.command == "tray":
            _run_tray()
        elif args.command == "autostart":
            raise SystemExit(_autostart(args.action))
    except AtticusError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
