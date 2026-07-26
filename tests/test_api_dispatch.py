from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from atticus.api.app import create_app
from atticus.core.config import load_app_config
from atticus.core.telemetry import Telemetry
from atticus.policy.store import ApprovalStore
from atticus.providers.mock_provider import MockProvider
from atticus.runs.store import RunStore

TOKEN_HEADERS = {"X-Atticus-Approval-Token": "test-token-do-not-use"}


@pytest.fixture
def client(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ATTICUS_APPROVAL_TOKEN", "test-token-do-not-use")
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.policy.approvals_sqlite_path = str(tmp_path / "approvals.sqlite3")
    cfg.api.include_system_prompt = False
    cfg.tools.enabled = True
    cfg.tools.files.enabled = True
    cfg.tools.approved_paths = [str(tmp_path)]
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, service_name="dispatch-test"),
        run_store=RunStore(Path(cfg.api.runs_sqlite_path)),
        approval_store=ApprovalStore(Path(cfg.policy.approvals_sqlite_path)),
        provider_factory=lambda _name: MockProvider(reply="ok"),
        default_provider="mock",
    )
    return TestClient(app)


def _approve_echo(client: TestClient) -> dict:
    created = client.post(
        "/v1/approvals",
        headers=TOKEN_HEADERS,
        json={
            "tool_name": "local_echo",
            "permission_class": "write",
            "action_summary": "Echo hello",
            "inputs": {"message": "hello from gateway"},
            "actor": "speaker",
        },
    )
    assert created.status_code == 200
    approval = created.json()["approval"]
    decided = client.post(
        f"/v1/approvals/{approval['id']}/decision",
        headers=TOKEN_HEADERS,
        json={
            "decision": "approve",
            "actor": "speaker",
            "action_digest": approval["action_digest"],
            "confirmation": f"APPROVE {approval['confirmation_hint']}",
        },
    )
    assert decided.status_code == 200
    return decided.json()


def test_execute_requires_idempotency_key(client: TestClient) -> None:
    approval = _approve_echo(client)
    missing = client.post(
        f"/v1/approvals/{approval['id']}/execute",
        headers=TOKEN_HEADERS,
        json={"actor": "atticus"},
    )
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "dispatch_denied"


def test_execute_and_replay(client: TestClient) -> None:
    approval = _approve_echo(client)
    headers = {**TOKEN_HEADERS, "Idempotency-Key": "dispatch-1"}
    first = client.post(
        f"/v1/approvals/{approval['id']}/execute",
        headers=headers,
        json={"actor": "atticus"},
    )
    assert first.status_code == 200
    body = first.json()
    assert body["replayed"] is False
    assert body["result"]["echo"] == "hello from gateway"

    second = client.post(
        f"/v1/approvals/{approval['id']}/execute",
        headers=headers,
        json={"actor": "atticus"},
    )
    assert second.status_code == 200
    assert second.json()["replayed"] is True
    assert second.json()["result"] == body["result"]
