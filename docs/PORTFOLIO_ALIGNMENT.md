# Portfolio Alignment — Dual-Track Crosswalk

Status: Source of truth for reconciling Track A (shipped product) with Track B (`SPEC.md`)  
Audience: maintainers, coding agents, portfolio reviewers

## Track definitions

### Track A — Current product (shipped)

Windows-first, local-first personal assistant named Atticus:

- Rich CLI chat (`atticus` / `python -m atticus`)
- Southern gentleman persona; addresses user as Boss
- OpenAI live provider; Claude/Gemini stubs; router skeleton
- SQLite memory (notes, preferences, summaries, tool audit)
- Permission classes + console y/N approvals
- Optional TTS (pyttsx3), PTT/wake via local Vosk
- Opt-in tools: approved-path files, allow-listed git, GitHub REST, URL open
- Thin Textual desk companion

Package version `1.0.0` refers to this Track A milestone labeling, **not** completion of Track B M0–M5.

### Track B — Portfolio north star (planned)

Secure local-first AI agent platform per root `SPEC.md`:

- Typed API, web UI, bounded orchestrator, policy engine
- Postgres/artifacts, traces, replay, EvalForge hooks
- Signature demo: research → comparison table → draft GitHub issue with approval gate
- Shared engineering standard stack defaults (FastAPI, Postgres, Next.js, Docker, OTel, Azure)

Track B is **not started as a platform rewrite**. Do not present FastAPI, Postgres, Next.js, sandbox execution, idempotency records, or trace viewers as shipped.

## Topic reconciliation

| Topic | Track A (today) | Track B (SPEC) | Reconciliation |
|-------|-----------------|----------------|----------------|
| Product identity | Personal Windows assistant | Secure agent platform | Both: UX/persona stays Track A; platform architecture is Track B |
| Status | Package v1.0 with working CLI | Spec complete; start at M0 | Shipped = Track A; Track B planned |
| UI | CLI + thin Textual desk | Text API + web UI | CLI remains primary until an explicit Track B UI milestone |
| Stack | Python 3.11+, SQLite, YAML, Rich | Python 3.12, FastAPI, Postgres, Next.js, Docker, OTel, Azure | Deviations allowed until ADRs adopt stack pieces |
| Layout | `atticus/`, `docs/`, `prompts/` | `src/`, `evals/`, `infra/`, top-level cards | Keep current layout; portfolio docs added; no silent `src/` move |
| Demo | Persona chat | Research → GitHub issue with approval | Chat is current demo; SPEC signature demo is Track B acceptance target |
| Roadmap | Phases 0–9 | Milestones M0–M5 | Both published; this file is the crosswalk |
| Source of truth | AGENTS, PRD, ROADMAP for Track A | SPEC + SHARED_ENGINEERING_STANDARD for Track B | Reading order in `AGENTS.md` |

## Phase 0–9 → Milestone M0–M5 map

| Track A phase | Status (approx.) | Related Track B intent | Gap vs SPEC |
|---------------|------------------|------------------------|-------------|
| Phase 0 repo foundation | Complete | M0 docs/CI skeleton | Missing full CI bar (lint/type/security/container), OTel exporter |
| Phase 1 CLI + OpenAI | Complete | M1 conversation + provider | No persisted bounded run API |
| Phase 2 memory + approvals | Complete | M3/M4 memory + audit | No policy engine object model; no approval API; no retention metadata |
| Phase 3 TTS | Complete (optional) | Out of Track B MVP (voice after MVP) | N/A |
| Phase 4–5 PTT/wake | Complete (optional extras) | Out of Track B MVP | Ambient continuous wake not implemented |
| Phase 6 file tools | MVP complete | M2 read tools + citations | Provenance/citation model incomplete; no structured citation artifacts |
| Phase 7 coding/git | Partial | M2/M3 tools | Patch/test allowlists exist; sandbox still open |
| Phase 8 integrations | Partial | M3 external writes | Gmail/Calendar/browse exist; no issue-draft publish flow |
| Phase 9 desktop | Partial | Track B web UI later | Tray/autostart exist; full GUI chat still open |

### Milestone checklist (Track B)

| Milestone | Exit criteria (SPEC) | Already covered by Track A? | Still needed |
|-----------|----------------------|-----------------------------|--------------|
| M0 | Skeleton, typed config, API health, CI, telemetry | Partial + M0 health slice (`atticus-api`, structured errors, telemetry hooks) | Broader CI (lint/type/security), OTel exporter |
| M1 | Conversation, provider, persisted bounded run | Partial + `/v1` conversations/runs (SQLite, checkpoints, cancel, idempotency) | Async workers, richer provider capability metadata |
| M2 | Read-only file/search + citations | Partial + `atticus.citation.v1` + `/v1/citations` + retro `/ui` | Richer locators, run linkage, read-tool HTTP execute APIs |
| M3 | Policy engine, write tool, approvals, audit | Partial (permission classes, y/N, audit table, file write) | First-class policy decisions, approval API, idempotency |
| M4 | Memory controls, sandbox, replay, trace viewer | Partial (memory forget/prefs) | Sandbox, replay, trace viewer |
| M5 | Adversarial evals, routing, demo, deploy docs | Minimal (router skeleton, pytest) | EvalForge suite, real multi-provider routing, signature demo |

## Signature demo gap

SPEC signature demo:

1. Research three current RAG-evaluation approaches
2. Save cited findings
3. Create a comparison table
4. Draft a GitHub issue
5. Stop for approval before publishing
6. Show trace + quality report in ~three minutes

Track A today can support pieces (`/file`, memory notes, `/gh` read APIs, approvals) but **cannot** run the full bounded research→issue workflow with traces/evals. Treat the signature demo as Track B acceptance work.

## Explicit gaps (do not claim shipped)

Portfolio reviewers and agents must **not** claim these as done:

- Typed HTTP API for approvals/traces (health + conversations/runs/citations exist; approvals/traces still open)
- Production Next.js web UI (local retro terminal `/ui` exists; not Next.js)
- PostgreSQL / Redis / object storage / Docker Compose local stack
- Bounded orchestrator with persisted checkpoints and cancel
- Policy engine as a first-class decision object
- Execution sandbox with network policy
- Idempotency records for approved mutating tool calls
- Trace viewer / replay UI
- EvalForge integration, golden/adversarial eval suites, cost/latency baselines
- OpenTelemetry exporter / distributed tracing (hooks exist; no exporter yet)
- Terraform / Azure deployment
- Automatic multi-provider routing with recorded fallback

## Compatible overlaps (build on these)

When extending the repo toward Track B, prefer evolving these existing seams:

- `atticus/api/` — FastAPI factory, health/ready, `/v1` conversations/runs/citations, retro `/ui`
- `atticus/services/citations.py` — unified citation/provenance records
- `atticus/runs/` — FastAPI-independent run store + bounded orchestrator
- `atticus/core/telemetry.py` — correlation IDs + redacted event sink
- `atticus/core/errors.py` — structured `AtticusError` fields
- `atticus/providers/base.py` — LLM provider protocol
- `atticus/core/permissions.py` + `atticus/core/approvals.py` + `tool_approvals` audit table
- `atticus/core/tool_request.py` — tool call request shape
- `atticus/memory/store.py` — durable prefs/notes/summaries
- `atticus/services/*` + `workbench_commands.py` — file/git/GitHub tool surfaces
- `atticus/core/secrets.py` — env-first credential helper

## Agent rules for this file

1. Do not re-scaffold Phase 1 as if the repo were empty.
2. Do not start Track B M0–M5 unless Boss asks for that milestone.
3. When changing tools/approvals, bias toward SPEC-shaped boundaries: typed tools, audit events, no silent external writes, treat retrieved content as untrusted.
4. Update this crosswalk when a milestone slice ships.
