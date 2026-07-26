from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from atticus.api.app import create_app
from atticus.core.config import load_app_config
from atticus.core.telemetry import Telemetry


@pytest.fixture
def base_cfg(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.api.traces_sqlite_path = str(tmp_path / "traces.sqlite3")
    cfg.policy.approvals_sqlite_path = str(tmp_path / "approvals.sqlite3")
    cfg.api.rate_limit_per_minute = 0
    return cfg, path


def test_memory_remember_search_forget(base_cfg) -> None:
    cfg, path = base_cfg
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False),
        default_provider="mock",
    )
    client = TestClient(app)
    remembered = client.post("/v1/memory/remember", json={"text": "Boss likes concise reports", "kind": "preference"})
    assert remembered.status_code == 200
    search = client.get("/v1/memory/search", params={"q": "concise"})
    assert search.status_code == 200
    assert search.json()["items"]
    forgotten = client.post("/v1/memory/forget", json={"query": "concise", "clear_all_matching": True})
    assert forgotten.status_code == 200
    assert forgotten.json()["removed"] >= 1


def test_settings_get_and_patch(base_cfg) -> None:
    cfg, path = base_cfg
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False),
        default_provider="mock",
    )
    client = TestClient(app)
    got = client.get("/v1/settings")
    assert got.status_code == 200
    assert "assistant" in got.json()
    patched = client.patch("/v1/settings", json={"spoken_responses": True, "default_mode": "coding_partner"})
    assert patched.status_code == 200
    assert "voice.spoken_responses" in patched.json()["changed"]


def test_api_token_required_when_set(base_cfg, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, path = base_cfg
    monkeypatch.setenv("ATTICUS_API_TOKEN", "test-api-token")
    cfg.api.api_token_env = "ATTICUS_API_TOKEN"
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False),
        default_provider="mock",
    )
    client = TestClient(app)
    denied = client.get("/v1/settings")
    assert denied.status_code == 401
    ok = client.get("/v1/settings", headers={"X-Atticus-Api-Token": "test-api-token"})
    assert ok.status_code == 200
    # Health stays public.
    assert client.get("/health/live").status_code == 200


def test_evals_platform_suite(base_cfg) -> None:
    cfg, path = base_cfg
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False),
        default_provider="mock",
    )
    client = TestClient(app)
    response = client.post("/v1/evals/run?suite=platform")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["failed"] == 0
