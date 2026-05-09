from __future__ import annotations

from pathlib import Path

from atticus.core.errors import ConfigurationError


def load_canonical_system_text(repo_root: Path) -> str:
    """Load prompts/atticus_system_prompt.md (markdown body kept verbatim)."""
    path = repo_root / "prompts" / "atticus_system_prompt.md"
    if not path.is_file():
        raise ConfigurationError(f"Missing canonical prompt file: {path}")
    return path.read_text(encoding="utf-8").strip()
