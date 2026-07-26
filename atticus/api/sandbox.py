"""HTTP routes for sandboxed execution (Track B M4)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from atticus.core.telemetry import get_telemetry
from atticus.sandbox.runner import SandboxRunner
from atticus.traces.models import SpanKind
from atticus.traces.store import TraceStore


class SandboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["python", "shell"] = "python"
    source: str = Field(min_length=1, max_length=20_000)
    run_id: str | None = Field(default=None, max_length=80)


def build_sandbox_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["sandbox"])

    @router.post("/sandbox/execute")
    async def execute_sandbox(request: Request, body: SandboxRequest) -> dict[str, Any]:
        from atticus.sandbox.runner import SandboxDenied

        if not request.app.state.config.sandbox.enabled:
            raise SandboxDenied("Sandbox execution is disabled in configuration.")
        runner: SandboxRunner = request.app.state.sandbox_runner
        trace_store: TraceStore = request.app.state.trace_store
        run_id = body.run_id or "sandbox_ad_hoc"
        span = trace_store.start_span(
            run_id=run_id,
            name=f"sandbox.{body.kind}",
            kind=SpanKind.SANDBOX,
            attributes={"kind": body.kind, "source_chars": len(body.source)},
        )
        try:
            if body.kind == "python":
                result = runner.run_python(body.source)
            else:
                result = runner.run_shell(body.source)
            trace_store.end_span(
                span.id,
                status=result.status,
                attributes={"exit_code": result.exit_code, "duration_ms": result.duration_ms},
            )
        except Exception:
            trace_store.end_span(span.id, status="error")
            raise
        get_telemetry().emit(
            "api.sandbox_execute",
            kind=body.kind,
            status=result.status,
            run_id=run_id,
        )
        payload = result.to_dict()
        payload["span_id"] = span.id
        payload["run_id"] = run_id
        return payload

    return router
