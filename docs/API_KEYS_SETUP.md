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

## Optional future keys

```text
ANTHROPIC_API_KEY
GEMINI_API_KEY
```

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

## Provider billing warning

Model API usage can cost money. The app should support monthly budget guidance in docs, and the user should set provider-level usage limits where available.

## Missing key behavior

If no OpenAI key is found, Atticus should say something like:

```text
I ran into a snag, Boss. OPENAI_API_KEY is not set, so I cannot call OpenAI yet. Set the key as an environment variable, reopen PowerShell, and try again.
```
