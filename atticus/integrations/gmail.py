"""Gmail OAuth (read + optional compose) with local token cache.

Requires optional extra: ``pip install -e ".[gmail]"``.
Never logs tokens or message bodies at debug level from this module.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Sequence

from atticus.core.errors import AtticusError, ConfigurationError


class GmailError(AtticusError):
    """Gmail integration failure (auth, API, or missing deps)."""


@dataclass(frozen=True)
class GmailHeader:
    id: str
    thread_id: str
    subject: str
    from_addr: str
    date: str
    snippet: str


def gmail_deps_installed() -> bool:
    try:
        import google.auth  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
    except ImportError:
        return False
    return True


def _require_deps() -> None:
    if not gmail_deps_installed():
        raise GmailError('Gmail dependencies missing. Install with: pip install -e ".[gmail]"')


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
) -> Any:
    """Load cached credentials or run local OAuth browser flow."""
    _require_deps()
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not client_secrets.is_file():
        raise ConfigurationError(
            f"Gmail client secrets not found at {client_secrets}. "
            "Download an OAuth Desktop client JSON from Google Cloud Console "
            "and set tools.email.gmail_client_secrets_path."
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
        # Local redirect; opens browser on the machine Atticus is running on.
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service(creds: Any) -> Any:
    _require_deps()
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _header_map(payload_headers: list[dict[str, str]] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in payload_headers or []:
        name = str(h.get("name", "")).lower()
        if name:
            out[name] = str(h.get("value", ""))
    return out


def list_inbox(service: Any, *, limit: int = 10) -> list[GmailHeader]:
    resp = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=max(1, min(limit, 50)))
        .execute()
    )
    items = resp.get("messages") or []
    results: list[GmailHeader] = []
    for item in items:
        mid = str(item["id"])
        meta = (
            service.users()
            .messages()
            .get(userId="me", id=mid, format="metadata", metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        headers = _header_map(meta.get("payload", {}).get("headers"))
        results.append(
            GmailHeader(
                id=mid,
                thread_id=str(meta.get("threadId") or item.get("threadId") or ""),
                subject=headers.get("subject") or "(no subject)",
                from_addr=headers.get("from") or "",
                date=headers.get("date") or "",
                snippet=str(meta.get("snippet") or ""),
            )
        )
    return results


def _collect_text_parts(payload: dict[str, Any], *, prefer_plain: bool = True) -> str:
    mime = str(payload.get("mimeType") or "")
    body = payload.get("body") or {}
    data = body.get("data")
    if data and mime.startswith("text/"):
        raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
        if prefer_plain and mime == "text/plain":
            return raw
        if not prefer_plain and mime == "text/html":
            return raw
        if mime.startswith("text/"):
            return raw
    chunks: list[str] = []
    for part in payload.get("parts") or []:
        text = _collect_text_parts(part, prefer_plain=prefer_plain)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def read_message(service: Any, message_id: str, *, max_chars: int = 8000) -> tuple[GmailHeader, str]:
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = _header_map((msg.get("payload") or {}).get("headers"))
    header = GmailHeader(
        id=str(msg.get("id") or message_id),
        thread_id=str(msg.get("threadId") or ""),
        subject=headers.get("subject") or "(no subject)",
        from_addr=headers.get("from") or "",
        date=headers.get("date") or "",
        snippet=str(msg.get("snippet") or ""),
    )
    body = _collect_text_parts(msg.get("payload") or {}, prefer_plain=True)
    if not body:
        body = header.snippet
    if len(body) > max_chars:
        body = body[: max_chars - 1] + "…"
    return header, body


def create_draft(
    service: Any,
    *,
    to: str,
    subject: str,
    body: str,
) -> str:
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    created = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )
    return str(created.get("id") or "")


def send_draft(service: Any, draft_id: str) -> str:
    sent = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    return str(sent.get("id") or draft_id)


def status_text(*, client_secrets: Path | None, token_path: Path, deps_ok: bool) -> str:
    lines = [
        f"gmail deps installed: {'yes' if deps_ok else 'no (pip install -e \".[gmail]\")'}",
        f"client secrets: {client_secrets if client_secrets else '(not configured)'}",
        f"client secrets present: {'yes' if client_secrets and client_secrets.is_file() else 'no'}",
        f"token cache: {token_path}",
        f"token present: {'yes' if token_path.is_file() else 'no'}",
        "Scopes: readonly for inbox/read; compose required for draft/send.",
        "Send always requires explicit Boss confirmation.",
    ]
    return "\n".join(lines)
