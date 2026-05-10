# ProjectAtticus

Atticus is a local-first Windows personal assistant designed to live on the user's laptop, respond to the wake word "Atticus" or "Hey Atticus," speak aloud by default, and use OpenAI, Claude, or Gemini as an interchangeable underlying brain.

Atticus is intentionally built as a serious personal software project: privacy-conscious, provider-agnostic, modular, voice-first, and agent-friendly for Cursor and Codex.

## North star

Build a full-character Southern gentleman assistant: kind, capable, loyal, funny in a restrained way, and always useful. Atticus is a wise old advisor who loves everybody, but Boss most of all.

## First milestone

The first working demo is intentionally narrow:

1. CLI chat with the Atticus persona.
2. OpenAI as the default provider.
3. Provider-router skeleton for OpenAI, Claude, and Gemini.
4. Config loaded from local YAML plus environment variables.
5. Conversation summaries and user preferences stored locally.
6. Permission-gated tool framework, but no dangerous tools enabled by default.
7. Spoken response interface stubbed for the next milestone.

Voice, wake word, desktop tray, calendar/email, and full local automation come after the CLI is reliable.

## Repo target path

Development target:

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

- `AGENTS.md`: primary agent instructions for Codex and other coding agents.
- `.cursor/rules/*.mdc`: Cursor-specific persistent project rules.
- `docs/PRD.md`: product requirements.
- `docs/ARCHITECTURE.md`: target architecture.
- `docs/SECURITY.md`: privacy, permission gates, threat model.
- `docs/ROADMAP.md`: phased build plan.
- `docs/PERSONA.md`: Atticus character and voice.
- `docs/API_KEYS_SETUP.md`: API key setup for OpenAI, Claude, and Gemini.
- `docs/CODEX_TASKS.md`: high-quality prompts to feed Codex.
- `docs/CURSOR_TASKS.md`: high-quality prompts to feed Cursor.

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

Prerequisites: **Python 3.11+** on Windows, PowerShell, and an OpenAI API key for live replies (tests stay offline).

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
copy .env.example .env
# Edit .env and set OPENAI_API_KEY=... (never commit .env)
# Optional local config (otherwise atticus.example.yaml is used with a warning):
copy config\atticus.example.yaml config\atticus.yaml
pytest
python -m atticus
```

Slash commands in the CLI: `/help`, `/exit`, `/provider`, `/mode`, `/memory`, `/remember`, `/forget`, plus Phase 2 memory and safety commands (`/memory items|prefs|summaries|audit`, `/pref`, `/recall`, `/summary add`, `/forget match|pref|summary`, natural-language remember/forget/recall). Bulk note delete (`/forget all` or substring forget) asks for confirmation; tool decisions are written to the local audit table.

Do not add real keys to `.env.example`. Keep `.env` and `config/atticus.yaml` out of git if they contain secrets or machine-specific paths.
