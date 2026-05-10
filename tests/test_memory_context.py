from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.config import AppConfig
from atticus.memory.context import build_memory_context_block
from atticus.memory.store import MemoryStore


@pytest.fixture()
def cfg() -> AppConfig:
    return AppConfig.model_validate({"privacy": {"memory_enabled": True}})


def test_build_memory_context_block_includes_notes(tmp_path: Path, cfg: AppConfig) -> None:
    store = MemoryStore(tmp_path / "m.sqlite3")
    try:
        store.add_item("remember the door code is 1234")
        text = build_memory_context_block(store, cfg)
        assert "door code" in text
    finally:
        store.close()


def test_build_memory_context_respects_disabled_memory(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "m2.sqlite3")
    cfg_off = AppConfig.model_validate({"privacy": {"memory_enabled": False}})
    try:
        store.add_item("secret note")
        assert build_memory_context_block(store, cfg_off) == ""
    finally:
        store.close()
