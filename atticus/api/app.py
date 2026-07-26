"""FastAPI application factory for Track B M0 health endpoints."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from atticus.api.errors import atticus_error_handler, unhandled_error_handler
from atticus.api.health import live_response, load_ready_response
from atticus.api.schemas import ReadyResponse
from atticus.core.config import AppConfig, load_app_config
from atticus.core.errors import AtticusError
from atticus.core.telemetry import (
    Telemetry,
    bind_correlation_id,
    get_telemetry,
    set_telemetry,
)


def create_app(
    *,
    config: AppConfig | None = None,
    config_path: Path | None = None,
    telemetry: Telemetry | None = None,
) -> FastAPI:
    """Build the Track B API app (health/readiness only in M0)."""
    if config is None:
        config, resolved_path = load_app_config(config_path=config_path)
    else:
        resolved_path = config_path

    if telemetry is not None:
        set_telemetry(telemetry)
        service_name = telemetry.service_name
    else:
        service_name = config.telemetry.service_name
        set_telemetry(
            Telemetry(
                enabled=config.telemetry.enabled,
                service_name=service_name,
                environment=config.telemetry.environment,
                emit_stderr=config.telemetry.emit_stderr,
                redact_keys=set(config.telemetry.redact_keys),
            )
        )

    docs_url = "/docs" if config.api.docs_enabled else None
    redoc_url = "/redoc" if config.api.docs_enabled else None
    app = FastAPI(
        title="ProjectAtticus API",
        version="0.1.0",
        description="Track B M0 health/readiness API. Conversations/runs are not exposed yet.",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url="/openapi.json" if config.api.docs_enabled else None,
    )
    app.state.config = config
    app.state.config_path = resolved_path
    app.state.service_name = service_name

    app.add_exception_handler(AtticusError, atticus_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next: Any) -> Response:
        incoming = request.headers.get("x-correlation-id")
        started = time.perf_counter()
        with bind_correlation_id(incoming) as correlation_id:
            request.state.correlation_id = correlation_id
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            get_telemetry().emit(
                "api.request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
            )
            return response

    @app.get("/health/live")
    async def health_live() -> dict[str, Any]:
        return live_response(service_name=app.state.service_name).model_dump()

    @app.get("/health/ready")
    async def health_ready() -> JSONResponse:
        payload = load_ready_response(
            config_path=app.state.config_path,
            service_name=app.state.service_name,
        )
        return _ready_json(payload)

    @app.get("/ready")
    async def ready_alias() -> JSONResponse:
        payload = load_ready_response(
            config_path=app.state.config_path,
            service_name=app.state.service_name,
        )
        return _ready_json(payload)

    return app


def _ready_json(payload: ReadyResponse) -> JSONResponse:
    status_code = 200 if payload.status == "ready" else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump())
