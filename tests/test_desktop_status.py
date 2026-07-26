from __future__ import annotations

from pathlib import Path

from atticus.core.config import AppConfig
from atticus.memory.store import MemoryStore
from atticus.services.desktop_status import build_snapshot, read_memory_counts
from atticus.services.windows_autostart import AutostartStatus


def test_read_memory_counts_does_not_create_missing_database(tmp_path: Path) -> None:
    path = tmp_path / "missing.sqlite3"
    counts = read_memory_counts(path)
    assert counts.notes == 0
    assert not path.exists()


def test_read_memory_counts_existing_database(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite3"
    store = MemoryStore(path)
    store.add_item("one")
    store.upsert_preference("tone", "warm")
    store.add_conversation_summary("summary", mode="default", provider="openai")
    store.record_tool_approval(
        tool_name="test",
        permission_class="execute",
        action_summary="run tests",
        approved=True,
    )
    store.close()

    counts = read_memory_counts(path)
    assert counts.notes == 1
    assert counts.preferences == 1
    assert counts.summaries == 1
    assert counts.approvals == 1


def test_snapshot_reports_flags_without_secret_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = AppConfig()
    cfg.memory.sqlite_path = str(tmp_path / "memory.sqlite3")
    cfg.tools.enabled = True
    cfg.tools.files.enabled = True
    monkeypatch.setattr(
        "atticus.services.desktop_status.get_credential",
        lambda name: "secret" if name == "OPENAI_API_KEY" else None,
    )
    snapshot = build_snapshot(
        cfg,
        config_path=tmp_path / "config.yaml",
        autostart=AutostartStatus(False, False, None, "not Windows"),
        cwd=tmp_path,
    )
    assert snapshot.provider_keys == {
        "OpenAI": True,
        "Anthropic": False,
        "Gemini": False,
    }
    assert snapshot.tools_enabled
    assert snapshot.tool_flags["Files"]
