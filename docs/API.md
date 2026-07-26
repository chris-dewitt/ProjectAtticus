# Track B local API (M0)

Status: M0 health/readiness slice only (ADR-010)

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

## Endpoints

| Method | Path | Meaning |
|--------|------|---------|
| GET | `/health/live` | Process is up; returns service name, version, correlation id |
| GET | `/health/ready` | Config loadable + memory parent path writable |
| GET | `/ready` | Alias of `/health/ready` |

Not ready returns HTTP 503 with a structured `checks` list. Missing/invalid config does not fall back to the example file for readiness when an explicit path was configured on the app.

## Correlation IDs

- Send `X-Correlation-ID` to propagate a client id.
- Responses always include `X-Correlation-ID`.
- Structured error bodies include `correlation_id` when available.

## Structured errors

Unhandled failures and `AtticusError` subclasses return:

```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred.",
    "correlation_id": "...",
    "details": {}
  }
}
```

## Telemetry

`atticus.core.telemetry` records redacted in-process events (`api.request`, `api.readiness`, `api.error`). No OpenTelemetry exporter is installed in M0.

## Out of scope (later milestones)

- Conversations / chat completions
- Persisted bounded runs (M1)
- Approvals, traces, evals, Postgres
