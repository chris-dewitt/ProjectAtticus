# Track B local API

Status: M0 health + M1 bounded runs (ADR-010, ADR-011)

## Install and run

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api]"
atticus-api
```

Defaults (from `config/atticus.example.yaml`):

- host: `127.0.0.1`
- port: `8000`
- OpenAPI docs: off (`api.docs_enabled: false`)
- runs DB: `data/atticus_runs.sqlite3`

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

`atticus.core.telemetry` records redacted in-process events (`api.request`, `run.succeeded`, `run.failed`, `run.cancelled`). No OpenTelemetry exporter yet.

## Privacy notes

- Run transcripts live in the local runs SQLite DB (`api.runs_sqlite_path`), separate from Track A memory notes/summaries.
- Raw Track A chat transcripts are still not stored by default.
- Do not point the API at cloud hosts without an explicit later ADR.

## Out of scope (later milestones)

- Approvals API and policy engine objects (M3)
- Trace viewer / replay UI (M4)
- EvalForge suites (M5)
- Postgres / Redis / Docker Compose
