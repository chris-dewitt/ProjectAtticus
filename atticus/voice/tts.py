"""Text-to-speech (stub until Phase 3)."""

from __future__ import annotations

from rich.console import Console

_console = Console()


def maybe_speak(text: str, *, enabled: bool) -> None:
    """If enabled, speak text; Phase 1 only logs intent (no audio engine yet)."""
    if not enabled or not text.strip():
        return
    _console.print("[dim]TTS stub: spoken output is configured on, but audio playback is not implemented yet.[/dim]")
