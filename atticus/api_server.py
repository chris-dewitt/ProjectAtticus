"""CLI entrypoint for the optional Track B local API server."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atticus-api",
        description=(
            "Run the Track B local API + retro terminal UI "
            "(requires pip install -e '.[api]')."
        ),
    )
    parser.add_argument("--host", default=None, help="Bind host (default from config.api.host)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default from config.api.port)")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to atticus.yaml (else ATTICUS_CONFIG_PATH / example)",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Bind 0.0.0.0 for phone/LAN access (trusted networks only).",
    )
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError:
        print(
            "The API extra is not installed. Run: pip install -e \".[api]\"",
            file=sys.stderr,
        )
        return 1

    from pathlib import Path

    from atticus.api.app import create_app
    from atticus.core.config import load_app_config

    config_path = Path(args.config).expanduser() if args.config else None
    cfg, resolved = load_app_config(config_path=config_path)
    host = "0.0.0.0" if args.lan else (args.host or cfg.api.host)
    port = args.port if args.port is not None else cfg.api.port
    if host in {"0.0.0.0", "::"}:
        print(
            "WARNING: Binding on all interfaces. Use only on a trusted LAN. "
            f"UI: http://<this-machine-ip>:{port}/ui/",
            file=sys.stderr,
        )
    else:
        print(f"Atticus terminal UI: http://{host}:{port}/ui/", file=sys.stderr)
    app = create_app(config=cfg, config_path=resolved)
    uvicorn.run(app, host=host, port=port, log_level=cfg.telemetry.log_level.lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
