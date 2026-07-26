"""Read-only status snapshot for the Textual desk."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from atticus.core.config import AppConfig
from atticus.core.secrets import get_credential
from atticus.services.windows_autostart import AutostartStatus


@dataclass(frozen=True)
class MemoryCounts:
    notes: int = 0
    preferences: int = 0
    summaries: int = 0
    approvals: int = 0


@dataclass(frozen=True)
class DesktopSnapshot:
    config_path: Path
    provider: str
    mode: str
    provider_keys: dict[str, bool]
    memory_path: Path
    memory: MemoryCounts
    memory_enabled: bool
    raw_transcripts: bool
    spoken_responses: bool
    tools_enabled: bool
    tool_flags: dict[str, bool]
    autostart: AutostartStatus


def resolve_memory_path(cfg: AppConfig, *, cwd: Path | None = None) -> Path:
    path = Path(cfg.memory.sqlite_path).expanduser()
    if not path.is_absolute():
        path = ((cwd or Path.cwd()) / path).resolve()
    return path


def read_memory_counts(path: Path) -> MemoryCounts:
    """Query an existing SQLite database read-only; never create or migrate it."""
    if not path.is_file():
        return MemoryCounts()
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return MemoryCounts()
    try:
        def count(table: str, where: str = "") -> int:
            try:
                row = conn.execute(f"SELECT COUNT(1) FROM {table} {where}").fetchone()
            except sqlite3.Error:
                return 0
            return int(row[0]) if row else 0

        return MemoryCounts(
            notes=count("memory_items", "WHERE deleted_at IS NULL"),
            preferences=count("preferences"),
            summaries=count("conversation_summaries"),
            approvals=count("tool_approvals"),
        )
    finally:
        conn.close()


def build_snapshot(
    cfg: AppConfig,
    *,
    config_path: Path,
    autostart: AutostartStatus,
    cwd: Path | None = None,
) -> DesktopSnapshot:
    memory_path = resolve_memory_path(cfg, cwd=cwd)
    return DesktopSnapshot(
        config_path=config_path,
        provider=cfg.providers.routing.default_provider,
        mode=cfg.assistant.default_mode,
        provider_keys={
            "OpenAI": bool(get_credential(cfg.providers.openai.api_key_env)),
            "Anthropic": bool(get_credential(cfg.providers.anthropic.api_key_env)),
            "Gemini": bool(get_credential(cfg.providers.gemini.api_key_env)),
        },
        memory_path=memory_path,
        memory=read_memory_counts(memory_path),
        memory_enabled=cfg.privacy.memory_enabled,
        raw_transcripts=cfg.privacy.store_raw_conversations,
        spoken_responses=cfg.voice.spoken_responses,
        tools_enabled=cfg.tools.enabled,
        tool_flags={
            "Files": cfg.tools.files.enabled,
            "Git/Patch/Test": cfg.tools.shell.enabled,
            "GitHub": cfg.tools.github.enabled,
            "Gmail": cfg.tools.email.enabled,
            "Calendar": cfg.tools.calendar.enabled,
            "Browser": cfg.tools.browser.enabled,
        },
        autostart=autostart,
    )
