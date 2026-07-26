"""Fetch public https pages with host allowlisting and local citation capture."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import httpx

from atticus.core.errors import WorkspaceError
from atticus.services import citations as cite_svc
from atticus.services.citations import CitationRecord


@dataclass(frozen=True)
class PageCitation:
    """Legacy browse citation shape (still returned for CLI compatibility)."""

    url: str
    title: str
    retrieved_at: str
    excerpt: str
    status_code: int
    content_type: str
    saved_path: str | None = None
    citation_id: str | None = None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript"}:
            self._skip += 1
            return
        if t == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
            return
        if t == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        else:
            self.text_parts.append(text)


def assert_http_url(url: str) -> str:
    raw = url.strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise WorkspaceError("Only http(s) URLs are allowed.")
    if not parsed.netloc:
        raise WorkspaceError("URL host is required.")
    # Block obvious local/private targets by hostname pattern (defense in depth).
    host = parsed.hostname or ""
    lowered = host.lower()
    if lowered in {"localhost", "127.0.0.1", "::1"} or lowered.endswith(".local"):
        raise WorkspaceError("Local/loopback URLs are not allowed for /browse.")
    return raw


def host_allowed(url: str, allowed_hosts: list[str]) -> bool:
    """If allowlist empty, any non-blocked https/http host is allowed (still needs approval)."""
    if not allowed_hosts:
        return True
    host = (urlparse(url).hostname or "").lower()
    for entry in allowed_hosts:
        e = entry.strip().lower()
        if not e:
            continue
        if host == e or host.endswith("." + e):
            return True
    return False


def _extract(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    title = " ".join(parser.title_parts).strip() or "(no title)"
    text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return title, text


def fetch_page(
    url: str,
    *,
    allowed_hosts: list[str],
    max_bytes: int,
    user_agent: str,
    timeout: float = 30.0,
) -> PageCitation:
    url = assert_http_url(url)
    if urlparse(url).scheme.lower() != "https" and allowed_hosts:
        # When an allowlist is configured, require https.
        raise WorkspaceError("Allowlisted browsing requires https URLs.")
    if not host_allowed(url, allowed_hosts):
        raise WorkspaceError(
            f"Host not on tools.browser.allowed_hosts allowlist: {urlparse(url).hostname}"
        )
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"}
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            with client.stream("GET", url) as resp:
                ctype = resp.headers.get("content-type", "")
                chunks: list[bytes] = []
                total = 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise WorkspaceError(f"Response exceeded max_bytes ({max_bytes}).")
                    chunks.append(chunk)
                body = b"".join(chunks)
                status = resp.status_code
    except WorkspaceError:
        raise
    except Exception as exc:
        raise WorkspaceError(f"Browse fetch failed: {exc}") from exc

    text_body = body.decode("utf-8", errors="replace")
    title, plain = _extract(text_body) if "html" in ctype.lower() or text_body.lstrip().startswith("<") else (
        "(binary or non-html)",
        text_body,
    )
    excerpt = plain[:2000] + ("…" if len(plain) > 2000 else "")
    return PageCitation(
        url=url,
        title=title,
        retrieved_at=datetime.now(tz=UTC).isoformat(),
        excerpt=excerpt,
        status_code=status,
        content_type=ctype,
    )


def save_citation(citation: PageCitation, citation_dir: Path) -> PageCitation:
    """Persist a structured v1 citation and return a legacy-compatible view."""
    truncated = citation.excerpt.endswith("…")
    record = cite_svc.from_web_page(
        url=citation.url,
        title=citation.title,
        excerpt=citation.excerpt,
        status_code=citation.status_code,
        content_type=citation.content_type,
        truncated=truncated,
    )
    saved = cite_svc.save_record(record, citation_dir)
    return PageCitation(
        url=citation.url,
        title=citation.title,
        retrieved_at=saved.retrieved_at,
        excerpt=citation.excerpt,
        status_code=citation.status_code,
        content_type=citation.content_type,
        saved_path=saved.saved_path,
        citation_id=saved.id,
    )


def save_structured_citation(record: CitationRecord, citation_dir: Path) -> CitationRecord:
    return cite_svc.save_record(record, citation_dir)


def list_citations(citation_dir: Path, *, limit: int = 20) -> list[Path]:
    if not citation_dir.is_dir():
        return []
    files = sorted(citation_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[: max(1, limit)]


def list_citation_records(citation_dir: Path, *, limit: int = 20) -> list[CitationRecord]:
    return cite_svc.list_records(citation_dir, limit=limit)
