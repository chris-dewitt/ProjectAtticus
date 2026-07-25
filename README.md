# ProjectAtticus

Atticus is a local-first Windows personal assistant designed to live on the user's laptop, respond to the wake word "Atticus" or "Hey Atticus," speak aloud by default, and use OpenAI, Claude, or Gemini as an interchangeable underlying brain.

Atticus is intentionally built as a serious personal software project: privacy-conscious, provider-agnostic, modular, voice-first, and agent-friendly for Cursor and Codex.

## Current status (Track A) vs portfolio north star (Track B)

**Track A — shipped personal assistant (this is what runs today):**

- Rich CLI (`atticus` / `python -m atticus`) with Atticus persona
- OpenAI + Claude/Gemini providers (optional `.[providers]`), YAML + `.env` config
- SQLite memory (notes, preferences, summaries, tool audit) with local auto-summaries
- Permission gates and y/N approvals for risky actions
- Optional TTS, local PTT/wake (Vosk), opt-in file/git/GitHub/Gmail/Calendar/browse tools
- Thin Textual desk companion

Package version `1.0.0` labels this Track A milestone. Tray/autostart and a full GUI chat remain unfinished.

**Track B — portfolio agent platform (planned, not shipped):**

- Bounded orchestrator, policy engine, API/traces/evals per [`SPEC.md`](SPEC.md)
- Engineering bar in [`docs/SHARED_ENGINEERING_STANDARD.md`](docs/SHARED_ENGINEERING_STANDARD.md)
- Honest capability map in [`docs/PORTFOLIO_ALIGNMENT.md`](docs/PORTFOLIO_ALIGNMENT.md)

Do not present FastAPI, Postgres, Next.js, sandboxes, or M0–M5 as already complete.

## North star

Build a full-character Southern gentleman assistant: kind, capable, loyal, funny in a restrained way, and always useful. Atticus is a wise old advisor who loves everybody, but Boss most of all. The longer-term portfolio architecture adds auditable agent workflows without abandoning that personal assistant.

## Track A foundation (already implemented)

1. CLI chat with the Atticus persona.
2. OpenAI as the default provider.
3. Provider-router skeleton for OpenAI, Claude, and Gemini.
4. Config loaded from local YAML plus environment variables.
5. Conversation summaries and user preferences stored locally.
6. Permission-gated tool framework; dangerous tools off by default.
7. Optional spoken replies, PTT/wake, and MVP local tools (enable in config).

## Quick start (download and run)

1. **Clone** this repository and `cd` into the project folder (the directory that contains `pyproject.toml`).
2. Install **Python 3.11+** and use a virtual environment (recommended).

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
# Edit .env: set OPENAI_API_KEY=... (never commit .env)
```

3. **Run** from the repo root (so `prompts/` and bundled config resolve correctly):

```powershell
atticus
```

If you prefer not to use the installed script: `python -m atticus`.

4. **Config:** If `config/atticus.yaml` is missing, Atticus loads `config/atticus.example.yaml` and prints a one-time warning. Copy the example to `config/atticus.yaml` only when you want machine-specific overrides (paths, voice, tools).

5. **Verify (optional):** `pytest` — tests do not call paid APIs.

6. **Optional extras:** `pip install -e ".[providers]"` for Claude/Gemini SDKs, `pip install -e ".[gmail]"` for Gmail OAuth, `pip install -e ".[stt]"` for local microphone + Vosk, `pip install -e ".[desktop]"` for `atticus-desktop`, `pip install -e ".[secrets]"` for OS keyring-backed tokens.

## Repo target path

Primary development machine (yours may differ):

```text
C:\Users\DELL\Documents\GitHub\ProjectAtticus
```

Agents must assume Windows first. Use PowerShell-compatible instructions unless a cross-platform command is safer.

## Recommended implementation direction

Use Python for v1 because it is the fastest path to a secure, working, local-first assistant on an older Dell Inspiron laptop. Python also has strong libraries for CLI apps, local storage, speech-to-text, text-to-speech, PDF parsing, file search, and API clients.

Recommended phased stack:

- v0.1: Python CLI app.
- v0.2: Python CLI + optional voice output.
- v0.3: Push-to-talk and wake-word prototype.
- v0.4: Local desktop shell or system tray.
- v1.0: Desktop assistant with voice-first operation, safe local tools, and provider routing.

## Core docs

- `AGENTS.md`: primary agent instructions (includes dual-track reading order).
- `SPEC.md`: Track B portfolio architecture north star.
- `docs/PORTFOLIO_ALIGNMENT.md`: Track A vs Track B crosswalk (read before claiming milestones).
- `docs/SHARED_ENGINEERING_STANDARD.md`: portfolio engineering bar.
- `.cursor/rules/*.mdc`: Cursor-specific persistent project rules.
- `docs/PRD.md`: product requirements (Track A).
- `docs/ARCHITECTURE.md`: current implementation vs target platform.
- `docs/SECURITY.md`: privacy, permission gates, threat model.
- `docs/ROADMAP.md`: Track A phases and Track B milestones.
- `docs/PERSONA.md`: Atticus character and voice.
- `docs/EVALUATION.md` / `docs/MODEL_CARD.md` / `docs/DATA_CARD.md`: quality and data honesty.
- `docs/API_KEYS_SETUP.md`: API key setup for OpenAI, Claude, and Gemini.
- `CHANGELOG.md`: milestone history.
- `docs/CODEX_TASKS.md` / `docs/CURSOR_TASKS.md`: task prompts for agents.

## Non-negotiables

1. Privacy is a product feature, not an afterthought.
2. No API keys, OAuth tokens, or secrets may be committed to the repo.
3. Atticus must ask before sending file contents to cloud model providers.
4. Shell commands require explicit confirmation every time.
5. File edits require explicit confirmation every time outside safe scratch/workspace flows.
6. Raw conversations should not be stored by default; store summaries and preferences.
7. The assistant must support a built-in "forget this" flow.
8. OpenAI is the default provider, but provider switching/routing must be designed from the beginning.
9. Atticus should eventually speak aloud by default, but the first milestone is CLI chat.
10. The persona should be full-character Southern gentleman, but never racist, exclusionary, cruel, or servile.

## Phase 1 — Windows setup (CLI)

Same steps as **Quick start** above. After `pip install -e ".[dev]"`, you can run `pytest` then `atticus` (or `python -m atticus`).

## Phase 3 — Spoken replies (offline TTS)

Replies are spoken with **`pyttsx3`** (Windows SAPI voices) when `voice.spoken_responses` is true in config. Use **`/mute`** and **`/unmute`** for a runtime pause without editing YAML; **`/voice`** shows the current flags. If the engine fails to start or playback errors, you still get full text output and a yellow warning—nothing in the chat loop hard-depends on audio.

Optional tuning: set `voice.tts_rate` to an integer (words per minute) if your machine supports it. Set `voice.muted: true` in YAML to start sessions silent until Boss runs `/unmute`.

## Phase 4 — Speech in (push-to-talk, local STT)

Install optional STT stack, then point **`voice.vosk_model_path`** at an unpacked Vosk model directory (see `docs/VOICE_LOCAL_AUDIO.md`):

```powershell
pip install -e ".[dev,stt]"
```

Use **`/ptt`** (or **`/listen`**) to record from the mic for a few seconds and send the transcript into the same chat path as typed text. Optional seconds: `/ptt 6`.

## Phase 5 — Wake phrase (local, two clips)

**`/wake`** records a **wake clip** (looks for configured `voice.wake_phrases` in the transcript), then a **command clip**. No ambient audio is streamed to the cloud. **`/voice-kill`** immediately blocks **`/ptt`** and **`/wake`**; **`/voice-arm`** restores them.

Slash commands in the CLI: `/help`, `/exit`, `/provider` (`openai` | `anthropic` | `gemini`), `/mode`, `/memory`, `/remember`, `/forget`, Phase 2 memory commands (`/memory items|prefs|summaries|audit`, `/pref`, `/recall`, `/summary add|session`, `/forget match|pref|summary`, natural-language remember/forget/recall), Phase 3 **`/mute`**, **`/unmute`**, **`/voice`**, and Phase 4–5 **`/ptt`**, **`/listen`**, **`/wake`**, **`/voice-kill`**, **`/voice-arm`**. Auto session summaries (local bullets only) can write on a turn cadence and on `/exit` when `memory.auto_summarize` is true. Bulk note delete asks for confirmation; tool decisions are audited.

## Phases 6–9 (tools, integrations, desk) — Track A MVP (partial)

- **Phase 6 — Local files:** with `tools.enabled` and `tools.files.enabled`, use **`/file read`**, **`/file search`**, **`/file write`**, **`/code-search`**, **`/summarize`** (paths must stay under `tools.approved_paths`). Writes and cloud-bound summarizes go through the same **y/N approval + audit** pattern as earlier phases. Optional PDF text: `pip install -e ".[pdf]"`.
- **Phase 7 — Coding / git:** with `tools.shell.enabled`, **`/git …`** (read-only allow-list), **`/patch plan|apply <diff>`** (unified diff under `approved_paths`), and **`/test <pytest …>`** (allow-listed pytest only). No arbitrary shell.
- **Phase 8 — Integrations:** **`/gh`**, **`/gmail`**, **`/cal`** (Calendar read/write with double-confirm), **`/open`**, **`/browse`** + **`/citations`** (fetch + local citation JSON; optional host allowlist). Google APIs: `pip install -e ".[gmail]"` + OAuth client JSON (see `docs/API_KEYS_SETUP.md`).
- **Phase 9 — Desk:** optional Textual hub — install **`pip install -e ".[desktop]"`** then run **`atticus-desktop`**. Companion window only; full chat stays **`python -m atticus`**.

JS-heavy browser automation, autostart tray, and a full GUI chat are **not** finished here. Track B platform pieces (API, orchestrator, traces, EvalForge) are documented in `SPEC.md` and are also **not** finished.

### Full product — one step at a time (backlog)

1. **Done:** shared **`get_credential(env)`** — env first, optional **keyring**; OpenAI/Anthropic/Gemini all use it.
2. **Done:** authenticated GitHub CLI — **`/gh me|repos|prs|issues`**.
3. **Done:** Claude + Gemini provider implementations (`pip install -e ".[providers]"`).
4. **Done:** local auto conversation summarizer (`/summary session`, auto on cadence/exit).
5. **Done:** Gmail OAuth + confirm-before-send (`/gmail …`).
6. **Done:** Calendar read + double-confirm writes (`/cal …`).
7. **Done:** Browser fetch helper + citation capture (`/browse`, `/citations`).
8. **Done:** Phase 7 deepen — patch plan/apply + gated pytest (`/patch`, `/test`).
9. **Next good step:** **Tray / autostart** and richer **desktop** UI wiring into the same tool gates.

Do not add real keys to `.env.example`. Keep `.env` and `config/atticus.yaml` out of git if they contain secrets or machine-specific paths.
