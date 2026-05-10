from __future__ import annotations

from typing import Any

from atticus.core.errors import WorkspaceError
from atticus.core.secrets import get_credential

_GITHUB_API = "https://api.github.com"
_HEADERS_BASE = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _http():
    try:
        import httpx
    except ImportError as exc:
        raise WorkspaceError("httpx is required for GitHub queries.") from exc
    return httpx


def _headers(token: str | None) -> dict[str, str]:
    h = dict(_HEADERS_BASE)
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get_json(url: str, *, token: str | None, params: dict[str, Any] | None = None) -> Any:
    httpx = _http()
    try:
        r = httpx.get(url, params=params, headers=_headers(token), timeout=30.0)
    except Exception as exc:
        raise WorkspaceError(f"GitHub request failed: {exc}") from exc
    if r.status_code != 200:
        raise WorkspaceError(f"GitHub API HTTP {r.status_code}: {r.text[:800]}")
    return r.json()


def github_token_from_config(token_env: str) -> str | None:
    """Token from env or keyring (see ``atticus.core.secrets``)."""
    return get_credential(token_env)


def require_github_token(token: str | None, *, token_env: str, for_action: str) -> str:
    if not (token and token.strip()):
        raise WorkspaceError(
            f"{for_action} requires a GitHub token. Set {token_env} in your environment, or store it with "
            f'keyring set ProjectAtticus {token_env} (install keyring: pip install -e ".[secrets]").'
        )
    return token.strip()


def fetch_recent_issue_titles(owner: str, repo: str, *, limit: int = 8, token: str | None = None) -> list[str]:
    """Fetch recent issue titles from the GitHub REST API (public repo works without token)."""
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/issues"
    data: list[Any] = _get_json(url, token=token, params={"per_page": limit, "state": "all"})
    lines: list[str] = []
    for item in data:
        if "pull_request" in item:
            continue
        title = item.get("title") or ""
        num = item.get("number")
        lines.append(f"#{num} {title}".strip())
    return lines


def fetch_authenticated_profile(token: str) -> tuple[str, str | None]:
    """Return (login, display_name) for GET /user."""
    url = f"{_GITHUB_API}/user"
    data: dict[str, Any] = _get_json(url, token=token, params=None)
    login = str(data.get("login") or "")
    name = data.get("name")
    return login, str(name) if name else None


def fetch_authenticated_repos(token: str, *, limit: int) -> list[str]:
    """List repo full names the token can see (affiliation: owner, collaborator, organization_member)."""
    url = f"{_GITHUB_API}/user/repos"
    params: dict[str, Any] = {
        "per_page": min(limit, 100),
        "affiliation": "owner,collaborator,organization_member",
        "sort": "updated",
    }
    data: list[Any] = _get_json(url, token=token, params=params)
    lines: list[str] = []
    for item in data[:limit]:
        fn = item.get("full_name") or ""
        priv = item.get("private")
        flag = "private" if priv else "public"
        lines.append(f"{fn} ({flag})")
    return lines


def fetch_pull_requests(
    owner: str,
    repo: str,
    *,
    token: str | None,
    limit: int,
    state: str = "open",
) -> list[str]:
    """List pull requests for a repository (token improves rate limits and is required for private repos)."""
    if state not in {"open", "closed", "all"}:
        state = "open"
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/pulls"
    data: list[Any] = _get_json(url, token=token, params={"per_page": min(limit, 100), "state": state})
    lines: list[str] = []
    for item in data[:limit]:
        num = item.get("number")
        title = (item.get("title") or "").strip()
        draft = item.get("draft")
        st = item.get("state") or ""
        d = " draft" if draft else ""
        lines.append(f"#{num} [{st}]{d} {title}".strip())
    return lines
