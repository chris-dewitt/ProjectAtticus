# Windows Desk, Tray, and Autostart

Atticus remains CLI-first. The optional desktop package adds two local
companions:

- a read-only Textual status desk;
- a Windows system tray that launches the desk or opens a new Atticus CLI.

Neither surface executes tools, arms the microphone, edits config, or bypasses
the existing CLI approval/audit flow.

## Install

From the repository root in an activated virtual environment:

```powershell
pip install -e ".[desktop]"
```

## Desk

```powershell
atticus-desktop
# equivalent:
atticus-desktop desk
```

The desk displays:

- default provider and whether each provider credential is configured (never
  the credential value);
- local memory counts and database path;
- voice configuration;
- global/per-tool enablement;
- Windows autostart status.

Press `r` to refresh and `q` to quit. The desk is read-only by design.

## System tray

```powershell
atticus-desktop tray
```

Tray menu:

- **Open Atticus Desk**
- **Open Atticus CLI**
- **Quit tray**

The tray does not run tools or capture audio in the background.

## Windows autostart

Inspect:

```powershell
atticus-desktop autostart status
```

Enable:

```powershell
atticus-desktop autostart enable
```

Atticus shows the exact Startup file and command, then requires typing
`ENABLE`. It creates only:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ProjectAtticus-Tray.cmd
```

Disable:

```powershell
atticus-desktop autostart disable
```

Atticus requires typing `DISABLE`, then removes only its own launcher.

Autostart uses the Python environment active when it is enabled. If the repo or
virtual environment moves, disable and enable autostart again.

## Limitations

- Tray/autostart are Windows-only.
- There is no full graphical chat yet; the tray opens the CLI.
- Runtime mute/mic state belongs to each CLI process and is not controlled by
  the tray.
- OAuth and tool approvals remain terminal flows.
