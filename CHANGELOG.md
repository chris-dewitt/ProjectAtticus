# Changelog — ProjectAtticus

All notable repository milestones. Dates follow merge history on `main`.

## 1.0.0 — 2026-05-10

Track A packaging milestone (personal assistant), not Track B M0–M5 completion.

- Portable example config, `atticus` CLI entrypoint, quick start, CI
- Authenticated GitHub CLI (`/gh me|repos|prs`) and secrets helper (env + optional keyring)
- Phases 6–9 MVP: file workspace tools, git allowlist, GitHub/open, integration stubs, Textual desk

## 0.5.0 — 2026-05-10

- Phase 4–5: push-to-talk + Vosk STT, two-clip wake flow, voice kill switch, privacy docs

## 0.4.0 — 2026-05-10

- Phase 3: pyttsx3 TTS, mute/unmute, voice status, Markdown strip for speech, tests

## 0.3.0 — 2026-05-09

- Phase 2: preferences, summaries, audit log, approvals, natural-language memory commands

## 0.2.0 — 2026-05-09

- Phase 1 CLI: providers, config, SQLite memory, slash commands, tests

## 0.1.0 — 2026-05-09

- Instruction pack at repo root (rules, docs, prompts, config)

## Unreleased

### Track B M1 slice

- Bounded run domain (`atticus/runs/`) with SQLite persistence and checkpoints
- `/v1/conversations`, `/v1/messages`, `/v1/runs`, cancel + `Idempotency-Key`
- Provider factory wiring (live providers or `mock` for tests); ADR-011

### Track B M0 slice

- Optional FastAPI health/readiness API (`pip install -e ".[api]"`, `atticus-api`)
- Structured `AtticusError` payloads and correlation-ID middleware
- Lightweight telemetry hooks with secret redaction (no OTel exporter yet)
- Typed `api` / `telemetry` config; ADR-010

### Documentation

- Dual-track reconciliation: `SPEC.md`, `docs/SHARED_ENGINEERING_STANDARD.md`, `docs/PORTFOLIO_ALIGNMENT.md`, evaluation/model/data cards, ADR-009
