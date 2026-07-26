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

### Epic: finish Track A GUI + Track B M0–M5 platform bar

- M4: durable traces, replay reports, Python sandbox, memory/settings APIs
- M5: eval suites, provider fallback routing, signature demo, deploy docs
- Shared standard: Docker Compose, Next.js `web/`, OTel-shaped exporter,
  API token auth, rate limits, Terraform sketches, root contract docs
- Retro `/ui` chat + approvals + settings + traces + SIG DEMO
- ADR-014–018; CI eval/demo smoke + container builds

### Track B M3 idempotent dispatch

- `ToolGateway` executes only approved actions
- `POST /v1/approvals/{id}/execute` with required `Idempotency-Key`
- SQLite idempotency ledger; handlers for `local_echo` and `file_write`
- Retro UI EXECUTE for approved requests; ADR-014

### Track B M3 policy / approvals

- Deterministic `atticus/policy/` engine (allow/deny/require approval)
- Stable action digests, expiring durable approval requests, execution results
- Token + exact-phrase gated `/v1/approvals` decisions and policy audit
- Pending approval queue in the retro terminal UI; ADR-013

### Retro terminal UI + Track B M2 citations

- Local CRT/phosphor web terminal at `/ui/` (phone via `atticus-api --lan`)
- Unified `atticus.citation.v1` provenance for browse/file/code-search
- `GET /v1/citations`, CLI `/citations list|show`, ADR-012

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
