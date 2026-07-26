# Agent Handoff — ProjectAtticus

## What we are building

**Track A (shipped):** A Windows-first, local-first personal assistant named Atticus. He is a full-character Southern gentleman advisor who responds to Boss, uses OpenAI by default, supports Claude/Gemini later, remembers summaries/preferences, speaks/listens through optional local voice components, and runs permissioned local tools when enabled.

**Track B (in progress):** A secure local-first agent platform (policy, bounded runs, traces, evals) defined in root `SPEC.md`. M0 health API + M1 bounded runs exist (`atticus/api/`, `atticus/runs/`, ADR-010/011); approvals/traces/evals are not shipped. See `docs/PORTFOLIO_ALIGNMENT.md`.

## Required reading order

1. `AGENTS.md`
2. `SPEC.md`
3. `docs/SHARED_ENGINEERING_STANDARD.md`
4. `docs/PORTFOLIO_ALIGNMENT.md`
5. Existing architecture, security, evaluation, persona, and implementation files under `docs/` and `atticus/`

## What matters most

1. Privacy.
2. Modularity.
3. Working CLI foundation (already present — extend it).
4. Provider abstraction.
5. Atticus persona (Track A).
6. Permission-gated actions and auditability.
7. Tests.
8. Honest status language (do not claim Track B milestones as done).

## What not to do first

Do not start with:

- re-scaffolding Phase 1 as if the repo were empty;
- a Track B Postgres/Next.js rewrite unless Boss asks for that milestone;
- ambient always-listening wake word beyond the existing two-clip flow;
- unrestricted shell execution;
- silent Gmail/calendar writes without confirmation;
- unrestricted file access;
- raw transcript storage;
- silent model/provider fallback.

## Best next work (choose by request)

Track A extensions (typical):

- richer desktop wiring into the same gates;
- JS-heavy browser automation (still open);
- full GUI chat (still open).

Track B (only if Boss names a milestone):

- M0 remainders: broader CI (lint/type/security), optional OTel exporter ADR;
- M1 remainders: async run workers, provider capability metadata;
- **M2 preferred next:** structured citations/provenance for read tools;
- evolve existing seams in `atticus/` rather than inventing a parallel tree.

## Completion report format

When an agent completes work, report:

```text
Summary:
- ...

Files changed:
- ...

Tests run:
- ...

Security/privacy notes:
- ...

Known limitations:
- ...

Track impact (A/B):
- ...

Recommended next step:
- ...
```
