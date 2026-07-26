"""Shared Google OAuth desktop-flow helpers for Gmail/Calendar."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from atticus.core.errors import AtticusError, ConfigurationError


class GoogleOAuthError(AtticusError):
    """Missing deps or OAuth configuration problems."""


def google_api_deps_installed() -> bool:
    try:
        import google.auth  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        return False
    return True


def require_google_api_deps(*, feature: str) -> None:
    if not google_api_deps_installed():
        raise GoogleOAuthError(
            f'{feature} dependencies missing. Install with: pip install -e ".[gmail]"'
        )


def resolve_path(raw: str | None, *, cwd: Path | None = None) -> Path | None:
    if not raw or not str(raw).strip():
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = ((cwd or Path.cwd()) / p).resolve()
    else:
        p = p.resolve()
    return p


def load_credentials(
    *,
    client_secrets: Path,
    token_path: Path,
    scopes: Sequence[str],
    feature: str = "Google API",
) -> Any:
    """Load cached credentials or run local OAuth browser flow."""
    require_google_api_deps(feature=feature)
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not client_secrets.is_file():
        raise ConfigurationError(
            f"{feature} client secrets not found at {client_secrets}. "
            "Download an OAuth Desktop client JSON from Google Cloud Console."
        )

    creds: Credentials | None = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), list(scopes))

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), list(scopes))
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(api: str, version: str, creds: Any) -> Any:
    require_google_api_deps(feature=api)
    from googleapiclient.discovery import build

    return build(api, version, credentials=creds, cache_discovery=False)
