from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from atticus.core.config import VoiceConfig
from atticus.voice.tts import VoiceOutput, plain_text_for_tts


def test_plain_text_for_tts_strips_bold() -> None:
    assert "bold" in plain_text_for_tts("this is **bold** here")
    assert "**" not in plain_text_for_tts("this is **bold** here")


def test_plain_text_for_tts_strips_inline_code() -> None:
    out = plain_text_for_tts("Use the `foo` flag")
    assert "foo" in out
    assert "`" not in out


def test_voice_muted_skips_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    class _Engine:
        def say(self, t: str) -> None:
            called.append(t)

        def runAndWait(self) -> None:
            pass

    class _Py:
        @staticmethod
        def init() -> _Engine:
            return _Engine()

    monkeypatch.setattr("atticus.voice.tts._pyttsx3", _Py)
    buf = StringIO()
    console = Console(file=buf, width=80, force_terminal=True)
    voice = VoiceConfig(spoken_responses=True, muted=True, tts_engine="pyttsx3")
    out = VoiceOutput(voice, console)
    out.speak("hello")
    assert called == []


def test_voice_speak_invokes_pyttsx3(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    class _Engine:
        def say(self, t: str) -> None:
            called.append(t)

        def runAndWait(self) -> None:
            pass

    class _Py:
        @staticmethod
        def init() -> _Engine:
            return _Engine()

    monkeypatch.setattr("atticus.voice.tts._pyttsx3", _Py)
    buf = StringIO()
    console = Console(file=buf, width=80, force_terminal=True)
    voice = VoiceConfig(spoken_responses=True, muted=False, tts_engine="pyttsx3")
    out = VoiceOutput(voice, console)
    out.speak("**Hi** Boss")
    assert len(called) == 1
    assert "Hi" in called[0]
    assert "**" not in called[0]


def test_unsupported_engine_never_calls_init(monkeypatch: pytest.MonkeyPatch) -> None:
    inits: list[int] = []

    class _Bad:
        @staticmethod
        def init() -> object:
            inits.append(1)
            raise RuntimeError("should not be used")

    monkeypatch.setattr("atticus.voice.tts._pyttsx3", _Bad)
    buf = StringIO()
    console = Console(file=buf, width=80, force_terminal=True)
    voice = VoiceConfig(spoken_responses=True, muted=False, tts_engine="piper")
    out = VoiceOutput(voice, console)
    out.speak("hello")
    assert inits == []
