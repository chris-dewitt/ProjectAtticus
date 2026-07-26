# Atticus classical terminal UI

Status: local web terminal for computer + installable phone/desktop PWA

## Look and feel

Subdued classical terminal: graphite field, soft brass/amber phosphor text,
IBM Plex Mono, thin rules, restrained motion. **ATTICUS** remains the brand
hero. Same-origin with the local API.

## Run (computer)

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api]"
python -m atticus.api_server
```

Open: `http://127.0.0.1:8000/ui/`

### Desktop app window

```powershell
pip install -e ".[api,desktop]"
python -m atticus.desktop ui
```

This starts the local API if needed and opens a native window (pywebview) or
falls back to your browser (`--browser` to force the browser).

Tray shortcut:

```powershell
python -m atticus.desktop tray
```

Default tray action: **Open Atticus Terminal**.

## Run (phone on trusted LAN)

```powershell
python -m atticus.api_server --lan
```

On the phone, open `http://<your-pc-lan-ip>:8000/ui/`.

Install as an app:

- **iPhone/Safari:** Share → Add to Home Screen  
- **Android/Chrome:** menu → Install app / Add to Home Screen  
- Or tap **Install app** in the terminal when the browser offers it

Warnings:

- `--lan` binds `0.0.0.0` — use only on a network you trust.
- Prefer setting `ATTICUS_API_TOKEN` before LAN exposure.
- Do not expose to the public internet.
- Live LLM calls still need provider API keys on the PC.

## What it does

- GUI chat through `/v1` bounded runs
- Health/ready + editable settings
- Citations, approval queue, trace/replay, signature demo
- Installable PWA shell (service worker caches `/ui` assets only — never API bodies)

Config flag: `api.ui_enabled` (default `true`).
