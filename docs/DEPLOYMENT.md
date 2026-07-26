# Deployment

## Local (recommended)

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
python -m pip install -e ".[dev,api]"
copy config\atticus.example.yaml config\atticus.yaml
# set OPENAI_API_KEY / ATTICUS_APPROVAL_TOKEN in .env as needed
atticus-api
```

- Terminal UI: `http://127.0.0.1:8000/ui/`
- Next.js console (optional): `cd web && npm install && npm run dev`
- Signature demo: `python scripts/run_signature_demo.py`
- Evals: `python scripts/run_evals.py --suite platform`

## Docker Compose

```powershell
docker compose up --build
```

Services:

| Service  | Port | Role                                      |
|----------|------|-------------------------------------------|
| api      | 8000 | FastAPI + retro `/ui` + `/v1`             |
| web      | 3000 | Next.js operator console                  |
| postgres | 5432 | Optional platform DB (SQLite still default) |
| redis    | 6379 | Optional queue/cache                      |

Secrets belong in a local `.env` consumed by Compose — never commit them.

## Azure (optional)

Terraform sketches live under `infra/terraform/`. Before apply:

1. Configure a remote state backend.
2. Build/push the API image to a registry you control.
3. Store `ATTICUS_API_TOKEN` / `ATTICUS_APPROVAL_TOKEN` / provider keys in Key Vault.
4. Confirm the threat model in `docs/SECURITY.md`.

Track A on The Speaker's Windows laptop does **not** require Azure.
