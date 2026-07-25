"""Normalize OpenAI-style chat messages for Anthropic and Gemini adapters."""

from __future__ import annotations

from typing import Any


def split_system_and_turns(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    """
    Return ``(system_text, turns)`` where turns are user/assistant only.

    Consecutive system messages are joined. Non-text content is coerced with ``str()``.
    """
    system_parts: list[str] = []
    turns: list[dict[str, str]] = []
    for msg in messages:
        role = str(msg.get("role", "")).strip().lower()
        content = msg.get("content", "")
        text = content if isinstance(content, str) else str(content)
        if role == "system":
            if text.strip():
                system_parts.append(text.strip())
            continue
        if role in {"user", "assistant"}:
            turns.append({"role": role, "content": text})
            continue
        # Ignore unknown roles rather than failing the whole request.
    return "\n\n".join(system_parts).strip(), turns


def anthropic_messages(turns: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Map assistant→assistant, user→user; drop leading assistants (Anthropic requirement)."""
    out: list[dict[str, Any]] = []
    for turn in turns:
        role = "assistant" if turn["role"] == "assistant" else "user"
        out.append({"role": role, "content": turn["content"]})
    while out and out[0]["role"] == "assistant":
        out.pop(0)
    if not out:
        out = [{"role": "user", "content": "(empty)"}]
    return out


def gemini_contents(turns: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Map OpenAI roles to Gemini ``user`` / ``model`` contents."""
    contents: list[dict[str, Any]] = []
    for turn in turns:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})
    if not contents:
        contents = [{"role": "user", "parts": [{"text": "(empty)"}]}]
    return contents
