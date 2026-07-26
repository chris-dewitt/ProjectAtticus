"""Structured Atticus errors (Track A CLI + Track B API).

Existing subclasses remain constructible with a single message string so Track A
call sites stay compatible. Structured fields support API error bodies without
leaking secrets.
"""

from __future__ import annotations

from typing import Any


class AtticusError(Exception):
    """Base error for user-facing failures."""

    code: str = "atticus_error"
    status_code: int = 500

    def __init__(
        self,
        message: str = "Atticus error",
        *,
        code: str | None = None,
        status_code: int | None = None,
        safe_details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.safe_details: dict[str, Any] = dict(safe_details or {})

    def to_dict(self, *, correlation_id: str | None = None) -> dict[str, Any]:
        """Return a privacy-safe structured error payload."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": dict(self.safe_details),
        }
        if correlation_id:
            payload["correlation_id"] = correlation_id
        return payload


class ConfigurationError(AtticusError):
    """Invalid or missing configuration."""

    code = "configuration_error"
    status_code = 500


class ProviderError(AtticusError):
    """LLM provider failures (network, auth, unsupported)."""

    code = "provider_error"
    status_code = 502


class PermissionDenied(AtticusError):
    """Action blocked by the permission model."""

    code = "permission_denied"
    status_code = 403


class VoiceInputError(AtticusError):
    """Microphone capture or local speech recognition failed."""

    code = "voice_input_error"
    status_code = 500


class WorkspaceError(AtticusError):
    """File path outside approved workspace or unsafe tool use."""

    code = "workspace_error"
    status_code = 400


class ReadinessError(AtticusError):
    """Local dependency is not ready for API traffic."""

    code = "not_ready"
    status_code = 503


class DependencyUnavailable(AtticusError):
    """Optional dependency or external service is unavailable."""

    code = "dependency_unavailable"
    status_code = 503
