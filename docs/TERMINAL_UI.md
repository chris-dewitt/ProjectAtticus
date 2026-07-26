# Atticus retro terminal UI

Status: local web terminal for computer/phone (Track B UI slice)

## Look and feel

CRT / phosphor-green terminal chrome, monospace type, scanline atmosphere, **ATTICUS** as the brand hero. Same-origin with the local API — no CDN assets.

## Run (computer)

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api]"
atticus-api
```

Open: `http://127.0.0.1:8000/ui/`

Defaults stay on loopback (`api.host: 127.0.0.1`).

## Run (phone on trusted LAN)

```powershell
atticus-api --lan
```

Then open `http://<your-pc-lan-ip>:8000/ui/` on the phone.

Warnings:

- `--lan` binds `0.0.0.0` — use only on a network you trust.
- There is no auth token yet; do not expose to the public internet.
- Live LLM calls still need provider API keys in the PC environment.

## What it does

- Creates/resumes a `/v1` conversation session
- Sends messages through bounded runs
- Shows health/ready status
- Lists structured citations from `/v1/citations`
- **AUTH APPROVALS** prompts for `ATTICUS_APPROVAL_TOKEN`, kept only in page
  memory, then shows pending requests
- Approve/deny prompts for an exact digest phrase; the token is never written
  to local storage

Config flag: `api.ui_enabled` (default `true`). Set `false` to serve API-only.
