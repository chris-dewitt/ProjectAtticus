# Roadmap — ProjectAtticus

This roadmap has two tracks. Track A is the shipped personal assistant. Track B is the portfolio agent-platform north star. See `docs/PORTFOLIO_ALIGNMENT.md` for the crosswalk.

---

## Track A — Personal assistant phases

### Phase status summary

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Repo foundation | Complete |
| 1 | CLI Atticus | Complete |
| 2 | Memory + permission core | Complete |
| 3 | Spoken responses | Complete (optional; config-gated) |
| 4 | Speech input (PTT) | Complete (optional `[stt]` extra) |
| 5 | Wake phrase (two-clip local) | Complete (optional; not ambient always-on) |
| 6 | Local file tools | MVP complete (tools off by default) |
| 7 | Coding assistant tools | MVP complete (`/git`, approved `/patch`, gated `/test`) |
| 8 | Integrations | MVP complete (GitHub, Gmail, Calendar, browse citations) |
| 9 | Desktop/tray | MVP complete (status desk, Windows tray, autostart) |

### Phase 0 — Repo foundation

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

### Phase 1 — CLI Atticus

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

### Phase 2 — Local memory and permission core

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

### Phase 3 — Spoken responses

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

### Phase 4 — Speech input

Goal: Boss can speak to Atticus.

Deliverables:

- Microphone input.
- Push-to-talk fallback.
- Local STT adapter.
- Transcription display.
- Error handling for microphone permissions.

Exit criteria:

- Boss can speak a prompt and receive a spoken answer.

### Phase 5 — Wake word

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

Note: current implementation is a two-clip `/wake` flow over local STT, not a continuous ambient detector.

### Phase 6 — Local file tools

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

### Phase 7 — Coding assistant tools

Goal: Atticus can help modify repos safely.

Deliverables:

- Code read/search.
- Patch proposal mode.
- File edit approval.
- Test command approval.
- Git status summary.

Exit criteria:

- Atticus can propose and apply code changes with approval.

Current implementation: allow-listed read-only git and code search, unified
diff plan/apply constrained to approved paths, and approval-gated pytest
commands. Arbitrary shell remains intentionally unavailable.

### Phase 8 — Integrations

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

Current implementation: GitHub REST CLI, Gmail and Calendar OAuth flows,
high-friction confirmation for external writes, URL open, and approved
server-rendered page fetch with local citation capture. JS-heavy browser
automation remains deferred.

### Phase 9 — Desktop/tray experience

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

Current implementation: read-only Textual status desk, Windows tray launcher,
and confirmation-gated Startup-folder management. A full graphical chat and
graphical tool-approval UI remain deferred; the CLI is authoritative.

---

## Track B — Portfolio milestones (SPEC)

Defined in root `SPEC.md`. These are **planned**. Do not mark complete without acceptance evidence.

| Milestone | Goal | Exit criteria (summary) | Status |
|-----------|------|-------------------------|--------|
| M0 | Repo/platform skeleton | Typed config, API health/readiness, CI/telemetry baseline | Not started as platform rewrite (Track A config + pytest CI exist) |
| M1 | Conversation + provider + bounded run | Persisted run with cancel/failure semantics | Partial via CLI chat only |
| M2 | Read tools + citations | File/search tools with structured provenance | Partial via `/file` and `/code-search` |
| M3 | Policy + write + approvals + audit | First-class policy decisions and approval workflow | Partial via permission classes + y/N + audit table |
| M4 | Memory controls + sandbox + replay + traces | Inspectable plans/tools/approvals/artifacts | Partial memory controls only |
| M5 | Evals + routing + demo + deploy docs | Signature demo + adversarial/golden evals | Not started |

### Signature demo (Track B acceptance target)

Research three current RAG-evaluation approaches, save cited findings, create a comparison table, draft a GitHub issue, and stop for approval before publishing — with trace and quality report in about three minutes after setup.

### Recommended Track B entry

When Boss asks to advance the portfolio track, start with the smallest **M0** vertical slice and record assumptions in ADRs. Prefer evolving existing `atticus/` seams over a greenfield rewrite. Details: `docs/PORTFOLIO_ALIGNMENT.md`.
