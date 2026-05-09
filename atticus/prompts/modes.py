from __future__ import annotations

from pathlib import Path

from atticus.core.errors import ConfigurationError

_MODE_FILES: dict[str, str] = {
    "default": "default.md",
    "chief_of_staff": "chief_of_staff.md",
    "coding_partner": "coding_partner.md",
    "research_analyst": "research_analyst.md",
    "study_tutor": "study_tutor.md",
    "finance_analyst": "finance_analyst.md",
    "life_admin": "life_admin.md",
}


def valid_modes() -> frozenset[str]:
    return frozenset(_MODE_FILES)


def load_mode_addon(repo_root: Path, mode: str) -> str:
    """Return extra instructions for a named mode (may be short)."""
    filename = _MODE_FILES.get(mode)
    if not filename:
        raise ConfigurationError(f"Unknown mode: {mode}. Valid: {', '.join(sorted(_MODE_FILES))}")
    path = repo_root / "prompts" / "modes" / filename
    if not path.is_file():
        raise ConfigurationError(f"Missing mode prompt file: {path}")
    return path.read_text(encoding="utf-8").strip()
