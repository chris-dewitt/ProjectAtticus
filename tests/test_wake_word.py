from __future__ import annotations

from atticus.core.config import VoiceConfig
from atticus.voice.wake_word import strip_leading_wake, wake_match


def test_wake_match_basic() -> None:
    v = VoiceConfig.model_validate({"wake_phrases": ["Hey Atticus"]})
    assert wake_match("hey atticus what's the plan", v) is True
    assert wake_match("nothing here", v) is False


def test_strip_leading_wake() -> None:
    v = VoiceConfig.model_validate({"wake_phrases": ["Atticus"]})
    assert strip_leading_wake("Atticus please open the pod bay doors", v).lower().startswith("please")
