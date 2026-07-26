from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from atticus.api.app import create_app
from atticus.core.config import AppConfig, load_app_config
from atticus.core.telemetry import Telemetry


@pytest.fixture
def api_client(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "data" / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "data" / "runs.sqlite3")
    cfg.api.docs_enabled = False
    tel = Telemetry(enabled=True, emit_stderr=False, service_name="project-atticus-test")
    app = create_app(config=cfg, config_path=path, telemetry=tel)
    return TestClient(app)


def test_health_live(api_client: TestClient) -> None:
    response = api_client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "project-atticus-test"
    assert "version" in body
    assert response.headers.get("X-Correlation-ID")
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]


def test_health_ready_ok(api_client: TestClient) -> None:
    response = api_client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    names = {check["name"] for check in body["checks"]}
    assert "config" in names
    assert "memory_path" in names
    assert "runs_path" in names
    assert "approvals_path" in names
    assert all(check["ok"] for check in body["checks"])


def test_ready_alias(api_client: TestClient) -> None:
    assert api_client.get("/ready").status_code == 200


def test_preserves_incoming_correlation_id(api_client: TestClient) -> None:
    response = api_client.get("/health/live", headers={"X-Correlation-ID": "boss-42"})
    assert response.headers["X-Correlation-ID"] == "boss-42"
    assert response.json()["correlation_id"] == "boss-42"


def test_docs_disabled_by_default(api_client: TestClient) -> None:
    assert api_client.get("/docs").status_code == 404
    assert api_client.get("/openapi.json").status_code == 404


def test_readiness_not_ready_when_config_missing(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = AppConfig()
    cfg.memory.sqlite_path = str(tmp_path / "mem.sqlite3")
    missing = tmp_path / "missing.yaml"
    tel = Telemetry(enabled=True, emit_stderr=False)
    app = create_app(config=cfg, config_path=missing, telemetry=tel)
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert any(not check["ok"] and check["name"] == "config" for check in body["checks"])


def test_structured_error_body_for_unhandled(
    repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    app = create_app(config=cfg, config_path=path, telemetry=Telemetry(enabled=True))

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("explode")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "explode" not in body["error"]["message"]
    assert body["error"]["correlation_id"]
