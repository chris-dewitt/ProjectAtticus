# Repo Setup — ProjectAtticus

## Target repo location

```text
C:\Users\DELL\Documents\GitHub\ProjectAtticus
```

## Suggested first setup commands

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

## Git setup

```powershell
git status
git add README.md AGENTS.md docs .cursor .env.example config prompts .gitignore
git commit -m "Add ProjectAtticus agent instructions"
```

Do not commit `.env`.

## Recommended `.gitignore`

See root `.gitignore` in this instruction pack.

## API keys

See `docs/API_KEYS_SETUP.md`.

## Cursor usage

Open the ProjectAtticus folder in Cursor. Cursor should read rules from `.cursor/rules/*.mdc`.

Use the prompts in `docs/CURSOR_TASKS.md`.

## Codex usage

Codex reads `AGENTS.md` before working. Use the prompts in `docs/CODEX_TASKS.md`.
