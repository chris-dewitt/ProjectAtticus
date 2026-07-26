# Atticus — Secure Local-First AI Agent Platform

Status: Portfolio architecture north star (Track B)  
Version: 1.0  
Audience: maintainers, coding agents, reviewers, and portfolio visitors

## Dual-track status (read this first)

This repository ships a working **Track A** personal assistant today:

- Package code lives under `atticus/` (Rich CLI, persona, OpenAI provider, SQLite memory, permissioned tools, optional voice).
- Package version and CLI entrypoints describe that product; see `README.md` and `docs/PORTFOLIO_ALIGNMENT.md`.

This `SPEC.md` defines **Track B**: the portfolio agent-platform architecture (policy engine, bounded orchestrator, API/traces/evals). Local M0–M5 vertical slices now ship under `atticus/` (see `docs/PORTFOLIO_ALIGNMENT.md` and ADR-010–018). That is **not** a claim of a live Azure/Postgres-default production deployment — Compose/Next/Terraform/OTel file export cover the shared-standard bar with documented deviations.

When documents conflict:

1. Track A behavior and privacy gates win for anything that already runs in `atticus/`.
2. This SPEC wins for future platform design unless an ADR explicitly defers or alters a requirement.
3. Always read `docs/PORTFOLIO_ALIGNMENT.md` for the honest capability map.

## 1. Product vision

A trustworthy agent platform that can research, reason, and use computer or knowledge-work tools while keeping users in control of sensitive actions.

## 2. Target users

Developers, technical knowledge workers, and security-conscious power users who need an auditable assistant across local and external systems.

Track A additionally serves a single primary operator ("Boss") on a Windows laptop with a full-character Southern gentleman persona. Persona and Windows-first UX remain non-negotiable on Track A (see ADR-009).

## 3. Product principles

- Evidence and traceability before fluency
- Deterministic computation for authoritative results
- Least privilege and explicit approval for consequential actions
- Bounded, inspectable workflows rather than opaque autonomous loops
- Reproducible runs, versioned inputs, and measurable quality
- Public, synthetic, or properly licensed data only

## 4. MVP scope

### In scope

- Text chat API and web interface; voice is optional after MVP
- Typed tool registry with read/write capability labels
- Explicit policy evaluation and approval gates
- Session memory and user-controlled durable memory
- File and document analysis with provenance
- Sandboxed Python and command execution
- GitHub issue drafting with approval before publishing
- Trace viewer, audit log, replay, and evaluation hooks
- Hosted/local model routing through provider adapters

### Explicitly out of scope

- General autonomous desktop control in MVP
- Silent background actions
- Unreviewed financial, medical, or legal decisions
- Credential management beyond integration with an external secret store
- A marketplace for third-party tools

## 5. System architecture

```text
Client / CLI
     |
Typed API and identity boundary
     |
Application workflow / state machine
     |
+----------------+----------------+----------------+
| Domain services| AI adapters    | Policy/eval    |
+----------------+----------------+----------------+
     |                 |                 |
Postgres/artifacts  Model providers  Traces/metrics
```

### Major components

- API and UI: conversations, plans, approvals, traces
- Orchestrator: bounded state machine with persisted checkpoints
- Policy engine: identity, capability, resource, risk, and approval decision
- Tool gateway: schema validation, timeouts, idempotency, and normalized errors
- Memory service: scoped writes, provenance, retention, and deletion
- Execution sandbox: isolated workspace, resource limits, and network policy
- Model router: explicit provider/model policy, fallback, and usage accounting
- Evaluation adapter: exports cases and traces to EvalForge

Domain code must remain independent of FastAPI, provider SDKs, and deployment infrastructure. All long-running workflows persist checkpoints and expose cancellation and terminal failure.

## 6. Core data model

- Conversation, message, plan, step, and artifact
- ToolDefinition, ToolInvocation, and ToolResult
- PolicyDecision and ApprovalRequest
- MemoryRecord with scope, source, sensitivity, and retention
- TraceSpan and AuditEvent
- IdempotencyRecord

All entities use stable identifiers and timestamps. Versioned records are immutable; corrections create a new version. Source-derived records retain source URI, retrieval time, content checksum, license/usage notes, and parser version.

## 7. API contract

Initial resource families:

- POST /v1/conversations and /messages
- GET /v1/runs/{id}; POST /v1/runs/{id}/cancel
- GET/POST /v1/approvals with approve or deny decision
- GET /v1/tools and /v1/traces/{run_id}
- GET/DELETE /v1/memories with explicit scope

APIs use versioned routes, Pydantic request/response schemas, idempotency keys for mutating operations, pagination for collections, and structured errors containing code, message, correlation ID, and safe details.

## 8. AI and workflow design

The workflow is an explicit state machine: validate request, assemble context, plan bounded work, execute typed operations, verify outputs, request approval when required, and finalize artifacts. Each transition is traceable. Model output is parsed against schemas and may not alter permissions, bypass deterministic validation, or invent unavailable evidence.

Provider adapters expose capabilities, context limits, structured-output support, usage, latency, and normalized failure modes. Fallback is allowed only by configured policy and is recorded in the run.

## 9. Security and privacy

- Classify inputs, outputs, tools, and stored artifacts by sensitivity.
- Keep secrets in an external secret mechanism and redact telemetry.
- Reject unsupported file types, unsafe paths, private-network URLs, and oversized payloads.
- Treat retrieved content as data, not instructions.
- Require an authenticated, scoped policy decision before external writes.
- Store approval actor, decision, exact action digest, expiry, and execution result.
- Document retention/deletion behavior and provide fixture data containing no confidential information.

## 10. Evaluation plan

Primary metrics:

- End-to-end task completion
- Correct tool selection and argument validity
- Permission violations and approval bypasses
- Recovery from injected, failed, or timed-out tools
- Unnecessary steps and human intervention rate
- p50/p95 latency, tokens, and estimated cost

Maintain a versioned golden set plus adversarial, malformed, timeout, empty-result, contradictory-evidence, and dependency-failure cases. Report per-case outputs as well as aggregates. CI runs a deterministic smoke suite; scheduled evaluation runs cover models and external integrations.

## 11. Testing strategy

- Unit tests for domain rules, validation, policies, and calculations
- Contract tests for providers, tools, stores, and source adapters
- Integration tests against disposable Postgres/Redis/object storage
- Golden tests for stable transformations and reports
- End-to-end tests for the signature workflow
- Security tests for injection, authorization, path/URL handling, redaction, and replay
- Property tests for invariants and numerical or temporal boundaries where applicable

## 12. Observability and operations

Emit structured logs, distributed traces, and metrics keyed by correlation and run IDs. Track state-transition duration, dependency errors, retries, model and token usage, cost, evaluation scores, and project-specific quality. Jobs use bounded exponential backoff, dead-letter/quarantine behavior, and operator-visible recovery instructions.

## 13. Milestones

- M0: repository skeleton, typed config, API health, CI, telemetry
- M1: single conversation, provider adapter, persisted bounded run
- M2: read-only file/search tools and structured citations
- M3: policy engine, write tool, approval workflow, audit events
- M4: memory controls, sandbox, replay, trace viewer
- M5: adversarial evals, model routing, demo, deployment documentation

Each milestone must ship a demonstrable vertical slice with tests, evaluation cases, telemetry, and documentation. Deferred scope becomes tracked issues rather than hidden TODOs.

Track A already covers portions of M1–M3 intent via the CLI (see `docs/PORTFOLIO_ALIGNMENT.md`). That does **not** mean Track B M0–M5 are complete.

## 14. Signature demonstration

Research three current RAG-evaluation approaches, save cited findings, create a comparison table, and draft a GitHub issue. The run must stop for approval before publishing.

The demo must run from documented commands with public or synthetic fixtures, show a trace and quality report, and complete in approximately three minutes after setup.

## 15. MVP acceptance criteria

- No write-capable tool executes without an allow decision and required approval
- Repeated approved requests are idempotent
- Prompt-injected documents cannot grant capabilities
- A failed tool produces a bounded recovery or explicit terminal failure
- A user can inspect the exact plan, tool inputs, results, approvals, and final artifacts
- The signature demo passes a versioned regression suite

Additionally, all applicable requirements in `docs/SHARED_ENGINEERING_STANDARD.md` must pass.

## 16. Repository layout

Target portfolio layout (Track B; not fully adopted yet):

```text
README.md
SPEC.md
AGENTS.md
ARCHITECTURE.md
SECURITY.md
EVALUATION.md
MODEL_CARD.md
DATA_CARD.md
CHANGELOG.md
docs/adr/
src/
tests/
evals/
examples/
scripts/
infra/
```

Current Track A layout remains authoritative for implementation:

```text
atticus/
config/
prompts/
docs/
tests/
.cursor/rules/
```

Do not relocate `atticus/` to `src/` without an ADR and an explicit migration task.

## 17. Initial agent work order (Track B)

1. Verify repository identity and read all source-of-truth documents (including `docs/PORTFOLIO_ALIGNMENT.md`).
2. Do not re-scaffold Phase 1 CLI; Track A already exists.
3. When asked to advance Track B, create the smallest M0 vertical slice using the shared standard, with tests and docs in the same change.
4. Define domain schemas and interfaces before external integrations.
5. Expand CI toward the shared standard (formatting, linting, typing, security, container) via incremental ADRs.
6. Implement one representative end-to-end fixture for the active milestone.
7. Record assumptions and deferred decisions in ADRs and issues.

Do not begin later Track B milestones until the active milestone's acceptance evidence is recorded, unless Boss explicitly requests otherwise.
