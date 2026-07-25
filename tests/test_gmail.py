from __future__ import annotations

import base64
from email.message import EmailMessage
from pathlib import Path
from types import SimpleNamespace

import pytest

from atticus.integrations import gmail as gmail_api


def test_status_text_mentions_send_confirm(tmp_path: Path) -> None:
    text = gmail_api.status_text(
        client_secrets=None,
        token_path=tmp_path / "token.json",
        deps_ok=False,
    )
    assert "Send always requires" in text
    assert "pip install" in text


def test_resolve_path_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    secrets = tmp_path / "secrets.json"
    secrets.write_text("{}", encoding="utf-8")
    resolved = gmail_api.resolve_path("secrets.json")
    assert resolved == secrets.resolve()


def test_list_inbox_parses_headers() -> None:
    class _Messages:
        def list(self, **kwargs):  # noqa: ANN003
            return SimpleNamespace(execute=lambda: {"messages": [{"id": "m1", "threadId": "t1"}]})

        def get(self, **kwargs):  # noqa: ANN003
            assert kwargs["id"] == "m1"

            def _exec():
                return {
                    "id": "m1",
                    "threadId": "t1",
                    "snippet": "Hello snippet",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Subj"},
                            {"name": "From", "value": "a@b.com"},
                            {"name": "Date", "value": "today"},
                        ]
                    },
                }

            return SimpleNamespace(execute=_exec)

    class _Users:
        def messages(self):
            return _Messages()

    service = SimpleNamespace(users=lambda: _Users())
    rows = gmail_api.list_inbox(service, limit=5)
    assert len(rows) == 1
    assert rows[0].subject == "Subj"
    assert rows[0].from_addr == "a@b.com"


def test_create_draft_encodes_raw() -> None:
    captured: dict = {}

    class _Drafts:
        def create(self, **kwargs):  # noqa: ANN003
            captured.update(kwargs)

            def _exec():
                return {"id": "d1"}

            return SimpleNamespace(execute=_exec)

    class _Users:
        def drafts(self):
            return _Drafts()

    service = SimpleNamespace(users=lambda: _Users())
    draft_id = gmail_api.create_draft(
        service, to="boss@example.com", subject="Hi", body="Body text"
    )
    assert draft_id == "d1"
    raw = captured["body"]["message"]["raw"]
    decoded = base64.urlsafe_b64decode(raw.encode("utf-8")).decode("utf-8")
    assert "boss@example.com" in decoded
    assert "Body text" in decoded


def test_read_message_plain_part() -> None:
    plain = base64.urlsafe_b64encode(b"Plain body").decode("utf-8")

    class _Messages:
        def get(self, **kwargs):  # noqa: ANN003
            def _exec():
                return {
                    "id": "m9",
                    "threadId": "t9",
                    "snippet": "snip",
                    "payload": {
                        "mimeType": "text/plain",
                        "headers": [
                            {"name": "Subject", "value": "S"},
                            {"name": "From", "value": "x@y.z"},
                            {"name": "Date", "value": "d"},
                        ],
                        "body": {"data": plain},
                    },
                }

            return SimpleNamespace(execute=_exec)

    class _Users:
        def messages(self):
            return _Messages()

    header, body = gmail_api.read_message(SimpleNamespace(users=lambda: _Users()), "m9")
    assert header.subject == "S"
    assert body == "Plain body"


def test_email_message_roundtrip_helper() -> None:
    # Sanity: stdlib EmailMessage still packs as expected for Gmail raw.
    msg = EmailMessage()
    msg["To"] = "a@b.c"
    msg["Subject"] = "s"
    msg.set_content("body")
    assert "a@b.c" in msg.as_string()
