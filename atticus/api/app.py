"""FastAPI application factory for Track B health + bounded run APIs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from atticus.api.citations import build_citations_router
from atticus.api.errors import atticus_error_handler, unhandled_error_handler
from atticus.api.health import live_response, load_ready_response
from atticus.api.policy import build_policy_router
from atticus.api.runs import build_runs_router
from atticus.api.schemas import ReadyResponse
from atticus.core.config import AppConfig, load_app_config, resolve_repo_root
from atticus.core.errors import AtticusError, ProviderError
from atticus.core.router import ProviderRouter
from atticus.core.telemetry import (
    Telemetry,
    bind_correlation_id,
    get_telemetry,
    set_telemetry,
)
from atticus.providers.base import LLMProvider
from atticus.providers.mock_provider import MockProvider
from atticus.policy.dispatch import ToolGateway
from atticus.policy.engine import PolicyEngine
from atticus.policy.service import PolicyService
from atticus.policy.store import ApprovalStore
from atticus.runs.orchestrator import BoundedRunOrchestrator
from atticus.runs.store import RunStore


def create_app(
    *,
    config: AppConfig | None = None,
    config_path: Path | None = None,
    telemetry: Telemetry | None = None,
    run_store: RunStore | None = None,
    approval_store: ApprovalStore | None = None,
    provider_factory: Callable[[str], LLMProvider] | None = None,
    default_provider: str | None = None,
) -> FastAPI:
    """Build the Track B API app (health + M1 conversations/runs)."""
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
        version="0.5.0",
        description=(
            "Track B local API: health, bounded runs, citations, policy/approvals, "
            "idempotent approved-tool dispatch, and optional retro /ui. "
            "Traces remain a later milestone."
        ),
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url="/openapi.json" if config.api.docs_enabled else None,
    )
    app.state.config = config
    app.state.config_path = resolved_path
    app.state.service_name = service_name
    app.state.default_provider = (
        default_provider or config.providers.routing.default_provider
    ).lower()
    app.state.default_mode = config.assistant.default_mode

    if run_store is None:
        run_store = RunStore(Path(config.api.runs_sqlite_path).expanduser())
    app.state.run_store = run_store

    if approval_store is None:
        approval_store = ApprovalStore(
            Path(config.policy.approvals_sqlite_path).expanduser()
        )
    app.state.approval_store = approval_store
    app.state.policy_service = PolicyService(
        PolicyEngine(config),
        approval_store,
        approval_ttl_seconds=config.policy.approval_ttl_seconds,
    )
    app.state.tool_gateway = ToolGateway(config, approval_store)

    if provider_factory is None:
        router = ProviderRouter(config)

        def _factory(name: str) -> LLMProvider:
            key = name.lower()
            if key == "mock":
                return MockProvider()
            if key != router.current:
                try:
                    router.set_provider(key)
                except ValueError as exc:
                    raise ProviderError(str(exc), code="invalid_provider", status_code=400) from exc
            return router.active_provider()

        provider_factory = _factory

    repo_root = resolve_repo_root(config, config_file=resolved_path)
    app.state.orchestrator = BoundedRunOrchestrator(
        run_store,
        provider_factory=provider_factory,
        repo_root=repo_root,
        max_messages=config.api.max_messages_per_run,
        include_system_prompt=config.api.include_system_prompt,
    )

    app.add_exception_handler(AtticusError, atticus_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(build_runs_router())
    app.include_router(build_citations_router())
    app.include_router(build_policy_router())

    static_dir = Path(__file__).resolve().parent / "static" / "retro"
    if config.api.ui_enabled and static_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="retro_ui")

        @app.get("/")
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

        @app.get("/terminal")
        async def terminal_alias() -> FileResponse:
            return FileResponse(static_dir / "index.html")

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
