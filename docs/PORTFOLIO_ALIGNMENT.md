# Portfolio alignment — Track A ↔ Track B

Honest map between the shipped personal assistant and the portfolio SPEC.

## Track definitions

### Track A — Current product (shipped)

Windows-first local assistant under `atticus/`: Rich CLI, persona, providers,
SQLite memory, permissioned tools, voice, tray/desk, and retro `/ui` GUI chat.

### Track B — Portfolio north star (local M0–M5 slices shipped)

Agent-platform capabilities from root `SPEC.md`, evolved inside `atticus/`
(not a silent greenfield rewrite). Shared-standard stack defaults are met with
documented deviations (ADR-009, ADR-015, ADR-016).

## Topic reconciliation

| Topic | Track A | Track B | Notes |
|-------|---------|---------|-------|
| Runtime | CLI + optional API/UI | FastAPI `/v1` + Compose | One repo |
| Store | SQLite | SQLite default; Postgres in Compose | ADR-015 |
| UI | Retro `/ui` + tray | Next.js `web/` + retro | ADR-016 |
| Policy | y/N gates + M3 API | Deterministic policy + approvals | ADR-013–014 |
| Traces | Telemetry hooks | Trace store + replay | ADR-017 |
| Evals | pytest | `evals/` + signature demo | ADR-018 |
| Roadmap | Phases 0–9 | Milestones M0–M5 | Both published |

## Milestone checklist (Track B)

| Milestone | Exit criteria (SPEC) | Status | Evidence |
|-----------|----------------------|--------|----------|
| M0 | Skeleton, typed config, API health, CI, telemetry | Done (local) | `atticus-api`, CI, OTel-shaped exporter |
| M1 | Conversation, provider, persisted bounded run | Done (local) | `/v1/conversations`, `/v1/runs` |
| M2 | Read-only file/search + citations | Done (local) | `atticus.citation.v1`, `/v1/citations` |
| M3 | Policy engine, write tool, approvals, audit | Done (local) | `/v1/policy`, approvals, dispatch |
| M4 | Memory controls, sandbox, replay, trace viewer | Done (local) | `/v1/traces`, replay, sandbox, memory API, `/ui` trace panel |
| M5 | Adversarial evals, routing, demo, deploy docs | Done (local) | `evals/`, fallback routing, signature demo, `docs/DEPLOYMENT.md` |

## Signature demo

Implemented with synthetic fixtures:

1. Research three RAG-evaluation approaches (fixtures)
2. Save cited findings
3. Create comparison table
4. Draft a GitHub issue
5. Stop for approval before publishing
6. Emit trace + quality report

```powershell
python scripts/run_signature_demo.py
```

## Remaining / do not over-claim

- Live Azure apply / shared hosted environment
- Full OTLP collector pipeline (file/stderr exporter exists)
- Postgres as default app store (Compose service only today)
- Exhaustive MCP tool marketplace (explicitly out of SPEC MVP scope)
- Native desktop full-window chat (retro `/ui` covers GUI chat)

## Compatible seams

- `atticus/api/`, `atticus/runs/`, `atticus/policy/`, `atticus/traces/`,
  `atticus/sandbox/`, `atticus/evals/`, `atticus/demo/`, `web/`, `infra/`

## Agent rules for this file

Update this crosswalk whenever milestone status changes. Prefer evolving
`atticus/` seams. Never claim paid API calls in CI.
