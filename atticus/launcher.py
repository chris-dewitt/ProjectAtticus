"""Downloadable desktop app entrypoint.

Frozen builds (PyInstaller) and ``python -m atticus.launcher`` open the
classical terminal UI and start the local Atticus API when needed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="Atticus",
        description="Atticus desktop app — The Listener for The Speaker.",
    )
    parser.add_argument("--port", type=int, default=8000, help="Local API port")
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Open system browser instead of native window",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to atticus.yaml",
    )
    args = parser.parse_args(argv)

    try:
        from atticus.ui.web_shell import open_terminal_ui
    except ImportError as exc:
        print(
            'Atticus UI shell unavailable. Install with: pip install -e ".[api,desktop]"',
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    config_path = Path(args.config).expanduser() if args.config else None
    return open_terminal_ui(
        port=args.port,
        config_path=config_path,
        prefer_webview=not args.browser,
        start_server=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
