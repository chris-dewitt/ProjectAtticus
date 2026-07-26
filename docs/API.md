# Track B local API

Status: M0–M5 local platform API + retro `/ui` + optional Next.js `web/` (ADR-010–018)

## Install and run

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api]"
atticus-api
# UI: http://127.0.0.1:8000/ui/
# Phone/LAN (trusted network only):
atticus-api --lan
```

Defaults (from `config/atticus.example.yaml`):

- host: `127.0.0.1`
- port: `8000`
- retro UI: on (`api.ui_enabled: true`) at `/ui/`
- OpenAPI docs: off (`api.docs_enabled: false`)
- runs DB: `data/atticus_runs.sqlite3`
- citations dir: `tools.browser.citation_dir` (`data/citations`)
- policy/audit DB: `data/atticus_approvals.sqlite3`

See also [`docs/TERMINAL_UI.md`](TERMINAL_UI.md).

## Health

| Method | Path | Meaning |
|--------|------|---------|
| GET | `/health/live` | Process is up |
| GET | `/health/ready` | Config + memory path + runs path usable |
| GET | `/ready` | Alias of `/health/ready` |

## Conversations and bounded runs (M1)

| Method | Path | Meaning |
|--------|------|---------|
| POST | `/v1/conversations` | Create conversation (`{"title"?}`) |
| GET | `/v1/conversations/{id}` | Fetch conversation |
| GET | `/v1/conversations/{id}/messages` | List messages |
| POST | `/v1/conversations/{id}/messages` | Append user message; optionally execute a run |
| POST | `/v1/runs` | Create a run (optionally creates a conversation) |
| GET | `/v1/runs/{id}` | Fetch run + checkpoints |
| POST | `/v1/runs/{id}/cancel` | Cancel queued/running run |

### Example

```powershell
# Create conversation
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/conversations -ContentType 'application/json' -Body '{"title":"demo"}'

# Send message + execute bounded run (uses configured provider; tests use mock)
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/conversations/<id>/messages `
  -ContentType 'application/json' `
  -Headers @{ 'Idempotency-Key' = 'demo-1' } `
  -Body '{"content":"Status report?","execute":true,"provider":"mock"}'
```

Run statuses: `queued` → `running` → `succeeded` | `failed` | `cancelled`.

Checkpoints recorded on the run include `queued`, `validate_request`, `assemble_context`, `execute_provider`, and `finalize` (or `cancelled` / `failed`).

### Idempotency

Send `Idempotency-Key` on `POST /v1/conversations/{id}/messages` or `POST /v1/runs`. Replay returns the original run without creating a duplicate.

### Providers

- Default provider comes from config (`providers.routing.default_provider`, usually `openai`).
- Request body may set `"provider": "openai" | "anthropic" | "gemini" | "mock"`.
- `mock` is for tests/fixtures only (no network).
- Live providers still require env credentials; automated tests never call paid APIs.

## Correlation IDs

- Send `X-Correlation-ID` to propagate a client id.
- Responses always include `X-Correlation-ID`.
- Structured error bodies include `correlation_id` when available.

## Structured errors

```json
{
  "error": {
    "code": "run_not_found",
    "message": "Run not found: ...",
    "correlation_id": "...",
    "details": {"run_id": "..."}
  }
}
```

## Telemetry

`atticus.core.telemetry` records redacted in-process events and can export
OTel-shaped JSON lines (`telemetry.otel_exporter: stderr|file`).

## Privacy notes

- Run transcripts live in the local runs SQLite DB (`api.runs_sqlite_path`), separate from Track A memory notes/summaries.
- Raw Track A chat transcripts are still not stored by default.
- Do not point the API at cloud hosts without an explicit later ADR.

## Citations / provenance (M2)

| Method | Path | Meaning |
|--------|------|---------|
| GET | `/v1/citations` | List recent structured citations |
| GET | `/v1/citations/{id}` | Fetch one citation record |

Schema version: `atticus.citation.v1` (stable id, kind, source URI, sha256, evidence spans, tool name, trust flags). Produced by CLI `/browse`, `/file read`, `/code-search`. Legacy browse JSON is normalized on read.

## Policy and approvals (M3)

| Method | Path | Meaning |
|--------|------|---------|
| POST | `/v1/policy/evaluate` | Persist deterministic allow/deny/require-approval decision |
| POST | `/v1/approvals` | Evaluate intent and create approval when required |
| GET | `/v1/approvals` | List requests; filter `?status=pending` |
| GET | `/v1/approvals/{id}` | Inspect exact action digest and lifecycle |
| POST | `/v1/approvals/{id}/decision` | Approve/deny (token + exact phrase required) |
| POST | `/v1/approvals/{id}/execution` | Manually record approved action result |
| POST | `/v1/approvals/{id}/execute` | Gateway-dispatch the approved action (`Idempotency-Key` required) |
| GET | `/v1/audit/policy` | Read policy audit (token required) |

Before decisions work, create a long random local secret:

```powershell
$env:ATTICUS_APPROVAL_TOKEN = "replace-with-a-long-random-value"
atticus-api
```

All policy/approval/audit endpoints require `X-Atticus-Approval-Token`.
Decision calls additionally require:

- Header `X-Atticus-Approval-Token`
- The full returned `action_digest`
- Exact `confirmation`: `APPROVE <confirmation_hint>` or
  `DENY <confirmation_hint>`

The terminal UI's **AUTH APPROVALS** control holds the token only in page memory,
then displays pending/approved requests. Decide with the exact phrase; EXECUTE
prompts for an `Idempotency-Key`. The token is never written to local storage.

Dispatchable tools in this slice: `local_echo`, `file_write` (approved paths).

## Traces and replay (M4)

| Method | Path | Meaning |
|--------|------|---------|
| GET | `/v1/traces/{run_id}` | List persisted spans for a run |
| GET | `/v1/runs/{run_id}/replay` | Reconstruct checkpoints/spans/artifacts |

## Sandbox (M4)

| Method | Path | Meaning |
|--------|------|---------|
| POST | `/v1/sandbox/execute` | Run bounded Python (shell opt-in) |

## Memory and settings

| Method | Path | Meaning |
|--------|------|---------|
| GET/POST | `/v1/memory/*` | list/search/remember/forget |
| GET/PATCH | `/v1/settings` | Non-secret operator toggles |

## Evals and signature demo (M5)

| Method | Path | Meaning |
|--------|------|---------|
| POST | `/v1/evals/run?suite=platform` | Run versioned eval suite |
| POST | `/v1/demo/signature` | Synthetic signature demo; stops for approval |

## Auth and rate limits

- When `ATTICUS_API_TOKEN` is set, `/v1/*` requires `X-Atticus-Api-Token`.
- `api.rate_limit_per_minute` applies a fixed-window limiter (0 disables).

## Still incremental

- Broader gateway handlers (gmail/calendar/git publish)
- Authenticated LAN pairing for phone access
- Postgres as default store (Compose service available; SQLite default)
