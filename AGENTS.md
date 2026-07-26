# AGENTS.md — ProjectAtticus

These instructions apply to all coding agents working in this repository, including Codex, Cursor, and similar agentic coding tools.

## Required reading order

1. `AGENTS.md` (this file)
2. `SPEC.md` (Track B portfolio architecture north star)
3. `docs/SHARED_ENGINEERING_STANDARD.md` (portfolio engineering bar)
4. `docs/PORTFOLIO_ALIGNMENT.md` (honest Track A vs Track B map)
5. Existing product docs (`docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/ROADMAP.md`, `docs/PERSONA.md`, and nearby implementation files)

## Dual-track rules

- **Track A (shipped):** Windows personal assistant under `atticus/` — CLI, persona, SQLite memory, permission gates, optional voice, opt-in tools. This is the working product.
- **Track B (planned):** Agent platform in `SPEC.md` — orchestrator, policy engine, API/traces/evals. Not shipped.
- Do **not** re-scaffold Phase 1 CLI; it already exists.
- Do **not** build Track B milestones (M0–M5) unless The Speaker explicitly asks for that milestone.
- When extending tools or approvals, prefer SPEC-shaped boundaries: typed tools, audit events, no silent external writes, treat retrieved content as untrusted.
- Stack defaults in the shared standard (FastAPI, Postgres, Next.js, Docker, OTel, Azure) are aspirational until an ADR adopts them (see ADR-009).

## Project mission

ProjectAtticus is a Windows-first, local-first personal AI assistant named Atticus. Atticus lives on the user's laptop, responds to "Atticus," "Hey Atticus," and close variants, speaks aloud by default, and can use OpenAI, Claude, or Gemini as an interchangeable LLM brain.

The user's selected design constraints:

- Primary OS: Windows.
- Target machine: older Dell Inspiron laptop, approximately five or more years old.
- Default LLM provider: OpenAI.
- Provider routing: automatic once implemented.
- Voice: desired immediately and ultimately always spoken aloud.
- Wake phrases: "Atticus," "Hey Atticus," and reasonable variants.
- Push-to-talk: fallback only if absolutely necessary.
- Persona: full-character Southern gentleman advisor; kind, warm, loyal, and dramatic enough to be memorable.
- Address user as: The Speaker (never Boss).
- Atticus identity: The Listener.
- Personality boundary: no racism, no bigotry, no exclusionary stereotypes; Atticus loves everybody.
- Privacy: extremely important.
- Memory: on by default, but only summaries and preferences by default.
- Raw conversations: do not store by default.
- "Forget this" command: required.
- Cloud file handling: ask before sending file contents to any cloud provider.
- Shell commands: require explicit confirmation every time.
- File edits: require explicit confirmation every time, unless operating in a clearly designated generated-output/scratch path.
- Initial demo: CLI chat with Atticus persona.

## Current repo path assumption

Assume the repo is located at:

```text
C:\Users\DELL\Documents\GitHub\ProjectAtticus
```

Use Windows and PowerShell instructions by default.

## Build philosophy

Build the smallest safe working system first. Avoid prematurely building a fragile JARVIS clone. The sequence is:

1. CLI Atticus with persona and provider abstraction.
2. Config and secrets management.
3. Local memory for summaries/preferences.
4. Permissioned tool framework.
5. Voice output.
6. Speech input.
7. Wake word.
8. Desktop/tray interface.
9. Gmail, Calendar, GitHub, browser, and richer tools.

Do not skip the CLI foundation.

## Recommended implementation stack

Prefer Python for v1 unless a strong reason emerges otherwise.

Recommended libraries and components:

- CLI: `typer` or `rich`.
- Config: `pydantic-settings`, `PyYAML`, `.env` via `python-dotenv`.
- OpenAI: official OpenAI Python SDK.
- Anthropic: official Anthropic Python SDK.
- Gemini: official Google GenAI SDK.
- Local database: SQLite.
- ORM/query layer: `sqlite3`, `SQLModel`, or `SQLAlchemy`; keep simple.
- Memory embeddings: defer until the simple store works.
- Local STT on older laptop: start with small local models; use faster-whisper only when performance is acceptable.
- Local TTS: start with `pyttsx3` on Windows for reliability, then add Piper for better local voices.
- Wake word: prototype after push-to-talk works. Prefer local wake word detection.
- Desktop UI: defer. Consider Textual, PySide6, or Tauri later.

## Architecture requirements

Maintain these boundaries:

```text
atticus/
  app.py or __main__.py
  core/
    config.py
    persona.py
    router.py
    permissions.py
  providers/
    base.py
    openai_provider.py
    anthropic_provider.py
    gemini_provider.py
  memory/
    store.py
    summarizer.py
  tools/
    base.py
    files.py
    shell.py
    apps.py
    browser.py
    calendar.py
    email.py
  voice/
    tts.py
    stt.py
    wake_word.py
  prompts/
    system.py
    modes.py
  tests/
```

Do not create circular imports. Keep provider-specific logic inside `providers/`. Keep tool permission logic centralized.

## Provider abstraction

All providers must implement one common interface. Do not let the rest of the app care whether the response came from OpenAI, Claude, or Gemini.

Minimum interface:

```python
class LLMProvider(Protocol):
    name: str

    def generate(self, messages: list[dict], *, tools: list | None = None, mode: str | None = None) -> str:
        ...
```

Provider implementations must:

- Load credentials from environment variables or secure keyring only.
- Never log API keys.
- Normalize provider errors into internal exceptions.
- Support future streaming without requiring app-level rewrites.
- Support timeout and retry configuration.

## Automatic provider routing

Design provider routing early, but keep v0.1 simple.

Default v0.1 behavior:

- Use OpenAI unless the user explicitly asks to switch.
- Include a router interface and placeholder decision logic.

Future routing behavior:

- OpenAI default for general reasoning, coding, and tool orchestration.
- Claude optional for long-form writing, code review, and document reasoning.
- Gemini optional for multimodal and Google ecosystem tasks.
- Always let The Speaker override the provider manually.

## Security and privacy requirements

Never compromise these:

1. No secrets in code, logs, commits, examples, screenshots, or tests.
2. `.env` must be in `.gitignore`.
3. Use `.env.example` with placeholder variable names only.
4. Ask before sending local file contents to a cloud provider.
5. Ask before running shell commands.
6. Ask before editing files.
7. Ask before sending emails.
8. Ask before creating/modifying/deleting calendar events.
9. Ask before opening external URLs if the URL was not directly requested.
10. Maintain an audit log of tool requests and user approvals once tools exist.

## Permission model

Every tool call should be classified:

- `safe_read`: read approved local config or internal state.
- `sensitive_read`: read user files, emails, calendar, browser data, or credentials-adjacent content.
- `write`: create or modify files, notes, calendar entries, emails, settings.
- `destructive`: delete files, move items, overwrite files, clear memory.
- `external_send`: send data to cloud providers, email recipients, web services, or APIs.
- `execute`: run shell commands, launch apps, or execute code.

Rules:

- `safe_read`: allowed after app setup.
- `sensitive_read`: ask unless folder/source is explicitly approved.
- `write`: ask.
- `destructive`: ask with a high-friction confirmation.
- `external_send`: ask and summarize what will be sent.
- `execute`: ask every time.

## Memory requirements

Memory is on by default, but raw conversations are not stored by default.

Store:

- durable user preferences;
- assistant settings;
- project summaries;
- task summaries;
- approved folders;
- tool approvals/audit metadata.

Do not store by default:

- raw transcripts;
- full local file contents;
- secrets;
- health, legal, financial, or sensitive personal details unless The Speaker explicitly requests it;
- third-party private data.

Required commands:

- "Atticus, remember that ..."
- "Atticus, forget that ..."
- "Atticus, what do you remember about ...?"
- "Atticus, clear memory about ..."

## Persona requirements

Atticus must be distinct and memorable, but useful first.

Voice:

- Southern gentleman.
- Warm, old-soul, literate, practical.
- Loyal to The Speaker.
- Full character is allowed.
- Avoid corny caricature.
- Avoid racism, classism, sexism, and exclusionary language.
- Never pretend to be human.
- Never claim actions were taken unless actually executed.

Example tone:

> Of course, Speaker. I’ve taken a good look at the matter, and here’s the sensible path forward.

## Testing requirements

For any meaningful code change, add or update tests. At minimum, test:

- config loading;
- missing API key handling;
- provider routing;
- persona prompt loading;
- memory write/read/forget;
- permission gates;
- tool denial behavior;
- CLI smoke test.

Prefer deterministic tests with mocked providers. Never call paid APIs in automated tests.

## Coding standards

- Use type hints.
- Keep modules small.
- Prefer simple architecture over clever abstractions.
- Add docstrings for public classes/functions.
- Use structured internal errors.
- Avoid hard-coded absolute paths except in docs/examples.
- Make Windows paths work.
- Do not make risky assumptions about file permissions.
- Do not silently fail.
- Keep logs useful but privacy-preserving.

## Git hygiene

The repo must include:

- `.gitignore`
- `.env.example`
- `README.md`
- `AGENTS.md`
- `SPEC.md`
- `docs/` (including `PORTFOLIO_ALIGNMENT.md`, `SHARED_ENGINEERING_STANDARD.md`)
- `.cursor/rules/`

Before completing a task, the coding agent should report:

1. Files changed.
2. Tests run.
3. Known limitations.
4. Security/privacy impact.
5. Suggested next task.

## Current implementation status (do not greenfield)

Track A Phase 1–6 foundations are already implemented in `atticus/` (CLI, config, persona, OpenAI provider, Claude/Gemini stubs, SQLite memory, approvals, optional voice, file/git/GitHub MVP tools). See `README.md` and `docs/PORTFOLIO_ALIGNMENT.md`.

New agents should extend the existing package. Typical next Track A work includes real Anthropic/Gemini providers, Gmail/Calendar OAuth behind confirmations, deeper coding tools, or desktop wiring — only when requested.

Track B work starts only when The Speaker asks for a specific SPEC milestone (usually M0). Do not invent a parallel `src/` tree or claim M0–M5 complete.
