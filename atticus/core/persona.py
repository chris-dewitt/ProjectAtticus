from __future__ import annotations

from pathlib import Path

from atticus.prompts.modes import load_mode_addon
from atticus.prompts.system import load_canonical_system_text


def build_system_prompt(repo_root: Path, mode: str) -> str:
    """Combine canonical Atticus instructions with the active mode profile."""
    base = load_canonical_system_text(repo_root)
    addon = load_mode_addon(repo_root, mode)
    return f"{base}\n\n---\n\n# Active mode\n\n{addon}"
