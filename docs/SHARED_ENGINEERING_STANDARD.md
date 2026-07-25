# Shared Engineering Standard

Status: Normative (portfolio bar)  
Applies to: Atticus, Atlas, EvalForge, FedLens, BalanceLab AI

## ProjectAtticus adoption note

ProjectAtticus meets this standard **incrementally**. Track A (shipped CLI assistant under `atticus/`) already satisfies several privacy, approval, and testing expectations. Full compliance with FastAPI/Postgres/Next.js/Docker/OTel/Terraform defaults requires Track B work and explicit ADRs (see `docs/PORTFOLIO_ALIGNMENT.md` and ADR-009 in `docs/DECISIONS.md`).

Deviations from the stack defaults below are allowed when documented in an ADR; they must not silently weaken security, evaluation, or reproducibility requirements.

## 1. Purpose

This document defines the minimum engineering bar for every repository in the portfolio. Project specifications may add stricter requirements but may not silently weaken these rules.

## 2. Required qualities

Every system must be reproducible, typed, testable, observable, secure by default, explicit about AI failure modes, and usable without privileged or confidential data. A reviewer must be able to determine what the system does, how it works, how quality is measured, and how to run it within five minutes of opening the repository.

## 3. Standard stack

- Python 3.12, FastAPI, Pydantic v2, pytest
- PostgreSQL with pgvector when vector retrieval is required
- Redis only when a queue, cache, or distributed coordination is justified
- Next.js and TypeScript for production user interfaces
- Docker Compose for local dependencies
- OpenTelemetry-compatible traces, structured JSON logs, and metrics
- GitHub Actions for linting, typing, tests, security scans, and evaluations
- Terraform for deployed cloud infrastructure
- Azure as the first deployment target; providers remain replaceable

Framework choices are defaults, not excuses. Any deviation must be documented in an ADR.

Current Track A deviations (documented in ADR-009): Python 3.11+ with Rich CLI, SQLite, YAML config, optional Textual desk, Windows-first local execution without Docker/Azure requirement.

## 4. Repository contract

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
docs/
src/
tests/
evals/
examples/
scripts/
infra/
```

The initial implementation may create empty directories incrementally, but the MVP is not complete until all applicable top-level documents contain useful content.

For ProjectAtticus, several contract documents live under `docs/` (`docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/EVALUATION.md`, `docs/MODEL_CARD.md`, `docs/DATA_CARD.md`) while implementation remains in `atticus/` rather than `src/`.

## 5. Application architecture

- Domain logic must not depend directly on web frameworks or model SDKs.
- Model providers, retrievers, stores, and external tools use typed interfaces.
- Important state transitions are explicit and persisted.
- Background jobs are retryable, idempotent, and observable.
- External calls have timeouts, bounded retries, and normalized errors.
- Configuration is typed and loaded from environment variables; secrets are never committed.
- Database changes use migrations.
- APIs publish stable schemas and return structured error bodies.

## 6. AI engineering rules

- Model output is untrusted input and must be parsed and validated.
- Models never perform authoritative arithmetic, authorization, or policy decisions.
- Prompts and evaluation datasets are versioned.
- Every generated claim that depends on a source retains provenance.
- Provider selection and fallback behavior are explicit and traceable.
- Model changes require evaluation against a pinned regression suite.
- Synthetic or LLM-generated evaluation data must be labeled.
- Human approval is required before consequential external writes.

## 7. Security baseline

- Maintain a threat model covering assets, trust boundaries, attackers, abuse cases, and mitigations.
- Separate read-only capabilities from write-capable capabilities.
- Apply least privilege to tools, identities, tokens, and network access.
- Redact secrets and sensitive content from logs and traces.
- Validate filenames, URLs, MIME types, and structured tool inputs.
- Defend retrieval and tool workflows against prompt injection.
- Record immutable audit events for approvals and consequential actions.
- Pin dependencies and run dependency, secret, and static-analysis scans in CI.

## 8. Evaluation baseline

Each repository must define:

- A representative, versioned evaluation dataset
- Deterministic success criteria where possible
- Quality, safety, latency, and cost metrics
- A baseline and a candidate comparison
- Known limitations and expected failure modes
- A CI threshold that prevents material regressions

LLM-as-judge scores may supplement but never replace deterministic checks and human-reviewed examples. Judges must use pinned prompts, models, and calibration cases.

## 9. Testing and CI

Required CI stages:

1. Format and lint
2. Static typing
3. Unit tests
4. Integration and contract tests
5. Security and secret scans
6. Database migration check
7. Evaluation smoke suite
8. Container build

Tests must cover success, malformed input, dependency failure, timeout, retry, authorization denial, and idempotent replay. Network-dependent tests are isolated and opt-in.

Track A CI currently runs pytest on Windows for Python 3.11/3.12. Expanding toward the full stage list is Track B work.

## 10. Observability

Every request or job carries a correlation ID. Traces record model, retrieval, tool, and approval spans without exposing secrets. Metrics include request volume, latency, errors, token usage, estimated cost, queue depth, cache behavior, and project-specific quality indicators.

## 11. Documentation and demonstration

The README answers: what problem is solved, why AI is appropriate, how the system is designed, how quality is known, and how to run it. Each flagship includes an architecture diagram, a three-minute demo script, sample traces, known limitations, and measured quality/cost/latency results.

## 12. Definition of done

A feature is done only when code, tests, documentation, telemetry, security implications, and evaluation coverage are complete. A successful demo without repeatable tests is not done.
