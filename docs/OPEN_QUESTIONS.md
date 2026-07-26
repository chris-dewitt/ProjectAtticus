# Open Questions

## Track A (personal assistant)

These do not block the shipped CLI.

1. Which exact OpenAI model should be the production default once costs and latency are tested?
2. Should Atticus prefer Windows Credential Manager through `keyring` for OpenAI as well as GitHub tokens? (`get_credential` exists; OpenAI provider still reads env directly.)
3. Which TTS voice sounds most like Atticus on The Speaker's laptop?
4. Which local STT engine performs best on the older Dell Inspiron?
5. Should the desktop UI be PySide6, Tauri, Textual expansion, or local browser UI?
6. How should Gmail/Calendar OAuth scopes be minimized?
7. Should provider routing be rules-based, model-based, or user-confirmed for sensitive tasks?
8. How should Atticus auto-summarize conversations without storing raw transcripts? (`memory/summarizer.py` is still a stub.)

## Track B (portfolio platform)

These do not authorize starting M0–M5 until The Speaker asks.

1. When should FastAPI (or another typed API) be introduced alongside the CLI — M0 skeleton, or only when the signature demo needs it?
2. When is Postgres justified over continuing with SQLite for local-first Windows use?
3. How and when should EvalForge integrate (export format, CI threshold, golden set ownership)?
4. Does the Southern gentleman persona remain on the platform API/web surface, or is persona CLI-only while the API stays neutral?
5. Should Track B live as evolved modules inside `atticus/` or eventually migrate toward a `src/` layout per the shared standard?
6. What is the minimum telemetry stack that satisfies the shared standard without overloading the older Dell laptop?
