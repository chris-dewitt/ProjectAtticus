# Cursor Task Prompts — ProjectAtticus

Use these with Cursor Agent mode. Cursor should automatically read `.cursor/rules/*.mdc`.

## Initial Cursor prompt

```text
Read AGENTS.md, docs/PRD.md, docs/ARCHITECTURE.md, docs/SECURITY.md, docs/PERSONA.md, and docs/ROADMAP.md. Then produce a concise implementation plan for Phase 1 only. Do not write code until the plan is clear.
```

## Build Phase 1

```text
Implement Phase 1 from docs/ROADMAP.md.

Keep scope tight:
- Python CLI only.
- OpenAI provider working if OPENAI_API_KEY is set.
- Claude/Gemini stubs.
- Provider abstraction.
- Persona prompt.
- Local SQLite memory skeleton.
- Basic slash commands.
- Tests with mocks.

Do not implement voice, wake word, shell execution, calendar, email, browser, or desktop UI in this pass.
```

## Review prompt

```text
Review the current diff against AGENTS.md and docs/SECURITY.md. Identify any privacy, secrets, permission, or architecture problems. Suggest fixes before we proceed.
```

## Refactor prompt

```text
Refactor only where needed to improve modularity. Do not change behavior. Keep provider-specific code inside atticus/providers. Keep permission checks centralized. Add or update tests if refactoring changes interfaces.
```

## Test prompt

```text
Run the relevant tests. If tests fail, fix the underlying issue rather than weakening the tests. Do not call real provider APIs during tests.
```
