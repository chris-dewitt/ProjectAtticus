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
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, service_name="policy-test"),
        run_store=RunStore(Path(cfg.api.runs_sqlite_path)),
        approval_store=ApprovalStore(Path(cfg.policy.approvals_sqlite_path)),
        provider_factory=lambda _name: MockProvider(reply="ok"),
        default_provider="mock",
    )
    return TestClient(app)


def _approval(client: TestClient) -> dict:
    response = client.post(
        "/v1/approvals",
        headers=TOKEN_HEADERS,
        json={
            "tool_name": "file_write",
            "permission_class": "write",
            "action_summary": "Write report.md",
            "inputs": {"path": "report.md", "content_sha256": "abc"},
            "actor": "speaker",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["effect"] == "require_approval"
    assert body["approval"]["status"] == "pending"
    return body["approval"]


def test_policy_allow_and_deny(client: TestClient) -> None:
    allowed = client.post(
        "/v1/policy/evaluate",
        headers=TOKEN_HEADERS,
        json={
            "tool_name": "file_read",
            "permission_class": "safe_read",
            "action_summary": "Read fixture",
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["decision"]["effect"] == "allow"
    assert allowed.json()["approval"] is None

    denied = client.post(
        "/v1/policy/evaluate",
        headers=TOKEN_HEADERS,
        json={
            "tool_name": "calendar_delete",
            "permission_class": "destructive",
            "action_summary": "Delete event",
            "destructive": True,
        },
    )
    assert denied.status_code == 200
    assert denied.json()["decision"]["effect"] == "deny"


def test_approval_decision_is_token_and_phrase_gated(client: TestClient) -> None:
    approval = _approval(client)
    payload = {
        "decision": "approve",
        "actor": "speaker",
        "action_digest": approval["action_digest"],
        "confirmation": f"APPROVE {approval['confirmation_hint']}",
        "rationale": "Exact action reviewed.",
    }
    no_token = client.post(
        f"/v1/approvals/{approval['id']}/decision",
        json=payload,
    )
    assert no_token.status_code == 401
    assert no_token.json()["error"]["code"] == "approval_authentication_failed"

    wrong_phrase = dict(payload, confirmation="APPROVE")
    mismatch = client.post(
        f"/v1/approvals/{approval['id']}/decision",
        json=wrong_phrase,
        headers=TOKEN_HEADERS,
    )
    assert mismatch.status_code == 409

    decided = client.post(
        f"/v1/approvals/{approval['id']}/decision",
        json=payload,
        headers=TOKEN_HEADERS,
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"


def test_list_and_audit(client: TestClient) -> None:
    approval = _approval(client)
    locked = client.get("/v1/approvals?status=pending")
    assert locked.status_code == 401
    listed = client.get("/v1/approvals?status=pending", headers=TOKEN_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == approval["id"]

    unauthenticated = client.get("/v1/audit/policy")
    assert unauthenticated.status_code == 401
    audit = client.get(
        "/v1/audit/policy",
        headers=TOKEN_HEADERS,
    )
    assert audit.status_code == 200
    assert audit.json()["items"]
