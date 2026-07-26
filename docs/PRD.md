# Product Requirements Document — ProjectAtticus

## Product summary

Atticus is a local-first Windows personal assistant that lives on The Speaker's laptop, responds to "Atticus" and variants, speaks aloud by default, and uses OpenAI, Claude, or Gemini as a swappable reasoning engine.

Atticus is both a personal JARVIS and a local AI chief of staff: coding partner, research analyst, study tutor, finance analyst, life admin helper, and voice-first laptop companion.

## User

Primary user: Speaker.

Context:

- Windows laptop.
- Older Dell Inspiron, approximately five or more years old.
- Repo path: `C:\Users\DELL\Documents\GitHub\ProjectAtticus`.
- User is comfortable with Python and project-based learning.
- User cares deeply about privacy.

## Product personality

Atticus is a full-character Southern gentleman advisor. He should sound kind, old-soul, wise, loyal, and charming. He should be more than a generic chatbot, but he must remain useful and respectful.

Personality constraints:

- Address user as The Speaker.
- Full character is encouraged.
- No racism, bigotry, classism, sexism, or exclusionary stereotypes.
- Atticus loves everybody.
- Do not overdo "sir."
- Do not become a parody.

## Primary goals

1. Build a working local CLI assistant.
2. Support OpenAI as default provider.
3. Design provider abstraction for Claude and Gemini.
4. Add local memory for summaries/preferences.
5. Add privacy gates before file/cloud/tool actions.
6. Add voice output and speech input.
7. Add wake-word detection.
8. Add local tools for file search, summarization, code editing, shell commands, calendar, email, GitHub, and web browsing.
9. Add prompt modes for chief of staff, coding, research, study, finance, and life admin.

## First milestone: CLI Atticus

A successful v0.1 demo allows The Speaker to run:

```powershell
python -m atticus
```

Then chat with Atticus in the terminal. Atticus should:

- load config;
- check for OpenAI API key;
- load persona prompt;
- respond in Atticus voice;
- store summary/preferences locally when appropriate;
- support `/provider`, `/memory`, `/forget`, `/mode`, `/help`, and `/exit` commands;
- include provider router skeleton;
- include stubs for Claude and Gemini;
- include tests.

## Non-goals for v0.1

Do not implement these before the CLI foundation is solid:

- background always-listening loop;
- unrestricted shell execution;
- email sending;
- calendar modifications;
- autonomous app control;
- large desktop UI;
- full file-system access;
- raw transcript persistence.

## Functional requirements

### LLM provider support

- OpenAI is default.
- Claude and Gemini are supported through stubs or optional integrations.
- Provider choice can be manual or automatic.
- Provider errors are user-friendly.

### Voice

- Final product speaks aloud by default.
- Voice mode should be configurable.
- Wake-word detection must be local.
- Audio privacy indicators are required.

### Memory

- Store preferences and summaries by default.
- Do not store raw conversations by default.
- Support remember/forget/list commands.
- Memory must be local.

### Tools

Desired tools:

- read files;
- search folders;
- summarize PDFs/docs;
- write Markdown notes;
- create project files;
- run shell commands;
- open apps;
- edit code;
- manage calendar;
- draft emails;
- send emails;
- browse web.

All tools need permission gating based on risk.

### Modes

Prompt modes should be simple profiles first:

- Chief of Staff
- Coding Partner
- Research Analyst
- Study Tutor
- Finance Analyst
- Life Admin

## Security requirements

- Ask before sending file contents to any cloud provider.
- Ask before shell commands.
- Ask before file edits.
- Ask before emails/calendar changes.
- Store only summaries/preferences by default.
- Do not log secrets.
- Use environment variables or secure keyring.
- `.env` must be ignored.

## Success criteria

v0.1 is successful when:

- The Speaker can chat with Atticus from the CLI.
- Atticus sounds like Atticus.
- OpenAI provider works when a valid key is configured.
- Missing key errors are clear and helpful.
- Local memory can save/list/forget simple preferences.
- Provider abstraction exists.
- Tests pass without calling paid APIs.
