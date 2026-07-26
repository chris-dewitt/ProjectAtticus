from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from atticus.api.app import create_app
from atticus.core.config import load_app_config
from atticus.core.telemetry import Telemetry
from atticus.demo.signature import run_signature_demo
from atticus.policy.store import ApprovalStore
from atticus.traces.store import TraceStore


def test_signature_demo_stops_for_approval(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg, _ = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.tools.browser.citation_dir = str(tmp_path / "citations")
    cfg.policy.approvals_sqlite_path = str(tmp_path / "approvals.sqlite3")
    cfg.api.traces_sqlite_path = str(tmp_path / "traces.sqlite3")
    result = run_signature_demo(
        cfg,
        artifacts_dir=tmp_path / "artifacts",
        approval_store=ApprovalStore(Path(cfg.policy.approvals_sqlite_path)),
        trace_store=TraceStore(Path(cfg.api.traces_sqlite_path)),
    )
    assert result.stopped_for_approval is True
    assert result.policy_decision == "require_approval"
    assert result.approval_id
    assert len(result.comparison_table) == 3
    assert result.quality_report["ok"] is True
    assert (tmp_path / "artifacts" / "github_issue_draft.md").is_file()
    assert (tmp_path / "artifacts" / "trace.json").is_file()


def test_signature_demo_api(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.api.traces_sqlite_path = str(tmp_path / "traces.sqlite3")
    cfg.policy.approvals_sqlite_path = str(tmp_path / "approvals.sqlite3")
    cfg.tools.browser.citation_dir = str(tmp_path / "citations")
    cfg.api.rate_limit_per_minute = 0
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False),
        default_provider="mock",
    )
    client = TestClient(app)
    response = client.post("/v1/demo/signature", json={"artifacts_subdir": "demo"})
    assert response.status_code == 200
    body = response.json()
    assert body["quality_report"]["ok"] is True
    assert body["approval_id"]
