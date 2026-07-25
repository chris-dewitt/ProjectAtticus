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

from atticus.core.errors import AtticusError
from atticus.integrations.google_oauth import (
    build_service as google_build_service,
    google_api_deps_installed,
    load_credentials as google_load_credentials,
    require_google_api_deps,
    resolve_path,
)


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
    return google_api_deps_installed()


def _require_deps() -> None:
    try:
        require_google_api_deps(feature="Gmail")
    except AtticusError as exc:
        raise GmailError(str(exc)) from exc


def load_credentials(
    *,
    client_secrets: Path,
    token_path: Path,
    scopes: Sequence[str],
) -> Any:
    """Load cached credentials or run local OAuth browser flow."""
    _require_deps()
    return google_load_credentials(
        client_secrets=client_secrets,
        token_path=token_path,
        scopes=scopes,
        feature="Gmail",
    )


def build_service(creds: Any) -> Any:
    _require_deps()
    return google_build_service("gmail", "v1", creds)


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
