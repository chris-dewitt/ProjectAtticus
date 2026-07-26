# Downloadable Atticus app (Windows)

Atticus ships as a **downloadable desktop app** that connects to the local
Atticus API (The Listener) for The Speaker.

## Quick path (dev machine — use this today)

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api,desktop]"
python -m atticus.launcher
```

Same thing via desktop entry:

```powershell
python -m atticus.desktop ui
```

This starts the local API if needed and opens the classical terminal window.

## Build `Atticus.exe`

On Windows, from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_app.ps1
```

Output:

```text
dist\Atticus.exe
```

Copy that file anywhere (Desktop, USB, another folder). Double-click to launch.
No browser install required when `pywebview` is bundled.

## What the app does

1. Starts (or connects to) the local Atticus API on `127.0.0.1:8000`
2. Opens the classical terminal UI in a native window
3. Talks to the same `/v1` chat, approvals, traces, and settings endpoints

## Secrets

Never bake API keys into the exe. Set user environment variables or place a
`.env` next to the executable / working directory:

```text
OPENAI_API_KEY=...
ATTICUS_APPROVAL_TOKEN=...
```

## Phone companion

The phone surface remains the installable PWA:

```powershell
python -m atticus.api_server --lan
```

Then on the phone: open `http://<pc-ip>:8000/ui/` → Add to Home Screen.

## Notes

- First launch may take a few seconds while the local API starts.
- If a window fails to open, run `python -m atticus.launcher --browser`.
- CI does not currently publish signed installers; the PowerShell script is the
  supported local packaging path.
