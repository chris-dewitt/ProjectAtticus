# Architecture Decision Record — ProjectAtticus

## ADR-001 — Windows first

Decision: build for Windows first.

Reason: Boss's target machine is a Windows Dell Inspiron.

Implication: setup docs and path handling must be Windows-friendly.

## ADR-002 — Python first

Decision: use Python for the first version.

Reason: fastest path to a working local assistant with CLI, APIs, SQLite, file tools, voice libraries, and tests.

Implication: desktop UI can come later.

## ADR-003 — CLI first

Decision: first working demo is CLI chat.

Reason: safest and fastest foundation. Avoids UI/audio complexity before the assistant brain works.

Implication: voice-first product vision remains, but implementation is phased.

## ADR-004 — OpenAI default provider

Decision: OpenAI is the default brain.

Reason: user preference.

Implication: Claude/Gemini are optional provider modules, not blockers.

## ADR-005 — Automatic provider routing later

Decision: design router immediately, but keep initial routing simple.

Reason: routing is an architectural concern, but complex routing is not needed for v0.1.

Implication: use OpenAI by default while preserving router hooks.

## ADR-006 — Memory on by default, summaries only

Decision: memory is on by default, but raw conversations are not saved by default.

Reason: user wants memory and privacy.

Implication: build summaries/preferences store first.

## ADR-007 — Permission gates required

Decision: all risky tools require confirmation.

Reason: Atticus will eventually act on the user's laptop.

Implication: no shell/file/email/calendar actions bypass permission gate.

## ADR-008 — Voice always eventually, not first code milestone

Decision: spoken responses are a near-term goal, but CLI text chat ships first.

Reason: older Windows laptop and audio dependencies introduce risk.

Implication: voice layer must be optional and failure-tolerant.
