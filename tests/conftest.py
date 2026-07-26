from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clear_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not depend on a real OpenAI key unless explicitly set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ATTICUS_APPROVAL_TOKEN", raising=False)
