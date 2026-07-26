# Architecture — ProjectAtticus

## Dual-track view

- **Current implementation (Track A):** modular local CLI assistant under `atticus/` — Rich interface, orchestration helpers, OpenAI provider, SQLite memory, permission-gated tools, optional voice/desktop. This section below describes that shape.
- **Target platform (Track B):** bounded orchestrator, policy engine, typed API, traces/replay, and evaluation hooks described in root [`SPEC.md`](../SPEC.md). See [`PORTFOLIO_ALIGNMENT.md`](PORTFOLIO_ALIGNMENT.md) for what is shipped vs planned.

Do not assume Postgres, Next.js, or a `src/` layout exist in the tree today. An optional FastAPI API exists under `atticus/api/` with health, bounded runs, citations, policy/approvals, and a retro `/ui` terminal (`atticus/runs/`, `atticus/policy/`, ADR-010–013) — not a full tool-dispatch/traces platform.

## Architectural thesis

Atticus should be built as a modular local application with a thin orchestration core, swappable model providers, local memory, permission-gated tools, and optional voice/desktop layers.

The assistant should never be one giant script. The core must be simple enough to run on an older Windows laptop and structured enough that Codex/Cursor agents can safely extend it.

## Current implementation shape (Track A)

```text
ProjectAtticus/
  atticus/
    __init__.py
    __main__.py
    app.py
    api/                 # Track B: health + /v1 runs (optional .[api])
      app.py
      health.py
      runs.py
      schemas.py
      v1_schemas.py
      errors.py
    api_server.py
    runs/                # Track B domain: store + bounded orchestrator
      models.py
      store.py
      orchestrator.py
    policy/              # Track B M3: decisions, approvals, audit
      models.py
      engine.py
      service.py
      store.py
    core/
      config.py
      persona.py
      router.py
      permissions.py
      telemetry.py
      errors.py
    providers/
      base.py
      openai_provider.py
      anthropic_provider.py
      gemini_provider.py
      mock_provider.py
    memory/
      store.py
      models.py
      summarizer.py
    tools/
      base.py
      files.py
      shell.py
      apps.py
      browser.py
      calendar.py
      email.py
      github.py
    voice/
      tts.py
      stt.py
      wake_word.py
      audio_state.py
    prompts/
      persona.py
      modes.py
      router.py
  config/
    atticus.example.yaml
  docs/
  tests/
  .cursor/rules/
  .env.example
  .gitignore
  AGENTS.md
  README.md
```

## Target platform shape (Track B)

See `SPEC.md` for the full platform diagram and components:

- typed API and identity boundary
- application workflow / state machine with persisted checkpoints
- domain services, AI adapters, policy/eval
- Postgres/artifacts, model providers, traces/metrics
- tool gateway with schema validation, timeouts, idempotency
- evaluation adapter for EvalForge

Track B must keep domain logic independent of web frameworks and provider SDKs. Adopt stack pieces via ADRs; do not silently replace Track A.

## Layers (Track A today)

### 1. Interface layer

Primary interface: CLI (`atticus/app.py`).

Companion / future interfaces:

- optional voice loop (PTT/wake);
- thin Textual desk;
- future system tray / richer UI (Track A phase 9 / Track B web UI).

Interface layer responsibilities:

- collect input;
- display/speak output;
- ask for confirmations;
- show status;
- never directly call provider SDKs;
- never directly execute tools without permission core.

### 2. Orchestration core

Responsibilities:

- load config;
- select mode;
- assemble system prompt;
- route to provider;
- call memory layer;
- call tool layer through permission checks;
- normalize errors.

### 3. Provider layer

One common interface for OpenAI, Anthropic, Gemini, and mock providers.

Provider modules handle:

- credentials;
- SDK-specific message format;
- API calls;
- model names;
- provider-specific errors;
- provider-specific rate-limit handling.

The rest of the app should not know provider details.

### 4. Memory layer

Initial storage: SQLite.

Store summaries and preferences, not raw transcripts by default.

Suggested tables:

```text
preferences
  id
  key
  value
  source
  created_at
  updated_at

memory_items
  id
  kind
  content
  tags
  confidence
  created_at
  updated_at
  deleted_at

conversation_summaries
  id
  summary
  mode
  provider
  created_at

tool_approvals
  id
  tool_name
  permission_class
  action_summary
  approved
  created_at

approved_paths
  id
  path
  access_level
  created_at
  revoked_at
```

### 5. Tool layer

Tools should be separate from permission checks.

Bad:

```python
shell.run("dir")
```

Good:

```python
permission_gate.request(tool_call)
if approved:
    shell.run(tool_call)
```

Tool call schema:

```python
@dataclass
class ToolCallRequest:
    tool_name: str
    permission_class: PermissionClass
    action_summary: str
    inputs: dict
    external_data: bool = False
    destructive: bool = False
```

### 6. Voice layer

Voice should be optional at runtime. The app should still run if microphone/TTS dependencies are unavailable.

Voice responsibilities:

- TTS playback;
- STT transcription;
- wake-word detection;
- audio status;
- kill switch.

## Provider routing

v0.1:

```text
User request -> OpenAIProvider
```

v0.2:

```text
User request -> ProviderRouter -> selected provider
```

v1.0:

```text
User request
  -> privacy classifier
  -> mode selector
  -> provider router
  -> permission gate if tools/files involved
  -> provider
  -> local memory summary
  -> spoken response
```

## Security boundary

The main security boundary is between local user data and cloud providers.

Any flow that crosses this boundary must ask Boss first.

Boundary examples:

- local file -> OpenAI: ask.
- local file -> Claude: ask.
- local file -> Gemini: ask.
- conversation summary -> local SQLite: allowed by default unless sensitive.
- shell command -> Windows: ask every time.
- email draft -> Gmail: ask.
- email send -> Gmail recipient: ask again.

## Why CLI first

CLI first is not a retreat from the vision. It is the best foundation.

Benefits:

- easiest to test;
- lowest dependency risk;
- fastest path to a real assistant;
- easiest for Codex/Cursor to extend;
- avoids audio/UI issues before the brain works.

## Desktop options later

See `docs/PROS_CONS_APP_SHAPE.md` for CLI, desktop, browser-local, and tray tradeoffs.
