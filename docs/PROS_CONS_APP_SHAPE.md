# App Shape Options — Pros and Cons

Boss asked which first interface is best. This document compares the major options.

## Option 1: Terminal / CLI app

### Pros

- Fastest to build.
- Lowest dependency risk.
- Best for old Windows laptop reliability.
- Easy to test.
- Easy for Codex/Cursor to reason about.
- Perfect first milestone for provider routing, persona, memory, and permissions.
- Avoids premature UI and microphone complexity.

### Cons

- Does not feel like a true laptop companion yet.
- Not voice-first by itself.
- Less polished for daily use.
- Requires opening PowerShell or Terminal.

### Recommendation

Build this first.

## Option 2: Desktop app

Possible frameworks: PySide6, Tauri, Electron, Textual desktop-adjacent UI.

### Pros

- Feels more like a real personal assistant.
- Can show chat history, settings, memory, and permissions clearly.
- Better for nontechnical daily use.
- Can later support tray and notifications.

### Cons

- More dependencies.
- More packaging complexity on Windows.
- UI work can distract from the assistant core.
- Electron may be heavy on older hardware.
- Tauri requires Rust/Node setup.

### Recommendation

Add after CLI foundation. Prefer PySide6 or Tauri later depending on polish needs.

## Option 3: Browser-based local app

Example: FastAPI backend + local web UI.

### Pros

- Easier UI than native desktop.
- Runs locally in browser.
- Can reuse React if desired.
- Good for dashboards/settings/memory inspection.

### Cons

- Feels less like a native assistant.
- Local server/security considerations.
- Browser mic permissions can be finicky.
- More moving parts than CLI.

### Recommendation

Good second-stage option if native desktop slows things down.

## Option 4: System tray assistant

### Pros

- Best final form for "lives on my laptop."
- Always available.
- Can show listening/speaking status.
- Can expose quick actions.
- Feels like a real assistant.

### Cons

- Harder to build safely.
- Background process management matters.
- Wake-word privacy UX matters.
- Audio/resource usage must be controlled.
- More Windows packaging work.

### Recommendation

Target this for v1.0, not v0.1.

## Final recommendation

Use this sequence:

1. CLI app.
2. CLI + spoken responses.
3. Push-to-talk voice.
4. Wake-word loop.
5. Local browser or lightweight desktop UI.
6. System tray assistant.

This gets Boss to a working Atticus quickly without sacrificing the grand vision.
