"""CLI entrypoint for the optional Track B local API server."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atticus-api",
        description="Run the Track B local health API (requires pip install -e '.[api]').",
    )
    parser.add_argument("--host", default=None, help="Bind host (default from config.api.host)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default from config.api.port)")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to atticus.yaml (else ATTICUS_CONFIG_PATH / example)",
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
    host = args.host or cfg.api.host
    port = args.port if args.port is not None else cfg.api.port
    app = create_app(config=cfg, config_path=resolved)
    uvicorn.run(app, host=host, port=port, log_level=cfg.telemetry.log_level.lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
