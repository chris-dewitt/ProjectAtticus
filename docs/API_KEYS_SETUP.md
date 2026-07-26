# API Keys Setup — ProjectAtticus

## Important rules

Never commit API keys to git.

Never paste API keys into source files, screenshots, GitHub issues, prompts, or documentation.

Use environment variables for v0.1. Later, Atticus can support Windows Credential Manager through Python `keyring`.

## Required key for first milestone

Only OpenAI is required for v0.1.

Environment variable:

```text
OPENAI_API_KEY
```

## Optional provider keys

Claude and Gemini are implemented. Install SDKs with:

```powershell
pip install -e ".[providers]"
```

Environment variables:

```text
ANTHROPIC_API_KEY
GEMINI_API_KEY
```

Keys resolve through `get_credential` (environment / `.env` first, then optional OS keyring via `pip install -e ".[secrets]"`).

## OpenAI API key setup

1. Create or log into an OpenAI platform account.
2. Create a project for ProjectAtticus.
3. Create a new secret key under that project.
4. Save the key somewhere secure when it is shown.
5. Set it as a Windows user environment variable.
6. Add billing/usage limits as appropriate.

PowerShell / CMD-compatible approach from Windows command prompt:

```cmd
setx OPENAI_API_KEY "your_key_here"
```

Then close and reopen the terminal.

Validate in PowerShell:

```powershell
$env:OPENAI_API_KEY
```

Do not paste the output into chat or commit it anywhere.

## Anthropic API key setup

1. Create or log into an Anthropic Console account.
2. Create an API key.
3. Set it as:

```cmd
setx ANTHROPIC_API_KEY "your_key_here"
```

Then close and reopen the terminal.

## Gemini API key setup

1. Go to Google AI Studio.
2. Create or view a Gemini API key.
3. Set it as:

```cmd
setx GEMINI_API_KEY "your_key_here"
```

Then close and reopen the terminal.

## `.env` local development option

The app may also support `.env` for local development:

```text
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

`.env` must be listed in `.gitignore`.

## `.env.example`

`.env.example` should contain placeholders only:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
```

## Google OAuth (Gmail + Calendar; not an API key in `.env`)

Gmail and Calendar share the Google API optional extra and can share one OAuth Desktop client JSON:

1. `pip install -e ".[gmail]"`
2. Create an OAuth client (Desktop) in Google Cloud Console; enable **Gmail API** and/or **Google Calendar API**.
3. Download the client secrets JSON somewhere outside git (or a gitignored path).
4. Set `tools.enabled: true` and the relevant tool flags in `config/atticus.yaml`:
   - Gmail: `tools.email.enabled` + `tools.email.gmail_client_secrets_path`
   - Calendar: `tools.calendar.enabled` + `tools.calendar.client_secrets_path` (or leave null to reuse the Gmail secrets path)
5. Run `atticus`, then:
   - `/gmail auth readonly` (or `compose` for drafts/send)
   - `/cal auth readonly` (or `write` for create/delete)
6. Tokens cache under `data/` by default (`gmail_token.json`, `calendar_token.json`) — gitignored.

Gmail send requires y/N plus typing `SEND`. Calendar create/delete require y/N plus typing `CREATE` / `DELETE`. Never commit client secrets or tokens.

## Provider billing warning

Model API usage can cost money. The app should support monthly budget guidance in docs, and the user should set provider-level usage limits where available.

## Missing key behavior

If no OpenAI key is found, Atticus should say something like:

```text
I ran into a snag, Boss. OPENAI_API_KEY is not set, so I cannot call OpenAI yet. Set the key as an environment variable, reopen PowerShell, and try again.
```
