"""Local speech-to-text (Phase 4: Vosk offline)."""

from __future__ import annotations

import json
import wave
from io import BytesIO
from pathlib import Path

from rich.console import Console

from atticus.core.config import VoiceConfig
from atticus.core.errors import VoiceInputError
from atticus.voice.recording import pcm16_to_wav_bytes, record_pcm16_mono, stt_dependencies_installed

try:
    from vosk import KaldiRecognizer as _KaldiRecognizer
    from vosk import Model as _VoskModel
except ImportError:  # pragma: no cover
    _VoskModel = None  # type: ignore[misc, assignment]
    _KaldiRecognizer = None  # type: ignore[misc, assignment]


def stt_engine_uses_vosk(voice: VoiceConfig) -> bool:
    return voice.stt_engine.lower() in {"vosk", "local"}


def vosk_import_ok() -> bool:
    return _VoskModel is not None and _KaldiRecognizer is not None


def transcribe_wav_bytes(wav_bytes: bytes, *, model_dir: Path, console: Console | None = None) -> str:
    """Run Vosk on a complete WAV byte blob; returns normalized transcript."""
    if not vosk_import_ok():
        raise VoiceInputError("vosk is not installed. Install STT extras: pip install -e \".[stt]\"")
    if not model_dir.is_dir():
        raise VoiceInputError(
            f"Vosk model directory not found: {model_dir}. Download a small English model from "
            "https://alphacephei.com/vosk/models and set voice.vosk_model_path in config."
        )
    try:
        model = _VoskModel(str(model_dir))
    except Exception as exc:
        raise VoiceInputError(f"Failed to load Vosk model from {model_dir}: {exc}") from exc

    with wave.open(BytesIO(wav_bytes), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise VoiceInputError("Expected mono 16-bit WAV for Vosk.")
        rate = wf.getframerate()
        rec = _KaldiRecognizer(model, rate)
        parts: list[str] = []
        while True:
            data = wf.readframes(8000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                j = json.loads(rec.Result())
                t = (j.get("text") or "").strip()
                if t:
                    parts.append(t)
        j = json.loads(rec.FinalResult())
        t = (j.get("text") or "").strip()
        if t:
            parts.append(t)
    text = " ".join(parts).strip()
    if not text and console is not None:
        console.print("[dim](empty transcript — try speaking closer or check the model.)[/dim]")
    return text


def record_and_transcribe(
    voice: VoiceConfig,
    *,
    seconds: float,
    console: Console,
    label: str = "Recording",
) -> str:
    """Capture from the mic and return transcript text."""
    if not stt_dependencies_installed():
        raise VoiceInputError("sounddevice/numpy missing. Install: pip install -e \".[stt]\"")
    if not stt_engine_uses_vosk(voice):
        raise VoiceInputError(
            f"voice.stt_engine is {voice.stt_engine!r}. Set to vosk (or local) and configure voice.vosk_model_path."
        )
    if not voice.vosk_model_path:
        raise VoiceInputError("voice.vosk_model_path is not set. Point it at an unpacked Vosk model directory.")
    model_dir = Path(voice.vosk_model_path).expanduser()
    sr = int(voice.sample_rate_hz)
    console.print(f"[yellow]{label} {seconds:g}s — speak now…[/yellow]")
    pcm = record_pcm16_mono(seconds=seconds, sample_rate=sr, device=voice.microphone_device)
    wav = pcm16_to_wav_bytes(pcm, sample_rate=sr)
    text = transcribe_wav_bytes(wav, model_dir=model_dir, console=console)
    console.print(f"[bold cyan]Transcript:[/bold cyan] {text or '(empty)'}")
    return text
