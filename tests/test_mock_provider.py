from __future__ import annotations

from atticus.providers.mock_provider import MockProvider


def test_mock_provider_echo() -> None:
    p = MockProvider()
    out = p.generate([{"role": "user", "content": "ping"}])
    assert "ping" in out
