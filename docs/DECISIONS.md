# Architecture Decision Record — ProjectAtticus

## ADR-001 — Windows first

Decision: build for Windows first.

Reason: Boss's target machine is a Windows Dell Inspiron.

Implication: setup docs and path handling must be Windows-friendly.

## ADR-002 — Python first

Decision: use Python for the first version.

Reason: fastest path to a working local assistant with CLI, APIs, SQLite, file tools, voice libraries, and tests.

Implication: desktop UI can come later.

## ADR-003 — CLI first

Decision: first working demo is CLI chat.

Reason: safest and fastest foundation. Avoids UI/audio complexity before the assistant brain works.

Implication: voice-first product vision remains, but implementation is phased.

## ADR-004 — OpenAI default provider

Decision: OpenAI is the default brain.

Reason: user preference.

Implication: Claude/Gemini are optional provider modules, not blockers.

## ADR-005 — Automatic provider routing later

Decision: design router immediately, but keep initial routing simple.

Reason: routing is an architectural concern, but complex routing is not needed for v0.1.

Implication: use OpenAI by default while preserving router hooks.

## ADR-006 — Memory on by default, summaries only

Decision: memory is on by default, but raw conversations are not saved by default.

Reason: user wants memory and privacy.

Implication: build summaries/preferences store first.

## ADR-007 — Permission gates required

Decision: all risky tools require confirmation.

Reason: Atticus will eventually act on the user's laptop.

Implication: no shell/file/email/calendar actions bypass permission gate.

## ADR-008 — Voice always eventually, not first code milestone

Decision: spoken responses are a near-term goal, but CLI text chat ships first.

Reason: older Windows laptop and audio dependencies introduce risk.

Implication: voice layer must be optional and failure-tolerant.

## ADR-009 — Dual-track product and portfolio architecture

Decision: maintain two coordinated tracks in one repository.

- **Track A (current product):** Windows-first personal assistant UX — Rich CLI, Boss/persona, SQLite memory, permission gates, optional voice, opt-in tools under `atticus/`. This is what ships and what package version `1.0.0` refers to.
- **Track B (portfolio north star):** Secure local-first agent platform described in root `SPEC.md` — bounded orchestrator, policy engine, API/traces/evals, EvalForge hooks, signature research→GitHub-issue demo.

Reason: the portfolio flagship needs auditable agent-platform architecture, while Boss still needs a working local assistant. Erasing either narrative would misrepresent status or throw away a working foundation.

Implications:

1. Track A privacy, approval, persona, and Windows-first rules remain non-negotiable for anything that already runs.
2. `docs/SHARED_ENGINEERING_STANDARD.md` stack defaults (FastAPI, Postgres, Next.js, Docker, OTel, Azure) are aspirational until a later ADR adopts each piece.
3. Current layout (`atticus/`, `docs/`, `prompts/`) stays until an explicit migration ADR; do not silently move to `src/`.
4. Agents must read `docs/PORTFOLIO_ALIGNMENT.md` before claiming milestone completion.
5. Do not present Track B M0–M5 as fully shipped; claim only slices with acceptance evidence.

## ADR-010 — Track B M0 local health API without rewriting Track A

Decision: add an optional FastAPI health/readiness surface under `atticus/api/`, installed via `.[api]` and launched with `atticus-api`, while keeping the Rich CLI as the primary Track A product.

Includes in this slice:

- `GET /health/live` and `GET /health/ready` (plus `/ready` alias)
- structured `AtticusError` fields (`code`, `message`, `safe_details`, `status_code`)
- lightweight telemetry hooks (correlation ID, redacted in-process events; no OTel exporter yet)
- typed `api` and `telemetry` config blocks
- CI install of `.[dev,api]` so API tests run on Windows

Reason: SPEC M0 requires API health, typed config, and a telemetry baseline. A greenfield `src/` + Postgres rewrite would discard a working assistant. Evolving `atticus/` keeps privacy/approval rules intact.

Implications:

1. FastAPI/Uvicorn are optional dependencies, not required for Track A CLI.
2. API binds to `127.0.0.1` by default; OpenAPI docs off by default.
3. Conversations, runs, approvals, and traces remain future milestones (start with M1 bounded runs).
4. Broader shared-standard CI (ruff/mypy/security/container) and OTel export need later ADRs.
5. Update `docs/PORTFOLIO_ALIGNMENT.md` when claiming further M0/M1 progress.
