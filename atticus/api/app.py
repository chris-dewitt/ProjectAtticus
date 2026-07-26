"""FastAPI application factory for Track A/B local platform API."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Ensure PWA assets are served with useful content types on Windows.
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/javascript", ".js")

from atticus.api.auth import ApiAuthMiddleware, RateLimitMiddleware
from atticus.api.citations import build_citations_router
from atticus.api.demo import build_demo_router
from atticus.api.errors import atticus_error_handler, unhandled_error_handler
from atticus.api.evals_api import build_evals_router
from atticus.api.health import live_response, load_ready_response
from atticus.api.memory_api import build_memory_router
from atticus.api.policy import build_policy_router
from atticus.api.runs import build_runs_router
from atticus.api.sandbox import build_sandbox_router
from atticus.api.schemas import ReadyResponse
from atticus.api.settings import build_settings_router
from atticus.api.traces import build_traces_router
from atticus.core.config import AppConfig, load_app_config, resolve_repo_root
from atticus.core.errors import AtticusError, ProviderError
from atticus.core.router import ProviderRouter
from atticus.core.telemetry import (
    Telemetry,
    bind_correlation_id,
    get_telemetry,
    set_telemetry,
)
from atticus.memory.store import MemoryStore
from atticus.policy.dispatch import ToolGateway
from atticus.policy.engine import PolicyEngine
from atticus.policy.service import PolicyService
from atticus.policy.store import ApprovalStore
from atticus.providers.base import LLMProvider
from atticus.providers.mock_provider import MockProvider
from atticus.runs.orchestrator import BoundedRunOrchestrator
from atticus.runs.store import RunStore
from atticus.sandbox.runner import SandboxRunner
from atticus.traces.store import TraceStore


def create_app(
    *,
    config: AppConfig | None = None,
    config_path: Path | None = None,
    telemetry: Telemetry | None = None,
    run_store: RunStore | None = None,
    approval_store: ApprovalStore | None = None,
    trace_store: TraceStore | None = None,
    provider_factory: Callable[[str], LLMProvider] | None = None,
    default_provider: str | None = None,
) -> FastAPI:
    """Build the local API app (health, runs, citations, policy, traces, demo)."""
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
                otel_exporter=config.telemetry.otel_exporter,
                otel_file_path=config.telemetry.otel_file_path,
                redact_keys=set(config.telemetry.redact_keys),
            )
        )

    docs_url = "/docs" if config.api.docs_enabled else None
    redoc_url = "/redoc" if config.api.docs_enabled else None
    app = FastAPI(
        title="ProjectAtticus API",
        version="1.1.0",
        description=(
            "Local-first Atticus API: conversations/runs, citations, policy/approvals, "
            "idempotent dispatch, traces/replay, sandbox, memory controls, evals, "
            "signature demo, and retro /ui."
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

    if trace_store is None:
        trace_store = TraceStore(Path(config.api.traces_sqlite_path).expanduser())
    app.state.trace_store = trace_store

    app.state.memory_store = MemoryStore(Path(config.memory.sqlite_path).expanduser())
    app.state.sandbox_runner = SandboxRunner(
        work_dir=Path(config.sandbox.work_dir).expanduser(),
        timeout_seconds=config.sandbox.timeout_seconds,
        max_output_bytes=config.sandbox.max_output_bytes,
        allow_shell=config.sandbox.allow_shell,
    )

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
            if config.providers.routing.automatic:
                return router.resolve_with_fallback(key)
            return router.active_provider()

        provider_factory = _factory

    repo_root = resolve_repo_root(config, config_file=resolved_path)
    app.state.orchestrator = BoundedRunOrchestrator(
        run_store,
        provider_factory=provider_factory,
        repo_root=repo_root,
        max_messages=config.api.max_messages_per_run,
        include_system_prompt=config.api.include_system_prompt,
        trace_store=trace_store,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        per_minute=config.api.rate_limit_per_minute,
    )
    app.add_middleware(
        ApiAuthMiddleware,
        token_env=config.api.api_token_env,
    )

    app.add_exception_handler(AtticusError, atticus_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(build_runs_router())
    app.include_router(build_citations_router())
    app.include_router(build_policy_router())
    app.include_router(build_traces_router())
    app.include_router(build_sandbox_router())
    app.include_router(build_memory_router())
    app.include_router(build_settings_router())
    app.include_router(build_demo_router())
    app.include_router(build_evals_router())

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
