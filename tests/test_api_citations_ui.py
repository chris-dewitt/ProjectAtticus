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
from atticus.services import citations as cite_svc


@pytest.fixture
def client(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    cfg, path = load_app_config(config_path=repo_root / "config" / "atticus.example.yaml")
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.api.runs_sqlite_path = str(tmp_path / "runs.sqlite3")
    cfg.api.include_system_prompt = False
    cfg.api.ui_enabled = True
    cfg.tools.browser.citation_dir = str(tmp_path / "citations")
    store = RunStore(Path(cfg.api.runs_sqlite_path))
    app = create_app(
        config=cfg,
        config_path=path,
        telemetry=Telemetry(enabled=True, emit_stderr=False, service_name="ui-test"),
        run_store=store,
        provider_factory=lambda _name: MockProvider(reply="Link established, Boss."),
        default_provider="mock",
    )
    return TestClient(app)


def test_retro_ui_is_served(client: TestClient) -> None:
    root = client.get("/", follow_redirects=False)
    assert root.status_code in {307, 302}
    page = client.get("/ui/")
    assert page.status_code == 200
    assert "ATTICUS" in page.text
    css = client.get("/ui/styles.css")
    assert css.status_code == 200
    assert "--phosphor" in css.text
    js = client.get("/ui/app.js")
    assert js.status_code == 200


def test_citations_api_lists_records(client: TestClient, tmp_path: Path) -> None:
    cite_dir = tmp_path / "citations"
    source = tmp_path / "readme.txt"
    source.write_text("green phosphor forever\n", encoding="utf-8")
    record = cite_svc.from_local_file(path=source, text=source.read_text(), max_bytes=1000)
    cite_svc.save_record(record, cite_dir)

    listed = client.get("/v1/citations")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items
    assert items[0]["id"].startswith("cit_")

    got = client.get(f"/v1/citations/{items[0]['id']}")
    assert got.status_code == 200
    assert got.json()["kind"] == "local_file"


def test_missing_citation_is_404(client: TestClient) -> None:
    response = client.get("/v1/citations/cit_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "citation_not_found"
