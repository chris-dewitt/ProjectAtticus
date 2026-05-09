# Codex Task Prompts — ProjectAtticus

Use these prompts with Codex after placing this instruction pack in the repo.

## Task 1 — Build Python scaffold and CLI

```text
Read AGENTS.md and the docs folder first. Then implement the Phase 1 CLI Atticus scaffold.

Requirements:
- Use Python.
- Create package `atticus`.
- Add `python -m atticus` entrypoint.
- Add CLI chat loop.
- Load config from `config/atticus.yaml` if present, otherwise defaults.
- Load env vars from environment and optional `.env`.
- Use OpenAI as default provider.
- Add provider abstraction with OpenAI provider plus Claude/Gemini stubs.
- Add canonical Atticus persona prompt.
- Add SQLite memory skeleton with remember/list/forget operations.
- Add `/help`, `/exit`, `/provider`, `/mode`, `/memory`, `/remember`, and `/forget` commands.
- Do not implement voice yet.
- Do not implement shell tools yet.
- Add tests with mocked providers.
- Update README with exact Windows setup steps.

Before finishing, run the tests and report files changed, tests run, privacy impact, and next recommended task.
```

## Task 2 — Add permission gate

```text
Implement the permission gate described in docs/SECURITY.md and docs/TOOLS.md.

Requirements:
- Add PermissionClass enum.
- Add ToolCallRequest and ToolCallResult models.
- Add PermissionGate that prompts the user for approval in CLI.
- Add audit logging to SQLite.
- Add tests showing shell/file/cloud actions are blocked without approval.
- Do not implement actual shell execution yet.
```

## Task 3 — Add spoken responses

```text
Add optional text-to-speech playback for Atticus responses on Windows.

Requirements:
- Add `atticus/voice/tts.py`.
- Use a simple offline Windows-compatible engine first.
- Spoken responses default to true in config, but app must continue if TTS fails.
- Add `--mute` CLI flag.
- Add tests that mock TTS.
- Update docs/VOICE.md if needed.
```

## Task 4 — Add local file search skeleton

```text
Add a permission-gated local file search tool scoped to approved paths.

Requirements:
- Default approved path: ProjectAtticus repo path from config.
- Allow listing/searching filenames under approved path.
- Do not send file contents to LLM without explicit approval.
- Add tests for approved path, denied path, and traversal protection.
```

## Task 5 — Add provider router logic

```text
Implement ProviderRouter with simple automatic routing.

Requirements:
- OpenAI remains default.
- Allow manual provider override.
- Add task-category based routing hooks for future Claude/Gemini support.
- Do not require Anthropic/Gemini keys to run the app.
- Add tests for default, manual override, missing provider key, and fallback behavior.
```

## Task 6 — Add wake-word planning issue/docs only

```text
Do not implement wake word yet. Create a detailed implementation plan for wake-word support on Windows using local-only detection. Include privacy UX, kill switch, status indicator, and fallback strategy.
```
