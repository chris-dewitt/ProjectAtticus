"""Unified citation / provenance records for Track B M2 read tools.

Evolves the existing ``data/citations`` JSON files used by ``/browse``. Legacy
``PageCitation`` payloads are normalized on read.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from atticus.core.errors import AtticusError

SCHEMA_VERSION = "atticus.citation.v1"
PARSER_VERSION = "atticus-read-v1"

CitationKind = Literal["web_page", "local_file", "code_search_result", "pdf_extract"]


class CitationNotFound(AtticusError):
    code = "citation_not_found"
    status_code = 404


@dataclass
class EvidenceSpan:
    quote: str
    excerpt: str
    line_start: int | None = None
    line_end: int | None = None
    byte_start: int | None = None
    byte_end: int | None = None
    selector: str | None = None


@dataclass
class CitationRecord:
    schema_version: str
    id: str
    kind: CitationKind
    source_uri: str
    title: str
    retrieved_at: str
    tool_name: str
    excerpt: str
    content_sha256: str | None = None
    byte_count: int | None = None
    truncated: bool = False
    status_code: int | None = None
    content_type: str | None = None
    host: str | None = None
    local_path: str | None = None
    parser_version: str = PARSER_VERSION
    conversation_id: str | None = None
    run_id: str | None = None
    correlation_id: str | None = None
    approval_id: int | None = None
    evidence: list[EvidenceSpan] = field(default_factory=list)
    untrusted_external_content: bool = False
    sensitivity: Literal["public", "local_sensitive"] = "public"
    saved_path: str | None = None
    request: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def new_citation_id() -> str:
    return f"cit_{uuid.uuid4().hex}"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def citation_dir_from_config(citation_dir: str | Path, *, cwd: Path | None = None) -> Path:
    path = Path(citation_dir)
    if path.is_absolute():
        return path
    base = cwd or Path.cwd()
    return (base / path).resolve()


def save_record(record: CitationRecord, citation_dir: Path) -> CitationRecord:
    citation_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_host = (record.host or record.kind or "cite").replace(":", "_").replace("/", "_")
    path = citation_dir / f"{stamp}_{safe_host}_{record.id[4:12]}.json"
    record.saved_path = str(path)
    path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
    return record


def load_record(path: Path) -> CitationRecord:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return normalize_payload(raw, saved_path=str(path))


def normalize_payload(raw: dict[str, Any], *, saved_path: str | None = None) -> CitationRecord:
    """Accept v1 records or legacy browse PageCitation JSON."""
    if raw.get("schema_version") == SCHEMA_VERSION and raw.get("id"):
        evidence = [
            EvidenceSpan(**item) if isinstance(item, dict) else EvidenceSpan(quote="", excerpt=str(item))
            for item in raw.get("evidence") or []
        ]
        return CitationRecord(
            schema_version=SCHEMA_VERSION,
            id=str(raw["id"]),
            kind=raw.get("kind") or "web_page",  # type: ignore[arg-type]
            source_uri=str(raw.get("source_uri") or raw.get("url") or ""),
            title=str(raw.get("title") or "(untitled)"),
            retrieved_at=str(raw.get("retrieved_at") or _utc_now()),
            tool_name=str(raw.get("tool_name") or "unknown"),
            excerpt=str(raw.get("excerpt") or ""),
            content_sha256=raw.get("content_sha256"),
            byte_count=raw.get("byte_count"),
            truncated=bool(raw.get("truncated", False)),
            status_code=raw.get("status_code"),
            content_type=raw.get("content_type"),
            host=raw.get("host"),
            local_path=raw.get("local_path"),
            parser_version=str(raw.get("parser_version") or PARSER_VERSION),
            conversation_id=raw.get("conversation_id"),
            run_id=raw.get("run_id"),
            correlation_id=raw.get("correlation_id"),
            approval_id=raw.get("approval_id"),
            evidence=evidence,
            untrusted_external_content=bool(raw.get("untrusted_external_content", False)),
            sensitivity=raw.get("sensitivity") or "public",  # type: ignore[arg-type]
            saved_path=saved_path or raw.get("saved_path"),
            request=dict(raw.get("request") or {}),
        )

    # Legacy browse citation shape.
    url = str(raw.get("url") or "")
    excerpt = str(raw.get("excerpt") or "")
    host = urlparse(url).hostname
    return CitationRecord(
        schema_version=SCHEMA_VERSION,
        id=new_citation_id(),
        kind="web_page",
        source_uri=url,
        title=str(raw.get("title") or "(untitled)"),
        retrieved_at=str(raw.get("retrieved_at") or _utc_now()),
        tool_name="browse_fetch",
        excerpt=excerpt,
        content_sha256=sha256_text(excerpt) if excerpt else None,
        byte_count=len(excerpt.encode("utf-8")),
        truncated=excerpt.endswith("…"),
        status_code=raw.get("status_code"),
        content_type=raw.get("content_type"),
        host=host,
        local_path=None,
        evidence=[EvidenceSpan(quote=excerpt[:240], excerpt=excerpt)],
        untrusted_external_content=True,
        sensitivity="public",
        saved_path=saved_path or raw.get("saved_path"),
        request={"url": url},
    )


def list_records(citation_dir: Path, *, limit: int = 20) -> list[CitationRecord]:
    if not citation_dir.is_dir():
        return []
    files = sorted(citation_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[CitationRecord] = []
    for path in files[: max(1, limit)]:
        try:
            out.append(load_record(path))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return out


def get_record(citation_dir: Path, citation_id: str) -> CitationRecord:
    for record in list_records(citation_dir, limit=500):
        if record.id == citation_id:
            return record
    raise CitationNotFound(
        f"Citation not found: {citation_id}",
        safe_details={"citation_id": citation_id},
    )


def from_web_page(
    *,
    url: str,
    title: str,
    excerpt: str,
    status_code: int,
    content_type: str,
    truncated: bool,
    raw_text: str | None = None,
) -> CitationRecord:
    body = raw_text if raw_text is not None else excerpt
    return CitationRecord(
        schema_version=SCHEMA_VERSION,
        id=new_citation_id(),
        kind="web_page",
        source_uri=url,
        title=title,
        retrieved_at=_utc_now(),
        tool_name="browse_fetch",
        excerpt=excerpt,
        content_sha256=sha256_text(body),
        byte_count=len(body.encode("utf-8", errors="replace")),
        truncated=truncated,
        status_code=status_code,
        content_type=content_type,
        host=urlparse(url).hostname,
        evidence=[EvidenceSpan(quote=excerpt[:240], excerpt=excerpt)],
        untrusted_external_content=True,
        sensitivity="public",
        request={"url": url},
    )


def from_local_file(
    *,
    path: Path,
    text: str,
    max_bytes: int,
    tool_name: str = "file_read",
    kind: CitationKind = "local_file",
) -> CitationRecord:
    truncated = "…(truncated for safety)" in text or len(text.encode("utf-8", errors="replace")) >= max_bytes
    excerpt = text[:2000] + ("…" if len(text) > 2000 else "")
    uri = path.resolve().as_uri()
    return CitationRecord(
        schema_version=SCHEMA_VERSION,
        id=new_citation_id(),
        kind=kind,
        source_uri=uri,
        title=path.name,
        retrieved_at=_utc_now(),
        tool_name=tool_name,
        excerpt=excerpt,
        content_sha256=sha256_text(text),
        byte_count=len(text.encode("utf-8", errors="replace")),
        truncated=truncated,
        content_type="text/plain",
        local_path=str(path.resolve()),
        evidence=[
            EvidenceSpan(
                quote=excerpt[:240],
                excerpt=excerpt,
                byte_start=0,
                byte_end=min(len(text), 2000),
            )
        ],
        untrusted_external_content=False,
        sensitivity="local_sensitive",
        request={"path": str(path)},
    )


def from_code_search(
    *,
    path: Path,
    line: str,
    pattern: str,
    line_no: int | None = None,
) -> CitationRecord:
    excerpt = line.strip()
    return CitationRecord(
        schema_version=SCHEMA_VERSION,
        id=new_citation_id(),
        kind="code_search_result",
        source_uri=path.resolve().as_uri(),
        title=f"{path.name}:{line_no or '?'}",
        retrieved_at=_utc_now(),
        tool_name="code_search",
        excerpt=excerpt,
        content_sha256=sha256_text(excerpt),
        byte_count=len(excerpt.encode("utf-8", errors="replace")),
        truncated=False,
        content_type="text/x-source",
        local_path=str(path.resolve()),
        evidence=[
            EvidenceSpan(
                quote=excerpt[:240],
                excerpt=excerpt,
                line_start=line_no,
                line_end=line_no,
            )
        ],
        untrusted_external_content=False,
        sensitivity="local_sensitive",
        request={"pattern": pattern, "path": str(path)},
    )
