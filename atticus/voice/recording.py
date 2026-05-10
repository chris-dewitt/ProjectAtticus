"""Capture mono PCM from the default (or configured) microphone."""

from __future__ import annotations

import io
import wave

from atticus.core.errors import VoiceInputError


def _sd():
    try:
        import sounddevice as sd
    except ImportError:
        return None
    return sd


def _resolve_device(device: str | None) -> int | str | None:
    if device is None or device.strip() == "":
        return None
    s = device.strip()
    if s.isdigit():
        return int(s)
    return s


def record_pcm16_mono(*, seconds: float, sample_rate: int, device: str | None) -> bytes:
    """Record mono 16-bit little-endian PCM (for Vosk WAV packaging)."""
    sd = _sd()
    if sd is None:
        raise VoiceInputError("sounddevice is not installed. Install STT extras: pip install -e \".[stt]\"")
    import numpy as np

    if seconds <= 0 or seconds > 120:
        raise VoiceInputError("Recording duration must be between 0 and 120 seconds.")
    frames = int(seconds * sample_rate)
    dev = _resolve_device(device)
    try:
        audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32", device=dev)
        sd.wait()
    except OSError as exc:
        raise VoiceInputError(
            "Microphone capture failed (permission or device). On Windows, check Privacy → Microphone "
            f"for Terminal/Python. Details: {exc}"
        ) from exc
    except Exception as exc:
        raise VoiceInputError(f"Audio capture error: {exc}") from exc

    mono = np.clip(audio.reshape(-1), -1.0, 1.0)
    pcm = (mono * 32767.0).astype(np.int16).tobytes()
    return pcm


def pcm16_to_wav_bytes(pcm_s16le: bytes, *, sample_rate: int) -> bytes:
    """Wrap raw PCM in a minimal WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_s16le)
    return buf.getvalue()


def stt_dependencies_installed() -> bool:
    try:
        import numpy  # noqa: F401
        import sounddevice  # noqa: F401
    except ImportError:
        return False
    return True
