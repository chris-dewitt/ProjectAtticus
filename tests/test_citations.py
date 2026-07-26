from __future__ import annotations

import json
from pathlib import Path

from atticus.services import citations as cite_svc
from atticus.services import web_browse as browse_svc


def test_web_citation_is_structured_v1(tmp_path: Path) -> None:
    page = browse_svc.PageCitation(
        url="https://example.com/docs",
        title="Example Docs",
        retrieved_at="2026-07-26T00:00:00+00:00",
        excerpt="Hello world…",
        status_code=200,
        content_type="text/html",
    )
    saved = browse_svc.save_citation(page, tmp_path)
    assert saved.citation_id
    assert saved.saved_path
    payload = json.loads(Path(saved.saved_path).read_text(encoding="utf-8"))
    assert payload["schema_version"] == cite_svc.SCHEMA_VERSION
    assert payload["id"].startswith("cit_")
    assert payload["kind"] == "web_page"
    assert payload["content_sha256"]
    assert payload["untrusted_external_content"] is True


def test_legacy_citation_normalizes(tmp_path: Path) -> None:
    legacy = {
        "url": "https://example.com/old",
        "title": "Old",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
        "excerpt": "legacy excerpt",
        "status_code": 200,
        "content_type": "text/html",
        "saved_path": str(tmp_path / "legacy.json"),
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    record = cite_svc.load_record(path)
    assert record.schema_version == cite_svc.SCHEMA_VERSION
    assert record.source_uri.endswith("/old")
    assert record.tool_name == "browse_fetch"


def test_local_file_and_code_search_citations(tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("Boss likes green terminals.\n", encoding="utf-8")
    file_rec = cite_svc.from_local_file(path=source, text=source.read_text(), max_bytes=10_000)
    saved = cite_svc.save_record(file_rec, tmp_path / "citations")
    assert saved.kind == "local_file"
    assert saved.sensitivity == "local_sensitive"

    code_rec = cite_svc.from_code_search(
        path=source,
        line="Boss likes green terminals.",
        pattern="Boss",
        line_no=1,
    )
    cite_svc.save_record(code_rec, tmp_path / "citations")
    listed = cite_svc.list_records(tmp_path / "citations", limit=10)
    assert len(listed) >= 2
    loaded = cite_svc.get_record(tmp_path / "citations", saved.id)
    assert loaded.id == saved.id
