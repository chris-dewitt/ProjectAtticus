# Agent Handoff — ProjectAtticus

## What we are building

**Track A (shipped):** A Windows-first, local-first personal assistant named Atticus. He is a full-character Southern gentleman advisor who responds to Boss, uses OpenAI by default, supports Claude/Gemini, remembers summaries/preferences, speaks/listens through optional local voice components, runs permissioned local tools when enabled, and offers retro `/ui` GUI chat plus tray/desk.

**Track B (local M0–M5 slices shipped):** A secure local-first agent platform (policy, bounded runs, traces, evals, sandbox, signature demo) defined in root `SPEC.md`, evolved under `atticus/`. See ADR-010–018 and `docs/PORTFOLIO_ALIGNMENT.md`.

## Required reading order

1. `AGENTS.md`
2. `SPEC.md`
3. `docs/SHARED_ENGINEERING_STANDARD.md`
4. `docs/PORTFOLIO_ALIGNMENT.md`
5. `docs/DEPLOYMENT.md`
6. Existing architecture, security, evaluation, persona, and implementation files under `docs/` and `atticus/`

## What matters most

1. Privacy.
2. Modularity.
3. Working CLI foundation (already present — extend it).
4. Provider abstraction.
5. Atticus persona (Track A).
6. Permission-gated actions and auditability.
7. Tests.
8. Honest status language (note local vs hosted limits).

## What not to do first

Do not start with:

- re-scaffolding Phase 1 as if the repo were empty;
- a silent `atticus/` → `src/` migration;
- ambient always-listening wake word beyond the existing two-clip flow;
- unrestricted shell execution;
- silent Gmail/calendar writes without confirmation;
- unrestricted file access;
- raw transcript storage;
- silent model/provider fallback without recording the decision.

## Best next work

- Broader idempotent gateway handlers (gmail/calendar/git publish)
- Optional Postgres repository backend behind existing store interfaces
- Managed OTLP collector / live Azure apply when Boss wants hosting
- Native desktop full-window chat polish (retro `/ui` already covers GUI chat)

## Completion report format

When an agent completes work, report:

1. Files changed
2. Tests run
3. Known limitations
4. Security/privacy impact
5. Suggested next task

## Quick verification

```powershell
pip install -e ".[dev,api]"
pytest -q
python scripts/run_evals.py --suite platform
python scripts/run_signature_demo.py
atticus-api
# open http://127.0.0.1:8000/ui/
```
