# Infrastructure

Azure-first deploy sketches for Track B (SHARED_ENGINEERING_STANDARD §3).

This directory is intentionally thin: ProjectAtticus remains Windows-first and
local-first for Track A. Cloud deploy is optional for portfolio demos.

## Layout

```text
infra/
  README.md
  terraform/
    main.tf
    variables.tf
    outputs.tf
```

## Local dependencies

Prefer `docker compose up` from the repo root for API + Postgres + Redis + web.

## Azure notes

- Container Apps (or App Service) for `atticus-api`
- Azure Database for PostgreSQL when migrating off SQLite
- Azure Cache for Redis only if queue/coordination is justified
- Secrets via Key Vault; never commit tokens
- Terraform state must use a remote backend before any shared environment

See `docs/DEPLOYMENT.md` for operator steps and ADR-016 for stack decisions.
