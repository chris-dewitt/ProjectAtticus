from __future__ import annotations

from pathlib import Path

from atticus.providers.mock_provider import MockProvider
from atticus.runs.orchestrator import BoundedRunOrchestrator, RunConflict
from atticus.runs.store import RunStore
import pytest


def _orch(tmp_path: Path, reply: str = "Of course, Boss.") -> tuple[RunStore, BoundedRunOrchestrator]:
    store = RunStore(tmp_path / "runs.sqlite3")
    orch = BoundedRunOrchestrator(
        store,
        provider_factory=lambda _name: MockProvider(reply=reply),
        repo_root=None,
        include_system_prompt=False,
    )
    return store, orch


def test_execute_succeeds(tmp_path: Path) -> None:
    store, orch = _orch(tmp_path)
    conv = store.create_conversation()
    store.add_message(conv.id, role="user", content="Hello")
    run = store.create_run(
        conversation_id=conv.id,
        provider="mock",
        mode="default",
        input_messages=[{"role": "user", "content": "Hello"}],
    )
    result = orch.execute(run.id)
    assert result.status.value == "succeeded"
    assert result.output_text == "Of course, Boss."
    assert any(c.name == "finalize" for c in result.checkpoints)
    assert store.list_messages(conv.id)[-1].role == "assistant"
    store.close()


def test_cancel_queued_run(tmp_path: Path) -> None:
    store, orch = _orch(tmp_path)
    conv = store.create_conversation()
    run = store.create_run(
        conversation_id=conv.id,
        provider="mock",
        mode="default",
        input_messages=[{"role": "user", "content": "Hello"}],
    )
    cancelled = orch.cancel(run.id)
    assert cancelled.status.value == "cancelled"
    with pytest.raises(RunConflict):
        orch.cancel(run.id)
    store.close()


def test_provider_failure_marks_failed(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs.sqlite3")

    class Boom:
        name = "boom"

        def generate(self, messages, *, tools=None, mode=None):  # type: ignore[no-untyped-def]
            raise RuntimeError("network down")

    orch = BoundedRunOrchestrator(
        store,
        provider_factory=lambda _name: Boom(),  # type: ignore[arg-type, return-value]
        include_system_prompt=False,
    )
    conv = store.create_conversation()
    run = store.create_run(
        conversation_id=conv.id,
        provider="boom",
        mode="default",
        input_messages=[{"role": "user", "content": "Hello"}],
    )
    result = orch.execute(run.id)
    assert result.status.value == "failed"
    assert result.error_code == "provider_error"
    store.close()
