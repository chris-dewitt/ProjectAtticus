"""HTTP entry for the Track B signature demo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from atticus.core.telemetry import get_telemetry
from atticus.demo.signature import run_signature_demo
from atticus.policy.store import ApprovalStore
from atticus.traces.store import TraceStore


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifacts_subdir: str = Field(default="signature_demo", max_length=80)


def build_demo_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["demo"])

    @router.post("/demo/signature")
    async def signature_demo(request: Request, body: DemoRequest | None = None) -> dict[str, Any]:
        cfg = request.app.state.config
        body = body or DemoRequest()
        artifacts = Path("data") / "artifacts" / body.artifacts_subdir
        approval_store: ApprovalStore = request.app.state.approval_store
        trace_store: TraceStore = request.app.state.trace_store
        result = run_signature_demo(
            cfg,
            artifacts_dir=artifacts,
            approval_store=approval_store,
            trace_store=trace_store,
        )
        get_telemetry().emit("api.signature_demo", run_id=result.run_id, ok=result.quality_report.get("ok"))
        return result.to_dict()

    return router
