class AtticusError(Exception):
    """Base error for user-facing failures."""


class ConfigurationError(AtticusError):
    """Invalid or missing configuration."""


class ProviderError(AtticusError):
    """LLM provider failures (network, auth, unsupported)."""


class PermissionDenied(AtticusError):
    """Action blocked by the permission model."""
