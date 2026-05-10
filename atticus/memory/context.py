from __future__ import annotations

from atticus.core.config import AppConfig
from atticus.memory.store import MemoryStore


def build_memory_context_block(store: MemoryStore, cfg: AppConfig) -> str:
    """Compact, non-sensitive excerpt for system prompt injection."""
    if not cfg.privacy.memory_enabled:
        return ""

    lines: list[str] = []
    prefs = store.list_preferences(limit=8)
    if prefs:
        lines.append("Preferences:")
        for p in prefs:
            lines.append(f"- {p.key}: {p.value}")

    items = store.list_items(limit=5)
    if items:
        lines.append("Recent notes:")
        for it in items:
            snippet = it.content.replace("\n", " ")
            if len(snippet) > 160:
                snippet = snippet[:157] + "..."
            lines.append(f"- ({it.id}) {snippet}")

    summaries = store.list_summaries(limit=3)
    if summaries:
        lines.append("Recent session summaries:")
        for s in summaries:
            txt = s.summary.replace("\n", " ")
            if len(txt) > 200:
                txt = txt[:197] + "..."
            lines.append(f"- ({s.id}) {txt}")

    return "\n".join(lines).strip()
