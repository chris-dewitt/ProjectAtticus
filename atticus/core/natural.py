from __future__ import annotations

import re

_REMEMBER = re.compile(r"^(?:hey\s+)?atticus,?\s+remember(?:\s+that)?\s+(.+)$", re.IGNORECASE)
_FORGET = re.compile(r"^(?:hey\s+)?atticus,?\s+forget(?:\s+that)?\s+(.+)$", re.IGNORECASE)
_RECALL = re.compile(r"^(?:hey\s+)?atticus,?\s+what\s+do\s+you\s+remember(?:\s+about)?\s*(.*)$", re.IGNORECASE)


def parse_natural_command(line: str) -> tuple[str, str] | None:
    """
    Parse natural-language memory commands.

    Returns (verb, payload) where verb is remember|forget|recall, or None.
    """
    m = _REMEMBER.match(line.strip())
    if m:
        return "remember", m.group(1).strip()
    m = _FORGET.match(line.strip())
    if m:
        return "forget", m.group(1).strip()
    m = _RECALL.match(line.strip())
    if m:
        return "recall", (m.group(1) or "").strip()
    return None
