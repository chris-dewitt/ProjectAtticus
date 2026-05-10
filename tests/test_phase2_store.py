from __future__ import annotations

from pathlib import Path

from atticus.memory.store import MemoryStore


def test_preferences_upsert_and_delete(tmp_path: Path) -> None:
    db = tmp_path / "p.sqlite3"
    store = MemoryStore(db)
    try:
        store.upsert_preference("theme", "dark", source="test")
        store.upsert_preference("theme", "light", source="test")
        assert store.get_preference("theme") == "light"
        assert store.delete_preference("theme") is True
        assert store.get_preference("theme") is None
    finally:
        store.close()


def test_conversation_summary_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "s.sqlite3"
    store = MemoryStore(db)
    try:
        sid = store.add_conversation_summary("Discussed Phase 2 goals.", mode="default", provider="openai")
        rows = store.list_summaries(limit=5)
        assert any(r.id == sid and "Phase 2" in r.summary for r in rows)
        assert store.forget_summary_id(sid) is True
    finally:
        store.close()


def test_search_and_forget_matching(tmp_path: Path) -> None:
    db = tmp_path / "q.sqlite3"
    store = MemoryStore(db)
    try:
        store.add_item("buy oat milk")
        store.add_item("call dentist")
        hits = store.search_items("oat")
        assert len(hits) == 1
        n = store.forget_items_matching("oat")
        assert n == 1
        assert not store.search_items("oat")
    finally:
        store.close()


def test_counts(tmp_path: Path) -> None:
    db = tmp_path / "c.sqlite3"
    store = MemoryStore(db)
    try:
        assert store.count_active_items() == 0
        store.add_item("a")
        store.add_item("b")
        assert store.count_active_items() == 2
        store.upsert_preference("k", "v")
        assert store.count_preferences() == 1
        store.add_conversation_summary("s", mode=None, provider=None)
        assert store.count_summaries() == 1
        store.record_tool_approval(tool_name="t", permission_class="safe_read", action_summary="x", approved=True)
        assert store.count_tool_approvals() == 1
    finally:
        store.close()
