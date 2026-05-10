from __future__ import annotations

from typing import Any

from atticus.core.errors import WorkspaceError
from atticus.core.secrets import get_credential


def fetch_recent_issue_titles(owner: str, repo: str, *, limit: int = 8, token: str | None = None) -> list[str]:
    """Fetch recent issue titles from the public GitHub REST API (optional token for rate limits)."""
    try:
        import httpx
    except ImportError as exc:
        raise WorkspaceError("httpx is required for GitHub queries (bundled with the OpenAI SDK).") from exc

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = httpx.get(url, params={"per_page": limit, "state": "all"}, headers=headers, timeout=30.0)
    except Exception as exc:
        raise WorkspaceError(f"GitHub request failed: {exc}") from exc
    if r.status_code != 200:
        raise WorkspaceError(f"GitHub API HTTP {r.status_code}: {r.text[:500]}")
    data: list[Any] = r.json()
    lines: list[str] = []
    for item in data:
        if "pull_request" in item:
            continue
        title = item.get("title") or ""
        num = item.get("number")
        lines.append(f"#{num} {title}".strip())
    return lines


def github_token_from_config(token_env: str) -> str | None:
    """Token from env or keyring (see ``atticus.core.secrets``)."""
    return get_credential(token_env)
