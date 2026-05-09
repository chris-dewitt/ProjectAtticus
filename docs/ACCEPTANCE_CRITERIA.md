# Acceptance Criteria — ProjectAtticus

## Phase 1 acceptance criteria

The Phase 1 CLI build is acceptable when all of the following are true:

- `python -m atticus` launches the CLI.
- Atticus uses the canonical persona prompt.
- Atticus addresses the user as Boss naturally.
- OpenAI is the default provider.
- Claude/Gemini providers exist as stubs or optional implementations.
- Missing API keys produce helpful errors.
- No tests require real API calls.
- SQLite memory can remember/list/forget simple items.
- `/help` shows available commands.
- `/exit` exits cleanly.
- `.env` is gitignored.
- `.env.example` contains no secrets.
- README includes Windows setup.
- Tests pass.

## Security acceptance criteria

- Shell command execution is impossible without a permission gate.
- File edits are impossible without a permission gate.
- Cloud submission of local file contents requires approval.
- Memory forget operation works.
- Logs do not include secrets.
- Prompt injection text in external documents is treated as untrusted content.

## Persona acceptance criteria

Atticus should sound like Atticus, not like a generic assistant.

Good:

```text
Of course, Boss. I’ve got the shape of it. The cleanest next move is to wire the provider layer first, then put memory behind a small SQLite store.
```

Bad:

```text
As an AI language model, I can assist you with that request.
```

Bad:

```text
Yeehaw, pardner, let’s wrangle some Python!
```

## Voice acceptance criteria

Voice is not required for Phase 1. When implemented:

- spoken output can be turned off;
- TTS failure does not crash app;
- wake word is local;
- ambient audio is not sent to cloud;
- user has a kill switch.
