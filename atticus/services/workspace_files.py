from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from atticus.core.errors import WorkspaceError


def read_text(path: Path, *, max_bytes: int) -> str:
    data = path.read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
        suffix = "\n\n…(truncated for safety)"
    else:
        suffix = ""
    try:
        return data.decode("utf-8", errors="replace") + suffix
    except Exception as exc:
        raise WorkspaceError(f"Could not decode file as text: {exc}") from exc


def read_bytes_for_pdf(path: Path, *, max_bytes: int) -> bytes:
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise WorkspaceError("PDF exceeds configured max_read_bytes.")
    return data


def extract_pdf_text(path: Path, *, max_bytes: int) -> str:
    data = read_bytes_for_pdf(path, max_bytes=max_bytes)
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:
        raise WorkspaceError("Install PDF support: pip install pypdf") from exc
    import io

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages[:40]:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t.strip())
    return "\n\n".join(parts).strip() or "(no extractable text)"


def search_names(roots: list[Path], glob_pat: str, *, limit: int) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if len(out) >= limit:
                return out
            try:
                if p.is_file() and fnmatch.fnmatch(p.name.lower(), glob_pat.lower()):
                    out.append(p)
            except OSError:
                continue
    return out


def search_content(
    roots: list[Path],
    pattern: str,
    *,
    limit_files: int,
    max_bytes_per_file: int,
    glob_filter: str | None = None,
) -> list[tuple[Path, str]]:
    """Return (path, first_matching_line_snippet) for simple regex content search."""
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        raise WorkspaceError(f"Invalid regex: {exc}") from exc
    hits: list[tuple[Path, str]] = []
    seen = 0
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if seen >= limit_files:
                return hits
            if not p.is_file():
                continue
            if glob_filter and not fnmatch.fnmatch(p.name.lower(), glob_filter.lower()):
                continue
            try:
                data = p.read_bytes()[:max_bytes_per_file]
            except OSError:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            for line in text.splitlines():
                if rx.search(line):
                    snippet = line.strip()
                    if len(snippet) > 200:
                        snippet = snippet[:197] + "…"
                    hits.append((p, snippet))
                    seen += 1
                    break
    return hits


def write_text(path: Path, content: str, *, append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as fh:
        fh.write(content)
        if append and not content.endswith("\n"):
            fh.write("\n")
