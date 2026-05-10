from __future__ import annotations

from pathlib import Path

from atticus.memory.store import MemoryStore


def test_remember_list_forget(tmp_path: Path) -> None:
    db = tmp_path / "m.sqlite3"
    store = MemoryStore(db)
    try:
        mid = store.add_item("buy milk", kind="note")
        items = store.list_items()
        assert any(it.id == mid and "milk" in it.content for it in items)
        assert store.forget_id(mid) is True
        assert store.forget_id(mid) is False
        assert not store.list_items()
    finally:
        store.close()


def test_forget_all(tmp_path: Path) -> None:
    db = tmp_path / "m2.sqlite3"
    store = MemoryStore(db)
    try:
        store.add_item("a")
        store.add_item("b")
        assert store.forget_all() == 2
        assert not store.list_items()
    finally:
        store.close()
