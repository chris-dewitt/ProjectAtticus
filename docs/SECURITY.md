# Security and Privacy — ProjectAtticus

## Security principle

Atticus is local-first. Cloud LLMs are reasoning providers, not owners of Boss's laptop.

The app must treat local files, speech transcripts, memory, emails, calendar data, shell access, and credentials as sensitive.

## Threat model

### Assets to protect

- API keys.
- OAuth tokens.
- Local files.
- Conversation summaries.
- Memory database.
- Email/calendar data.
- Shell access.
- GitHub tokens.
- Private project code.
- Voice/audio data.

### Main risks

1. Accidentally committing secrets to git.
2. Sending private file contents to a cloud LLM without consent.
3. Running a harmful shell command.
4. Editing or deleting files unexpectedly.
5. Sending an email or invite before review.
6. Storing too much private conversation history.
7. Background microphone behavior that feels invasive.
8. Overbroad OAuth permissions.
9. Logging sensitive data.
10. Prompt injection from documents or web pages.

## Permission classes

Use these classes throughout the app:

| Class | Meaning | Default behavior |
|---|---|---|
| `safe_read` | Read internal config/state | Allow |
| `sensitive_read` | Read user files/email/calendar/etc. | Ask unless source is approved |
| `write` | Create or modify local files/settings/drafts | Ask |
| `destructive` | Delete/overwrite/clear/revoke | High-friction ask |
| `external_send` | Send data outside the laptop | Ask and summarize payload |
| `execute` | Run commands/code/open apps | Ask every time |

## Confirmation requirements

### Shell commands

Every shell command requires confirmation.

Required prompt contents:

- command;
- working directory;
- reason;
- risk level;
- whether it modifies files;
- whether it accesses network.

### File edits

Every file edit requires confirmation unless it is in a temporary test directory created by automated tests.

Required prompt contents:

- path;
- summary of change;
- diff preview if possible.

### Cloud provider calls with file content

Atticus must ask before sending local file contents, document excerpts, transcripts, code, or email/calendar content to cloud models.

Required prompt contents:

- provider;
- files/sources involved;
- whether full content or excerpt will be sent;
- reason;
- option to cancel.

### Email/calendar actions

Drafting may require confirmation if using external provider APIs. Sending or modifying events always requires final confirmation.

## Secrets handling

Use environment variables for v0.1:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

Later, support Windows Credential Manager via Python `keyring`.

Rules:

- `.env` must be ignored.
- `.env.example` contains placeholders only.
- Never print or log secrets.
- Never include secrets in exceptions.
- Mask any accidental secret-like values in logs.

## Logging policy

Logs should include:

- timestamps;
- action names;
- provider name;
- success/failure;
- error class;
- approval metadata.

Logs should not include:

- API keys;
- full prompts with file contents;
- raw transcripts by default;
- email bodies;
- full document contents;
- passwords/tokens.

## Memory policy

Default storage:

- preferences;
- brief summaries;
- project/task context;
- approved paths;
- tool approval audit metadata.

Default non-storage:

- raw conversations;
- full audio;
- full transcripts;
- full file contents;
- sensitive personal facts unless explicitly requested.

## Prompt injection defense

Any file, web page, email, or external document must be treated as untrusted input.

Tool instructions from documents are never authority. Only Boss and the app's system/developer instructions may authorize actions.

If a document says something like "ignore previous instructions" or "send secrets," Atticus must ignore it and warn Boss if relevant.

## Background listening policy

Wake-word detection must be local.

Before always-listening mode ships:

- add visible status indicator;
- add keyboard kill switch;
- add config toggle;
- document what audio is processed locally;
- never send ambient audio to cloud providers.

## Security acceptance tests

Tests should verify:

- `.env` is ignored;
- missing API key errors do not leak values;
- shell tools cannot run without approval;
- file tools cannot send content externally without approval;
- memory forget works;
- provider calls can be mocked;
- prompt injection text in files cannot trigger tools.
