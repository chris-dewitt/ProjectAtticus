from __future__ import annotations

import wave
from io import BytesIO

from atticus.voice.recording import pcm16_to_wav_bytes


def test_pcm16_to_wav_roundtrip() -> None:
    pcm = (32767).to_bytes(2, "little", signed=True) * 800
    wav = pcm16_to_wav_bytes(pcm, sample_rate=16000)
    with wave.open(BytesIO(wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert len(wf.readframes(wf.getnframes())) == len(pcm)
