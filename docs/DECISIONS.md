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

## ADR-011 — Track B M1 bounded runs on local SQLite

Decision: add a FastAPI-independent run domain (`atticus/runs/`) with SQLite persistence and a bounded orchestrator, exposed under `/v1/conversations` and `/v1/runs`, reusing provider adapters (including `mock` for tests).

Includes in this slice:

- Conversation + message persistence
- Bounded run state machine: `queued` → `running` → `succeeded` | `failed` | `cancelled`
- Persisted checkpoints and cooperative cancel
- `Idempotency-Key` for create-message / create-run
- Provider injection via factory (Track A `ProviderRouter` by default; tests inject `MockProvider`)
- Runs DB path in `api.runs_sqlite_path` (default `data/atticus_runs.sqlite3`)

Reason: SPEC M1 requires a single conversation, provider adapter, and persisted bounded run with cancel/failure semantics. Keeping the domain free of FastAPI preserves the shared engineering rule that domain logic must not depend on web frameworks.

Implications:

1. Track A CLI remains the primary interactive product; the API is optional (`.[api]`).
2. Run transcripts are stored locally in the runs DB — not copied into Track A memory summaries by default.
3. Approvals, traces, sandbox, and Postgres remain later milestones.
4. Live provider calls from the API require real credentials; CI uses `mock` only.
5. Update portfolio alignment when claiming further M1/M2 progress.

## ADR-012 — Retro terminal UI + unified citation provenance (M2 slice)

Decision: ship a local same-origin retro CRT/terminal web UI under `/ui` from `atticus-api`, and unify read-tool provenance into `atticus.citation.v1` JSON records in the existing `data/citations` directory.

Includes:

- Phosphor-green terminal UI (computer default on `127.0.0.1`; phone via explicit `--lan`)
- Structured citations for `/browse`, `/file read`, and `/code-search`
- CLI `/citations list|show <id>` and API `GET /v1/citations[/{id}]`
- Legacy browse JSON normalized on read

Reason: Boss asked for a terminal/hacker interface usable on computer or phone, and Track B M2 requires structured citations/provenance. Evolving the browse citation store avoids a parallel provenance system.

Implications:

1. UI defaults to enabled but still bound to `api.host` (loopback unless `--lan`).
2. No public internet exposure and no auth token yet — LAN mode is trusted-network only.
3. Approvals/traces/sandbox remain later milestones.
4. Citation artifacts may include local file paths; treat the citations directory as sensitive.

## ADR-013 — Deterministic policy decisions and token-gated approvals (M3 slice)

Decision: add a framework-independent `atticus/policy/` domain with deterministic
policy evaluation, immutable action digests, durable approval requests, and an
append-oriented audit log. Expose it through `/v1/policy`, `/v1/approvals`, and
`/v1/audit/policy`.

Security controls:

- Models never decide permissions; `PolicyEngine` uses deterministic rules.
- Every exact action receives a SHA-256 digest.
- Approval decisions require both:
  - `X-Atticus-Approval-Token` resolved from `ATTICUS_APPROVAL_TOKEN` (or the
    configured environment/keyring name), and
  - an exact phrase: `APPROVE <digest-prefix>` or `DENY <digest-prefix>`.
- Tokens are never persisted or logged.
- Approval requests expire and terminal decisions cannot be replayed.
- Execution outcome is recorded separately after approval.

Reason: Track B M3 requires first-class policy decisions, approval workflow, and
audit metadata. The legacy Track A y/N gates remain in place; this slice creates
the stronger platform boundary without weakening existing confirmations.

Implications:

1. API approval decisions are disabled (HTTP 503) until the token is configured.
2. The retro UI displays pending requests and prompts for exact phrase + token;
   it does not store the token.
3. Policy/audit SQLite defaults to `data/atticus_approvals.sqlite3`.
4. Tool execution after approval is handled by ADR-014 (idempotent gateway).

## ADR-014 — Idempotent approved-tool dispatch gateway

Decision: add `atticus/policy/dispatch.ToolGateway` and
`POST /v1/approvals/{id}/execute` so only previously approved actions can run,
and repeated calls with the same `Idempotency-Key` return the original result.

Includes:

- Persist exact approved intent (`inputs`, `resource`, flags) on approval rows
- Recompute/verify action digest before execution
- SQLite `idempotency_records` ledger keyed by `Idempotency-Key`
- Initial handlers: `local_echo` (safe fixture) and `file_write` (approved paths)
- Terminal UI EXECUTE for approved requests with prompted idempotency key

Reason: SPEC requires approved mutating tool calls to be idempotent and forbids
execution without an allow/approval decision. This closes the M3 execution
bridge without inventing a parallel tool system.

Implications:

1. Execute requires approval token + `Idempotency-Key`.
2. Only registered handlers are dispatchable; unknown tools return
   `tool_not_dispatchable`.
3. Replay never re-runs side effects for the same key.
4. Broader tool coverage (gmail/calendar/git) remains incremental.
5. Next major Track B step is M4 traces/replay.

## ADR-015 — SQLite default with optional Compose Postgres/Redis

Decision: keep SQLite as the default durable store for runs, approvals, traces,
and memory on Track A/B local installs. Provide `docker-compose.yml` with
Postgres 16 + Redis 7 for shared-standard parity and future store backends.
Do not silently migrate production data paths to Postgres in this epic.

Reason: Boss's Windows laptop and privacy-first local use remain primary.
Portfolio reviewers can still bring up the standard dependency stack via Compose.

Implications:

1. API readiness continues to check SQLite paths unless a future ADR flips the default.
2. Postgres/Redis in Compose are available but unused by the default app wiring.
3. A later ADR may introduce repository interfaces + migrations for Postgres.

## ADR-016 — Dual UI: retro `/ui` + Next.js `web/`

Decision: keep the phosphor FastAPI `/ui` as the primary local operator terminal
(Track A GUI chat/approvals/settings/traces/demo). Add a minimal Next.js app
under `web/` for SHARED_ENGINEERING_STANDARD production-UI parity and Compose.

Reason: Track A character UX already lives in the retro terminal; a greenfield
Next rewrite would delay SPEC acceptance. Both surfaces call the same `/v1` API.

Implications:

1. Retro UI remains the fastest three-minute demo path (`atticus-api` → `/ui`).
2. Next.js is built in CI container job; local `npm run dev` is optional.
3. CORS allows `localhost:3000` → API for the web console.

## ADR-017 — M4 traces, replay, and sandbox

Decision: add `atticus/traces/` (SQLite spans), `GET /v1/traces/{run_id}`,
`GET /v1/runs/{run_id}/replay`, and `atticus/sandbox/` with
`POST /v1/sandbox/execute` (Python AST-gated child process; shell opt-in).

Reason: SPEC M4 requires inspectable plans/tools/approvals/artifacts plus
sandboxed execution. Spans attach to bounded runs and the signature demo.

Implications:

1. Trace DB defaults to `data/atticus_traces.sqlite3`.
2. Sandbox denies network-capable imports; shell metacharacters blocked.
3. Replay is reconstructive (checkpoints + spans), not a re-execution engine.

## ADR-018 — M5 evals, routing fallback, signature demo, deploy docs

Decision: ship versioned `evals/` suites, `scripts/run_evals.py`,
`/v1/evals/run`, automatic provider fallback with recorded decisions,
`atticus/demo/signature.py` + `/v1/demo/signature`, OTel-shaped file/stderr
exporter, API token + rate-limit middleware, Azure Terraform sketches, and
`docs/DEPLOYMENT.md`.

Reason: SPEC M5 and the shared-standard definition of done require measurable
quality, routing transparency, a signature demo, and deploy documentation.

Implications:

1. Signature demo uses synthetic fixtures and always stops for approval.
2. CI runs pytest + eval smoke + signature demo smoke + container builds.
3. Full managed OTLP collector / live Azure apply remain operator follow-ups.
