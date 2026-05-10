from __future__ import annotations

import pytest

from atticus.core.errors import WorkspaceError
from atticus.integrations import github_public as gh


def test_require_github_token_raises() -> None:
    with pytest.raises(WorkspaceError, match="GITHUB_TOKEN"):
        gh.require_github_token(None, token_env="GITHUB_TOKEN", for_action="/gh me")


def test_fetch_profile_uses_get_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, *, token: str | None, params: dict | None) -> dict:
        assert "/user" in url
        assert token == "tok"
        return {"login": "octocat", "name": "The Octocat"}

    monkeypatch.setattr(gh, "_get_json", fake_get)
    login, name = gh.fetch_authenticated_profile("tok")
    assert login == "octocat"
    assert name == "The Octocat"


def test_fetch_repos_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gh,
        "_get_json",
        lambda url, token=None, params=None: [
            {"full_name": "a/pub", "private": False},
            {"full_name": "b/priv", "private": True},
        ],
    )
    lines = gh.fetch_authenticated_repos("tok", limit=10)
    assert "a/pub (public)" in lines
    assert "b/priv (private)" in lines


def test_fetch_pulls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gh,
        "_get_json",
        lambda url, token=None, params=None: [
            {"number": 2, "title": "Fix thing", "state": "open", "draft": False},
            {"number": 1, "title": "WIP", "state": "open", "draft": True},
        ],
    )
    lines = gh.fetch_pull_requests("o", "r", token="t", limit=5, state="open")
    assert any("Fix thing" in x for x in lines)
    assert any("draft" in x.lower() for x in lines)
