# Agent Handoff — ProjectAtticus

## What we are building

A Windows-first, local-first personal assistant named Atticus. He is a full-character Southern gentleman advisor who responds to Boss, uses OpenAI by default, supports Claude/Gemini later, remembers summaries/preferences, and eventually speaks/listens through local voice components.

## What matters most

1. Privacy.
2. Modularity.
3. Working CLI foundation.
4. Provider abstraction.
5. Atticus persona.
6. Permission-gated actions.
7. Tests.

## What not to do first

Do not start with:

- a complex desktop UI;
- wake-word implementation;
- shell command execution;
- Gmail sending;
- calendar write access;
- unrestricted file access;
- raw transcript storage.

## Best first PR

Implement Phase 1 CLI:

- package scaffold;
- config;
- persona;
- provider base;
- OpenAI provider;
- Claude/Gemini stubs;
- memory skeleton;
- slash commands;
- tests;
- Windows setup docs.

## Completion report format

When an agent completes work, report:

```text
Summary:
- ...

Files changed:
- ...

Tests run:
- ...

Security/privacy notes:
- ...

Known limitations:
- ...

Recommended next step:
- ...
```
