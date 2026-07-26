# Windows Desk, Tray, Terminal UI, and Autostart

Atticus remains CLI-first. The optional desktop package adds local companions:

- **classical terminal UI** (primary desktop surface — browser or native window);
- a read-only Textual status desk;
- a Windows system tray that launches the terminal, desk, or CLI.

None of these surfaces bypass approvals or silently run tools.

## Install

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api,desktop]"
```

## Terminal UI (recommended)

```powershell
python -m atticus.desktop ui
# force browser instead of native window:
python -m atticus.desktop ui --browser
```

Also available via the API alone:

```powershell
python -m atticus.api_server
# then open http://127.0.0.1:8000/ui/
```

Phone: `python -m atticus.api_server --lan`, then Add to Home Screen / Install app.
See [`TERMINAL_UI.md`](TERMINAL_UI.md).

## Status desk

```powershell
python -m atticus.desktop desk
```

Read-only provider/memory/voice/tool status. Press `r` to refresh, `q` to quit.

## System tray

```powershell
python -m atticus.desktop tray
```

Tray menu:

- **Open Atticus Terminal** (default)
- **Open Status Desk**
- **Open Atticus CLI**
- **Quit tray**

## Windows autostart

```powershell
python -m atticus.desktop autostart status
python -m atticus.desktop autostart enable
python -m atticus.desktop autostart disable
```

Enable/disable require exact confirmation phrases. Autostart launches the tray
only — it does not auto-run tools or open network listeners by itself.

## Scripts on PATH

If `atticus-desktop` is not recognized after install, either add

`%APPDATA%\Python\Python314\Scripts` to PATH, or keep using:

```powershell
python -m atticus.desktop ui
```
