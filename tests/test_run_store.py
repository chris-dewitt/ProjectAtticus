from __future__ import annotations

from pathlib import Path

import pytest

from atticus.runs.store import ConversationNotFound, RunNotFound, RunStore


def test_conversation_message_run_roundtrip(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.sqlite3")
    conv = store.create_conversation(title="demo")
    msg = store.add_message(conv.id, role="user", content="Howdy")
    assert msg.conversation_id == conv.id
    run = store.create_run(
        conversation_id=conv.id,
        provider="mock",
        mode="default",
        input_messages=[{"role": "user", "content": "Howdy"}],
        idempotency_key="key-1",
    )
    again = store.create_run(
        conversation_id=conv.id,
        provider="mock",
        mode="default",
        input_messages=[{"role": "user", "content": "Howdy"}],
        idempotency_key="key-1",
    )
    assert again.id == run.id
    loaded = store.get_run(run.id)
    assert loaded.status.value == "queued"
    assert store.list_messages(conv.id)[0].content == "Howdy"
    store.close()


def test_missing_entities(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.sqlite3")
    with pytest.raises(ConversationNotFound):
        store.get_conversation("missing")
    with pytest.raises(RunNotFound):
        store.get_run("missing")
    store.close()
