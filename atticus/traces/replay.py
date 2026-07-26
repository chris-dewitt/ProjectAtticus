"""Replay helpers: rebuild inspectable plan/tool/approval artifacts from a run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atticus.runs.models import RunRecord
from atticus.runs.store import RunStore
from atticus.traces.store import TraceStore


@dataclass
class ReplayReport:
    """Deterministic reconstruction of a completed (or failed) run."""

    run_id: str
    status: str
    provider: str
    mode: str
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    spans: list[dict[str, Any]] = field(default_factory=list)
    input_messages: list[dict[str, str]] = field(default_factory=list)
    output_text: str | None = None
    error: dict[str, str] | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "provider": self.provider,
            "mode": self.mode,
            "checkpoints": list(self.checkpoints),
            "spans": list(self.spans),
            "input_messages": list(self.input_messages),
            "output_text": self.output_text,
            "error": self.error,
            "artifacts": dict(self.artifacts),
        }


def build_replay_report(
    run_store: RunStore,
    trace_store: TraceStore,
    run_id: str,
) -> ReplayReport:
    """Assemble a replay report from persisted run + trace state."""
    run: RunRecord = run_store.get_run(run_id)
    try:
        spans = [s.to_public_dict() for s in trace_store.list_spans(run_id)]
    except Exception:  # noqa: BLE001 — empty traces are valid for older runs
        spans = []
    error = None
    if run.error_code:
        error = {"code": run.error_code, "message": run.error_message or ""}
    artifacts: dict[str, Any] = {
        "checkpoint_names": [c.name for c in run.checkpoints],
        "span_kinds": sorted({s["kind"] for s in spans}),
        "cancel_requested": run.cancel_requested,
        "correlation_id": run.correlation_id,
    }
    return ReplayReport(
        run_id=run.id,
        status=run.status.value,
        provider=run.provider,
        mode=run.mode,
        checkpoints=[
            {"name": c.name, "at": c.at, "detail": dict(c.detail)} for c in run.checkpoints
        ],
        spans=spans,
        input_messages=list(run.input_messages),
        output_text=run.output_text,
        error=error,
        artifacts=artifacts,
    )
