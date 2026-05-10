"""Phase 5 — local wake phrase detection on transcripts (no cloud audio)."""

from __future__ import annotations

import re
import unicodedata

from atticus.core.config import VoiceConfig


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def wake_match(transcript: str, voice: VoiceConfig) -> bool:
    """
    Return True if any configured wake phrase appears in the transcript.

    Matching is substring-based on letters/digits (punctuation-insensitive).
    """
    if not transcript.strip():
        return False
    hay = _normalize(transcript)
    if not hay:
        return False
    for phrase in voice.wake_phrases:
        needle = _normalize(phrase)
        if not needle:
            continue
        if needle in hay:
            return True
    return False


def strip_leading_wake(transcript: str, voice: VoiceConfig) -> str:
    """Remove the first matched wake phrase from the start of the transcript."""
    t = transcript.strip()
    for phrase in sorted(voice.wake_phrases, key=len, reverse=True):
        pat = re.compile(re.escape(phrase), re.IGNORECASE)
        t2 = pat.sub("", t, count=1).strip(" ,.-!?")
        if t2 != t:
            return t2
    return t
