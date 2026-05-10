# Local audio privacy — Phases 4 and 5

## What leaves the machine

- **Push-to-talk (`/ptt`)** and **wake flow (`/wake`)** capture audio from your microphone and run **offline Vosk** recognition on the laptop. Raw audio is **not** uploaded to OpenAI, Anthropic, Gemini, or any other cloud service as part of STT.
- Only the **recognized text** transcript is sent onward — the same as if you had typed it into the CLI — and only when you continue into a normal chat turn (which uses your configured LLM provider).

## Kill switch

- **`/voice-kill`** disables all microphone capture commands (`/ptt`, `/wake`) until you run **`/voice-arm`**. This is immediate and does not require editing YAML.

## Permissions

- Windows may block the terminal until **Settings → Privacy → Microphone** allows access for your terminal or Python. Denial is surfaced as a clear error; the text chat loop keeps running.

## Models

- Download a **Vosk** model (for example `vosk-model-small-en-us-0.15`) from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models), unpack it locally, and set **`voice.vosk_model_path`** in `config/atticus.yaml` to that folder. Do not commit model files to git.

## Wake phrases

- Wake detection in Phase 5 is **phrase matching on the local transcript** of the wake clip, followed by a separate command clip. There is no always-listening cloud stream.
