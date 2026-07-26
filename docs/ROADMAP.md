# Roadmap — ProjectAtticus

## Track A — Personal assistant phases

### Phase status summary

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Repo foundation | Done |
| 1 | CLI Atticus | Done |
| 2 | Memory + permissions | Done |
| 3 | Spoken responses | Done |
| 4 | Speech input | Done |
| 5 | Wake word | Done (local prototype) |
| 6 | Local file tools | Done (opt-in) |
| 7 | Coding assistant tools | Done (opt-in) |
| 8 | Integrations | Partial (Gmail/Calendar/GitHub) |
| 9 | Desktop/tray | Done (tray + status desk); full native GUI chat optional |

Retro `/ui` now provides browser GUI chat, approvals, settings, traces, and demo
controls for local/LAN use.

### Phase 0 — Repo foundation

Done.

### Phase 1 — CLI Atticus

Done.

### Phase 2 — Local memory and permission core

Done.

### Phase 3 — Spoken responses

Done.

### Phase 4 — Speech input

Done.

### Phase 5 — Wake word

Done (local prototype; push-to-talk fallback remains).

### Phase 6 — Local file tools

Done (opt-in, confirmation-gated).

### Phase 7 — Coding assistant tools

Done (git allowlist, patch/test helpers; confirmation-gated).

### Phase 8 — Integrations

Partial — GitHub/Gmail/Calendar/browse exist; broader MCP gateway still incremental.

### Phase 9 — Desktop/tray experience

Tray + autostart + Textual status desk shipped. Native full-window chat is optional;
primary GUI chat is the retro terminal at `/ui`.

## Track B — Portfolio milestones (SPEC)

| Milestone | Goal | Exit criteria (summary) | Status |
|-----------|------|-------------------------|--------|
| M0 | Repo/platform skeleton | Typed config, API health/readiness, CI/telemetry baseline | **Done (local)** — health/ready, structured errors, telemetry + OTel-shaped exporter, CI eval/container jobs (ADR-010, ADR-018) |
| M1 | Conversation + provider + bounded run | Persisted run with cancel/failure semantics | **Done (local)** — `/v1/conversations` + `/v1/runs` + checkpoints/cancel/idempotency (ADR-011) |
| M2 | Read tools + citations | File/search tools with structured provenance | **Done (local)** — `atticus.citation.v1` + `/v1/citations` + retro `/ui` (ADR-012) |
| M3 | Policy + write + approvals + audit | First-class policy decisions and approval workflow | **Done (local)** — policy engine, token-gated approvals, idempotent dispatch (ADR-013–014) |
| M4 | Memory controls + sandbox + replay + traces | Inspectable plans/tools/approvals/artifacts | **Done (local)** — traces/replay/sandbox/memory APIs (ADR-017) |
| M5 | Evals + routing + demo + deploy docs | Signature demo + adversarial/golden evals | **Done (local)** — evals, fallback routing, signature demo, deploy/Compose/Terraform (ADR-018) |

### Signature demo (Track B acceptance target)

Research three current RAG-evaluation approaches, save cited findings, create a
comparison table, draft a GitHub issue, and stop for approval before publishing —
with trace and quality report.

```powershell
python scripts/run_signature_demo.py
# or POST /v1/demo/signature / SIG DEMO in /ui
```

### Recommended next work

- Broader gateway handlers (gmail/calendar/git publish)
- Optional Postgres repository backend behind the same interfaces
- Managed OTLP collector wiring
- Live Azure environment from `infra/terraform` when Boss wants hosting
