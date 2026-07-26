"""HTTP routes for traces and replay (Track B M4)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from atticus.core.telemetry import get_telemetry
from atticus.runs.store import RunStore
from atticus.traces.replay import build_replay_report
from atticus.traces.store import TraceStore


def build_traces_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["traces"])

    @router.get("/traces/{run_id}")
    async def get_trace(request: Request, run_id: str) -> dict[str, Any]:
        run_store: RunStore = request.app.state.run_store
        # Ensure the run exists (404 if not).
        run_store.get_run(run_id)
        trace_store: TraceStore = request.app.state.trace_store
        try:
            payload = trace_store.get_trace(run_id)
        except Exception:
            # Empty trace is still a valid inspectable response once the run exists.
            payload = {"run_id": run_id, "span_count": 0, "spans": []}
        get_telemetry().emit("api.trace_fetched", run_id=run_id, span_count=payload["span_count"])
        return payload

    @router.get("/runs/{run_id}/replay")
    async def replay_run(request: Request, run_id: str) -> dict[str, Any]:
        run_store: RunStore = request.app.state.run_store
        trace_store: TraceStore = request.app.state.trace_store
        report = build_replay_report(run_store, trace_store, run_id)
        get_telemetry().emit("api.replay_built", run_id=run_id)
        return report.to_public_dict()

    return router
