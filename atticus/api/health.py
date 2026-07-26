"""Liveness and readiness checks for the Track B M0 API."""

from __future__ import annotations

from pathlib import Path

from atticus import __version__
from atticus.api.schemas import LiveResponse, ReadyCheck, ReadyResponse
from atticus.core.config import AppConfig, load_app_config
from atticus.core.errors import ConfigurationError
from atticus.core.telemetry import get_correlation_id, get_telemetry


def live_response(*, service_name: str) -> LiveResponse:
    return LiveResponse(
        service=service_name,
        version=__version__,
        correlation_id=get_correlation_id() or "",
    )


def evaluate_readiness(
    cfg: AppConfig,
    *,
    config_path: Path,
    service_name: str,
) -> ReadyResponse:
    """Local-only readiness: config loaded and memory parent path usable."""
    checks: list[ReadyCheck] = []
    checks.append(
        ReadyCheck(
            name="config",
            ok=config_path.is_file(),
            detail=str(config_path),
        )
    )

    memory_path = Path(cfg.memory.sqlite_path).expanduser()
    parent = memory_path.parent if memory_path.parent != Path("") else Path(".")
    try:
        parent.mkdir(parents=True, exist_ok=True)
        writable = parent.is_dir() and os_access_write(parent)
        checks.append(
            ReadyCheck(
                name="memory_path",
                ok=writable,
                detail=str(memory_path),
            )
        )
    except OSError as exc:
        checks.append(
            ReadyCheck(
                name="memory_path",
                ok=False,
                detail=f"unavailable: {exc.__class__.__name__}",
            )
        )

    ready = all(check.ok for check in checks)
    status = "ready" if ready else "not_ready"
    get_telemetry().emit(
        "api.readiness",
        status=status,
        checks_ok=sum(1 for check in checks if check.ok),
        checks_total=len(checks),
    )
    return ReadyResponse(
        status=status,
        service=service_name,
        version=__version__,
        correlation_id=get_correlation_id() or "",
        checks=checks,
    )


def load_ready_response(
    *,
    config_path: Path | None,
    service_name: str,
) -> ReadyResponse:
    """Return readiness payload; prefer structured not_ready over exceptions."""
    if config_path is not None and not config_path.is_file():
        # Skip example-config fallback so readiness reflects the configured path.
        get_telemetry().emit("api.readiness", status="not_ready", reason="config_missing")
        return ReadyResponse(
            status="not_ready",
            service=service_name,
            version=__version__,
            correlation_id=get_correlation_id() or "",
            checks=[
                ReadyCheck(
                    name="config",
                    ok=False,
                    detail=str(config_path),
                )
            ],
        )
    try:
        cfg, resolved = load_app_config(config_path=config_path)
    except ConfigurationError as exc:
        get_telemetry().emit("api.readiness", status="not_ready", reason="config_invalid")
        return ReadyResponse(
            status="not_ready",
            service=service_name,
            version=__version__,
            correlation_id=get_correlation_id() or "",
            checks=[
                ReadyCheck(
                    name="config",
                    ok=False,
                    detail=exc.message,
                )
            ],
        )
    return evaluate_readiness(cfg, config_path=resolved, service_name=service_name)


def os_access_write(path: Path) -> bool:
    import os

    return os.access(path, os.W_OK)
