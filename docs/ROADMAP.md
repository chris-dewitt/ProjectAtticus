# Roadmap — ProjectAtticus

## Phase 0 — Repo foundation

Goal: make the repo agent-ready.

Deliverables:

- `README.md`
- `AGENTS.md`
- `.cursor/rules/*.mdc`
- `docs/` architecture and product docs
- `.gitignore`
- `.env.example`
- `config/atticus.example.yaml`

Exit criteria:

- Cursor and Codex have enough instruction context to build safely.

## Phase 1 — CLI Atticus

Goal: text-based Atticus works.

Deliverables:

- Python package scaffold.
- CLI chat loop.
- Atticus persona prompt.
- OpenAI provider.
- Claude/Gemini provider stubs.
- Provider router skeleton.
- YAML + env config.
- SQLite memory skeleton.
- `/help`, `/exit`, `/provider`, `/mode`, `/memory`, `/forget` commands.
- Tests with mocked providers.

Exit criteria:

- Boss can run `python -m atticus` and chat with Atticus.
- Atticus sounds like Atticus.
- Tests pass without paid API calls.

## Phase 2 — Local memory and permission core

Goal: Atticus remembers safely and asks before risky actions.

Deliverables:

- Preference storage.
- Memory item storage.
- Conversation summary storage.
- Forget flow.
- Memory inspection command.
- Permission classes.
- Approval prompts.
- Tool audit log.

Exit criteria:

- Boss can tell Atticus to remember and forget things.
- Sensitive operations require approval.

## Phase 3 — Spoken responses

Goal: Atticus speaks aloud.

Deliverables:

- Offline TTS adapter.
- Config switch for spoken responses.
- CLI response playback.
- Mute flag.
- TTS failure fallback.

Exit criteria:

- Atticus speaks responses aloud on Boss's Windows laptop.
- App still works if TTS is unavailable.

## Phase 4 — Speech input

Goal: Boss can speak to Atticus.

Deliverables:

- Microphone input.
- Push-to-talk fallback.
- Local STT adapter.
- Transcription display.
- Error handling for microphone permissions.

Exit criteria:

- Boss can speak a prompt and receive a spoken answer.

## Phase 5 — Wake word

Goal: Atticus activates on wake phrases.

Deliverables:

- Local wake-word engine.
- Wake phrases: "Atticus," "Hey Atticus," variants.
- Visible listening indicator.
- Kill switch.
- Configurable sensitivity.
- Audio privacy docs.

Exit criteria:

- Atticus can locally detect wake phrases without streaming ambient audio to the cloud.

## Phase 6 — Local file tools

Goal: Atticus can help with local documents and project files.

Deliverables:

- Approved folder registry.
- File search.
- PDF/doc summarization.
- Markdown note writing.
- Project file creation.
- Permission prompts before cloud submission.

Exit criteria:

- Boss can ask Atticus to search/summarize files safely.

## Phase 7 — Coding assistant tools

Goal: Atticus can help modify repos safely.

Deliverables:

- Code read/search.
- Patch proposal mode.
- File edit approval.
- Test command approval.
- Git status summary.

Exit criteria:

- Atticus can propose and apply code changes with approval.

## Phase 8 — Integrations

Goal: Gmail, Calendar, GitHub, and web browsing.

Deliverables:

- OAuth or secure local auth strategy.
- Gmail draft flow.
- Gmail send confirmation.
- Calendar read flow.
- Calendar write confirmation.
- GitHub repo search/issues/PRs.
- Web browsing with source tracking.

Exit criteria:

- Atticus can help manage communications and projects without bypassing confirmations.

## Phase 9 — Desktop/tray experience

Goal: Atticus feels like he lives on the laptop.

Deliverables:

- Local UI.
- System tray.
- Voice state indicator.
- Settings panel.
- Memory panel.
- Provider switcher.
- Tool approval UI.

Exit criteria:

- Atticus can be launched at startup and used throughout the day.
