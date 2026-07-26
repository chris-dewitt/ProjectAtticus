from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from atticus.api.app import create_app
from atticus.core.config import load_app_config
from atticus.core.telemetry import Telemetry
from atticus.providers.mock_provider import MockProvider
from atticus.runs.store import RunStore
from atticus.traces.store import TraceStore


@pytest.fixture
def client(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.api.traces_sqlite_path = str(tmp_path / "traces.sqlite3")
    cfg.policy.approvals_sqlite_path = str(tmp_path / "approvals.sqlite3")
    cfg.api.include_system_prompt = False
    cfg.api.rate_limit_per_minute = 0
    store = RunStore(Path(cfg.api.runs_sqlite_path))
    traces = TraceStore(Path(cfg.api.traces_sqlite_path))
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False, service_name="trace-test"),
        run_store=store,
        trace_store=traces,
        provider_factory=lambda _name: MockProvider(reply="Traced reply."),
        default_provider="mock",
    )
    return TestClient(app)


def test_run_emits_trace_and_replay(client: TestClient) -> None:
    created = client.post("/v1/conversations", json={"title": "trace"})
    conversation_id = created.json()["id"]
    posted = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"content": "Trace me", "execute": True},
        headers={"Idempotency-Key": "trace-1"},
    )
    assert posted.status_code == 200
    run_id = posted.json()["run"]["id"]

    trace = client.get(f"/v1/traces/{run_id}")
    assert trace.status_code == 200
    body = trace.json()
    assert body["span_count"] >= 1
    kinds = {s["kind"] for s in body["spans"]}
    assert "run" in kinds
    assert "provider" in kinds

    replay = client.get(f"/v1/runs/{run_id}/replay")
    assert replay.status_code == 200
    report = replay.json()
    assert report["status"] == "succeeded"
    assert report["output_text"] == "Traced reply."
    assert any(c["name"] == "finalize" for c in report["checkpoints"])
