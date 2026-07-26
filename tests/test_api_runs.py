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


@pytest.fixture
def client(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.api.include_system_prompt = False
    store = RunStore(Path(cfg.api.runs_sqlite_path))
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False, service_name="runs-test"),
        run_store=store,
        provider_factory=lambda _name: MockProvider(reply="Steady as she goes, Speaker."),
        default_provider="mock",
    )
    return TestClient(app)


def test_conversation_message_run_flow(client: TestClient) -> None:
    created = client.post("/v1/conversations", json={"title": "demo"})
    assert created.status_code == 200
    conversation_id = created.json()["id"]

    posted = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"content": "Status report?", "execute": True},
        headers={"Idempotency-Key": "msg-1"},
    )
    assert posted.status_code == 200
    body = posted.json()
    assert body["message"]["content"] == "Status report?"
    assert body["run"]["status"] == "succeeded"
    assert body["run"]["output_text"] == "Steady as she goes, Speaker."
    run_id = body["run"]["id"]

    got = client.get(f"/v1/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["id"] == run_id
    assert any(c["name"] == "finalize" for c in got.json()["checkpoints"])

    again = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"content": "Status report?", "execute": True},
        headers={"Idempotency-Key": "msg-1"},
    )
    assert again.status_code == 200
    assert again.json()["run"]["id"] == run_id


def test_create_run_direct_and_cancel_queued(client: TestClient) -> None:
    created = client.post(
        "/v1/runs",
        json={
            "messages": [{"role": "user", "content": "Hold up"}],
            "execute": False,
            "provider": "mock",
        },
    )
    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "queued"
    cancelled = client.post(f"/v1/runs/{run['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_cancel_terminal_conflicts(client: TestClient) -> None:
    created = client.post(
        "/v1/runs",
        json={
            "messages": [{"role": "user", "content": "Go"}],
            "execute": True,
            "provider": "mock",
        },
    )
    run_id = created.json()["id"]
    response = client.post(f"/v1/runs/{run_id}/cancel")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "run_conflict"


def test_missing_run_is_structured_404(client: TestClient) -> None:
    response = client.get("/v1/runs/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"
