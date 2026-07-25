"""Google Calendar read/write helpers (optional ``.[gmail]`` Google API stack)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from atticus.core.errors import AtticusError, WorkspaceError
from atticus.integrations.google_oauth import (
    build_service,
    google_api_deps_installed,
    load_credentials,
    resolve_path,
)


class CalendarError(AtticusError):
    """Calendar integration failures."""


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    summary: str
    start: str
    end: str
    location: str
    html_link: str


def calendar_deps_installed() -> bool:
    return google_api_deps_installed()


def status_text(*, client_secrets: Path | None, token_path: Path, deps_ok: bool) -> str:
    return "\n".join(
        [
            f"calendar deps installed: {'yes' if deps_ok else 'no (pip install -e \".[gmail]\")'}",
            f"client secrets: {client_secrets if client_secrets else '(not configured)'}",
            f"client secrets present: {'yes' if client_secrets and client_secrets.is_file() else 'no'}",
            f"token cache: {token_path}",
            f"token present: {'yes' if token_path.is_file() else 'no'}",
            "Writes require double confirmation (y/N + CREATE/DELETE token).",
        ]
    )


def authenticate(*, client_secrets: Path, token_path: Path, scopes: list[str]) -> Any:
    return load_credentials(
        client_secrets=client_secrets,
        token_path=token_path,
        scopes=scopes,
        feature="Google Calendar",
    )


def calendar_service(creds: Any) -> Any:
    return build_service("calendar", "v3", creds)


def _fmt_time(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return str(value.get("dateTime") or value.get("date") or "")


def list_events(
    service: Any,
    *,
    calendar_id: str = "primary",
    days: int = 7,
    max_events: int = 20,
) -> list[CalendarEvent]:
    now = datetime.now(tz=UTC)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=max(1, days))).isoformat()
    resp = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max(1, min(max_events, 50)),
        )
        .execute()
    )
    out: list[CalendarEvent] = []
    for item in resp.get("items") or []:
        out.append(
            CalendarEvent(
                id=str(item.get("id") or ""),
                summary=str(item.get("summary") or "(no title)"),
                start=_fmt_time(item.get("start")),
                end=_fmt_time(item.get("end")),
                location=str(item.get("location") or ""),
                html_link=str(item.get("htmlLink") or ""),
            )
        )
    return out


def create_event(
    service: Any,
    *,
    calendar_id: str,
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
) -> CalendarEvent:
    body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    # All-day support: YYYY-MM-DD
    if "T" not in start_iso and "T" not in end_iso:
        body["start"] = {"date": start_iso}
        body["end"] = {"date": end_iso}
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    return CalendarEvent(
        id=str(created.get("id") or ""),
        summary=str(created.get("summary") or summary),
        start=_fmt_time(created.get("start")),
        end=_fmt_time(created.get("end")),
        location=str(created.get("location") or ""),
        html_link=str(created.get("htmlLink") or ""),
    )


def delete_event(service: Any, *, calendar_id: str, event_id: str) -> None:
    if not event_id.strip():
        raise WorkspaceError("event_id is required")
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


# Re-export path helper for callers
__all__ = [
    "CalendarError",
    "CalendarEvent",
    "authenticate",
    "calendar_deps_installed",
    "calendar_service",
    "create_event",
    "delete_event",
    "list_events",
    "resolve_path",
    "status_text",
]
