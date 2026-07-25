# Evaluation — ProjectAtticus

Status: Track A practice documented; Track B EvalForge suite planned  
Related: `SPEC.md` §10, `docs/SHARED_ENGINEERING_STANDARD.md` §8, `docs/PORTFOLIO_ALIGNMENT.md`

## Current practice (Track A)

- Automated tests: `pytest` under `tests/` with mocked providers.
- CI (`.github/workflows/ci.yml`): install `.[dev]` and run `pytest` on Windows for Python 3.11 and 3.12.
- Paid APIs are never called in automated tests.
- Coverage priorities today: config, router, persona, memory, approvals, permissions, tool gate, git allowlist, secrets helpers, voice/wake helpers.

There is **no** versioned golden agent-eval dataset, no cost/latency baseline table, and no EvalForge export yet. Do not claim measured end-to-end task quality beyond unit/integration pytest results.

## Planned direction (Track B)

From `SPEC.md` and the shared engineering standard:

- Versioned golden set plus adversarial, malformed, timeout, empty-result, and dependency-failure cases
- Metrics: task completion, tool selection validity, permission violations/approval bypasses, recovery behavior, human intervention rate, p50/p95 latency, tokens, estimated cost
- CI smoke suite for deterministic checks; scheduled runs for model/integration coverage
- Export/adapter hooks for EvalForge
- LLM-as-judge only as a supplement to deterministic graders

## How to run what exists

```powershell
pip install -e ".[dev]"
pytest -q
```

## Definition of done for evaluation work

An evaluation change is done only when fixtures, graders or assertions, documentation here, and CI wiring (when applicable) land together — not when a one-off demo succeeds.
