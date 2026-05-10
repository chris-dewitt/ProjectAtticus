from __future__ import annotations

from pathlib import Path

from atticus.core.config import AppConfig
from atticus.core.errors import WorkspaceError


def approved_roots(cfg: AppConfig) -> list[Path]:
    roots = [Path(p).expanduser().resolve() for p in cfg.tools.approved_paths if str(p).strip()]
    return roots


def resolve_under_approved(cfg: AppConfig, user_path: str) -> Path:
    """Resolve a user-supplied path and ensure it stays under an approved root."""
    if not cfg.tools.enabled or not cfg.tools.files.enabled:
        raise WorkspaceError("File tools are disabled in configuration.")
    roots = approved_roots(cfg)
    if not roots:
        raise WorkspaceError("No tools.approved_paths configured; refusing file access.")
    raw = Path(user_path).expanduser()
    candidate = (Path.cwd() / raw).resolve() if not raw.is_absolute() else raw.resolve()
    for root in roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise WorkspaceError(f"Path is outside approved workspace: {candidate}")
