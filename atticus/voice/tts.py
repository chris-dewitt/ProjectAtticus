"""Offline text-to-speech (Phase 3: pyttsx3 on Windows, graceful fallback)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rich.console import Console

from atticus.core.config import VoiceConfig

try:
    import pyttsx3 as _pyttsx3
except ImportError:  # pragma: no cover - exercised via tests with monkeypatch
    _pyttsx3 = None


def plain_text_for_tts(text: str) -> str:
    """Strip common Markdown so TTS does not read asterisks and hashes aloud."""
    t = text.replace("```", " ")
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


@dataclass
class VoiceOutput:
    """Session-scoped TTS: config gate, runtime mute, one-shot init, failure-safe speak."""

    voice: VoiceConfig
    console: Console
    _engine: object | None = field(default=None, repr=False)
    _init_failed: bool = field(default=False, repr=False)
    _warned_init: bool = field(default=False, repr=False)
    runtime_muted: bool = field(init=False)

    def __post_init__(self) -> None:
        self.runtime_muted = bool(self.voice.muted)

    def set_muted(self, muted: bool) -> None:
        self.runtime_muted = muted

    def is_effective_speech_on(self) -> bool:
        return bool(self.voice.spoken_responses) and not self.runtime_muted

    def _ensure_engine(self) -> object | None:
        if self._init_failed:
            return None
        if self._engine is not None:
            return self._engine
        if self.voice.tts_engine.lower() != "pyttsx3":
            if not self._warned_init:
                self.console.print(
                    f"[dim]TTS engine {self.voice.tts_engine!r} is not supported yet; skipping speech.[/dim]"
                )
                self._warned_init = True
            self._init_failed = True
            return None
        if _pyttsx3 is None:
            if not self._warned_init:
                self.console.print(
                    "[yellow]pyttsx3 is not installed; spoken output is disabled. "
                    "Install with: pip install pyttsx3[/yellow]"
                )
                self._warned_init = True
            self._init_failed = True
            return None
        try:
            engine = _pyttsx3.init()
            if self.voice.tts_rate is not None:
                try:
                    engine.setProperty("rate", int(self.voice.tts_rate))
                except Exception:
                    pass
            self._engine = engine
            return self._engine
        except Exception as exc:
            self._init_failed = True
            if not self._warned_init:
                self.console.print(f"[yellow]TTS could not start ({exc}). Replies stay on-screen only.[/yellow]")
                self._warned_init = True
            return None

    def speak(self, text: str) -> None:
        """Speak plain text if configured; never raises to callers."""
        if not self.is_effective_speech_on() or not text.strip():
            return
        engine = self._ensure_engine()
        if engine is None:
            return
        utterance = plain_text_for_tts(text)
        if not utterance:
            return
        try:
            engine.say(utterance)
            engine.runAndWait()
        except Exception as exc:
            self.console.print(f"[yellow]TTS playback failed ({exc}). Continuing without audio.[/yellow]")


def maybe_speak(text: str, *, enabled: bool) -> None:
    """Backward-compatible no-op stub (prefer VoiceOutput.speak in the CLI)."""
    del enabled
    if not text.strip():
        return
    _console = Console()
    _console.print("[dim]maybe_speak legacy path: use VoiceOutput.speak[/dim]")
