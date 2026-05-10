from __future__ import annotations

import sys
import types

import pytest

from atticus.core.secrets import KEYRING_SERVICE_NAME, get_credential


def test_get_credential_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "from-env")
    assert get_credential("MY_TOKEN") == "from-env"


def test_get_credential_keyring_when_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RING_TOKEN", "")
    monkeypatch.delenv("RING_TOKEN", raising=False)

    mod = types.ModuleType("keyring")

    def get_password(service: str, user: str) -> str | None:
        if service == KEYRING_SERVICE_NAME and user == "RING_TOKEN":
            return "from-ring"
        return None

    mod.get_password = get_password  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", mod)
    try:
        assert get_credential("RING_TOKEN") == "from-ring"
    finally:
        sys.modules.pop("keyring", None)


def test_get_credential_none_when_keyring_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NONE_TOKEN", raising=False)
    mod = types.ModuleType("keyring")
    mod.get_password = lambda s, u: None  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", mod)
    try:
        assert get_credential("NONE_TOKEN") is None
    finally:
        sys.modules.pop("keyring", None)
