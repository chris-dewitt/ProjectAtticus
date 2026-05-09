# Implementation Notes — ProjectAtticus

## Recommended first dependencies

Keep dependencies lean in Phase 1.

Possible `requirements.txt`:

```text
openai
python-dotenv
pydantic
pydantic-settings
PyYAML
rich
typer
pytest
```

Add Anthropic/Gemini SDKs only when implementing those providers:

```text
anthropic
google-genai
```

Add voice dependencies only after CLI works.

## First package files to create

```text
atticus/__init__.py
atticus/__main__.py
atticus/app.py
atticus/core/config.py
atticus/core/persona.py
atticus/core/router.py
atticus/providers/base.py
atticus/providers/openai_provider.py
atticus/providers/anthropic_provider.py
atticus/providers/gemini_provider.py
atticus/providers/mock_provider.py
atticus/memory/store.py
tests/test_config.py
tests/test_router.py
tests/test_memory.py
```

## CLI command sketch

```text
/help
/exit
/provider
/provider openai
/mode
/mode coding_partner
/memory
/remember <text>
/forget <query>
/mute
```

## Error messages

Make errors helpful and in character.

Example missing key:

```text
I ran into a snag, Boss. OPENAI_API_KEY is not set, so I cannot call OpenAI yet. Set it as a Windows environment variable, reopen PowerShell, and try again.
```

## Testing approach

Use mock provider by default in tests.

Never call paid APIs during test runs.

## Packaging later

Do not package as EXE until the CLI, memory, voice, and permissions work reliably.

Future options:

- PyInstaller;
- Briefcase;
- Tauri wrapper;
- Windows startup shortcut.
