from __future__ import annotations

from types import SimpleNamespace

from atticus.integrations import calendar as cal


def test_list_events_maps_items() -> None:
    class _Events:
        def list(self, **kwargs):  # noqa: ANN003
            def _exec():
                return {
                    "items": [
                        {
                            "id": "e1",
                            "summary": "Standup",
                            "start": {"dateTime": "2026-08-01T09:00:00Z"},
                            "end": {"dateTime": "2026-08-01T09:30:00Z"},
                            "location": "Zoom",
                            "htmlLink": "https://calendar.google.com/event?eid=e1",
                        }
                    ]
                }

            return SimpleNamespace(execute=_exec)

    service = SimpleNamespace(events=lambda: _Events())
    rows = cal.list_events(service, days=3, max_events=5)
    assert len(rows) == 1
    assert rows[0].summary == "Standup"
    assert rows[0].location == "Zoom"


def test_status_mentions_double_confirm(tmp_path) -> None:  # noqa: ANN001
    text = cal.status_text(client_secrets=None, token_path=tmp_path / "t.json", deps_ok=False)
    assert "CREATE/DELETE" in text
