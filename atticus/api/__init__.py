"""Track B local HTTP API (optional ``.[api]`` extra).

M0 exposes health/readiness only. Conversation/run/approval APIs remain later
milestones. Track A CLI does not require this package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

__all__ = ["create_app"]


def create_app(*args: Any, **kwargs: Any) -> "FastAPI":
    """Lazy import so installing Atticus without ``.[api]`` still works."""
    from atticus.api.app import create_app as _create_app

    return _create_app(*args, **kwargs)
