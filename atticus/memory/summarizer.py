"""Privacy-safe conversation summarization (local by default; no raw transcript storage)."""

from __future__ import annotations

import re
from typing import Any, Sequence


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def extract_dialogue_turns(messages: Sequence[dict[str, Any]]) -> list[tuple[str, str]]:
    """Return (role, content) for user/assistant turns only (system omitted)."""
    turns: list[tuple[str, str]] = []
    for msg in messages:
        role = str(msg.get("role", "")).strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = msg.get("content", "")
        text = content if isinstance(content, str) else str(content)
        text = text.strip()
        if text:
            turns.append((role, text))
    return turns


def summarize_conversation(
    messages: Sequence[dict[str, Any]],
    *,
    max_chars: int = 900,
    max_bullets: int = 8,
) -> str:
    """
    Build a local summary from in-memory chat turns.

    This does **not** call a cloud model and does **not** persist raw transcripts.
    Callers decide whether to store the returned summary string in SQLite.
    """
    turns = extract_dialogue_turns(messages)
    if not turns:
        return ""

    user_bits = [t for role, t in turns if role == "user"]
    assistant_bits = [t for role, t in turns if role == "assistant"]

    bullets: list[str] = []
    # Prefer recent user intents (what The Speaker asked for).
    for text in user_bits[-max_bullets:]:
        bullets.append(f"- The Speaker: {_clip(text, 140)}")
    # Include a couple of assistant conclusions if space remains.
    remaining = max(0, max_bullets - len(bullets))
    for text in assistant_bits[-remaining:]:
        bullets.append(f"- Atticus: {_clip(text, 140)}")

    header = f"Session summary ({len(user_bits)} user turn(s), {len(assistant_bits)} assistant turn(s))."
    body = "\n".join(bullets)
    summary = f"{header}\n{body}".strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"
    return summary


def should_auto_summarize(
    *,
    enabled: bool,
    store_summaries: bool,
    memory_enabled: bool,
    user_turns_since_summary: int,
    every_n_turns: int,
) -> bool:
    """Return True when an automatic summary should be written."""
    if not enabled or not store_summaries or not memory_enabled:
        return False
    if every_n_turns <= 0:
        return False
    return user_turns_since_summary >= every_n_turns


# Kept for older imports; prefer summarize_conversation.
def summarize_transcript_stub(_text: str) -> str:
    """Deprecated stub — use summarize_conversation(messages)."""
    raise NotImplementedError(
        "summarize_transcript_stub is retired. Use summarize_conversation(messages) "
        "for local privacy-safe summaries."
    )
