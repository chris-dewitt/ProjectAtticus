from __future__ import annotations

from atticus.ui import web_shell


def test_port_open_localhost_negative() -> None:
    assert web_shell._port_open("127.0.0.1", 1) is False


def test_open_terminal_ui_reports_missing_api(monkeypatch) -> None:
    monkeypatch.setattr(web_shell, "_port_open", lambda *_a, **_k: True)
    monkeypatch.setattr(web_shell, "_ui_ready", lambda *_a, **_k: False)
    monkeypatch.setattr(web_shell, "_wait_for_ui", lambda *_a, **_k: False)
    code = web_shell.open_terminal_ui(start_server=True, prefer_webview=False)
    assert code == 1
