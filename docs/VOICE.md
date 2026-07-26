# Voice Design — ProjectAtticus

## Product goal

Atticus should ultimately be fully operational by voice:

- The Speaker says "Atticus" or "Hey Atticus."
- Atticus wakes.
- The Speaker speaks request.
- Atticus thinks, acts if allowed, and speaks the answer aloud.

The Speaker wants spoken responses always on by default.

## Engineering reality

The target machine is an older Dell Inspiron Windows laptop. Prioritize reliability and low resource usage.

## Phased voice plan

### Phase 1: TTS only

After CLI text works, add spoken responses.

Recommended first TTS engine:

- `pyttsx3` for Windows offline TTS.

Why:

- simple;
- offline;
- usually works with installed Windows voices;
- low setup burden.

Later option:

- Piper for better local neural voice if performance is acceptable.

### Phase 2: Push-to-talk STT

Even though push-to-talk is only a fallback, it is the safest way to validate microphone capture and transcription before always-listening wake word.

Possible STT options:

- local lightweight Whisper variant;
- faster-whisper with small/int8 model if the laptop can handle it;
- Vosk for lightweight offline recognition;
- cloud STT only if The Speaker explicitly allows audio to leave the laptop.

Default privacy stance: local STT.

### Phase 3: Wake word

Wake-word detection must be local. Do not stream ambient audio to the cloud.

Wake phrases:

- Atticus
- Hey Atticus
- Atticus, please
- Atticus, old son
- configurable variants

Potential wake engines:

- Picovoice Porcupine;
- openWakeWord;
- custom lightweight phrase detector later.

### Phase 4: Always-listening loop

Before shipping always-listening mode:

- visible status indicator;
- mute/kill switch;
- config toggle;
- local wake-word processing documentation;
- no cloud streaming of ambient audio;
- log state transitions, not audio.

## Voice config

```yaml
voice:
  spoken_responses: true
  tts_engine: pyttsx3
  stt_engine: local
  wake_word_engine: local
  wake_phrases:
    - Atticus
    - Hey Atticus
    - Atticus, please
  push_to_talk_enabled: true
  cloud_audio_allowed: false
```

## Failure behavior

If TTS fails:

- print the response;
- show a clear warning;
- do not crash.

If STT fails:

- fall back to typing;
- show troubleshooting steps.

If wake word fails:

- fall back to push-to-talk or typed CLI;
- do not block normal app usage.
