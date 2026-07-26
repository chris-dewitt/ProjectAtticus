from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from atticus.api.app import create_app
from atticus.core.config import load_app_config
from atticus.core.telemetry import Telemetry
from atticus.sandbox.runner import SandboxRunner


@pytest.fixture
def client(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.api.traces_sqlite_path = str(tmp_path / "traces.sqlite3")
    cfg.policy.approvals_sqlite_path = str(tmp_path / "approvals.sqlite3")
    cfg.sandbox.work_dir = str(tmp_path / "sandbox")
    cfg.api.rate_limit_per_minute = 0
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False),
        default_provider="mock",
    )
    return TestClient(app)


def test_python_sandbox_ok(client: TestClient) -> None:
    response = client.post(
        "/v1/sandbox/execute",
        json={"kind": "python", "source": "print(2 + 2)\n"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "4" in body["stdout"]


def test_python_sandbox_blocks_import(client: TestClient) -> None:
    response = client.post(
        "/v1/sandbox/execute",
        json={"kind": "python", "source": "import os\nprint(os.getcwd())\n"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "sandbox_denied"


def test_shell_disabled_by_default(client: TestClient) -> None:
    response = client.post(
        "/v1/sandbox/execute",
        json={"kind": "shell", "source": "echo hi"},
    )
    assert response.status_code == 400


def test_runner_unit_math() -> None:
    runner = SandboxRunner(timeout_seconds=3.0)
    result = runner.run_python("print(sum(range(5)))")
    assert result.status == "ok"
    assert "10" in result.stdout
