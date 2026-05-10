"""Resolve local secrets: environment first, then optional OS keyring (Step 1 for full-product integrations)."""

from __future__ import annotations

import os

KEYRING_SERVICE_NAME = "ProjectAtticus"


def get_credential(env_name: str, *, keyring_username: str | None = None) -> str | None:
    """
    Return a secret value for integration use.

    Resolution order:
    1. Non-empty ``os.environ[env_name]`` (including values loaded from ``.env``).
    2. If ``keyring`` is installed, ``keyring.get_password(KEYRING_SERVICE_NAME, username)``.

    Store in the keyring (example, Windows): ``keyring set ProjectAtticus GITHUB_TOKEN``
    with the package installed: ``pip install -e ".[secrets]"``.
    """
    raw = os.environ.get(env_name, "")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    user = keyring_username or env_name
    try:
        import keyring  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        pw = keyring.get_password(KEYRING_SERVICE_NAME, user)
    except Exception:
        return None
    if isinstance(pw, str) and pw.strip():
        return pw.strip()
    return None
