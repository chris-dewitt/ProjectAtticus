# Data Card — ProjectAtticus

Status: Local-first data inventory  
Related: `docs/MEMORY.md`, `docs/SECURITY.md`, `SPEC.md` §9

## Data the product stores locally (Track A)

| Store | Location (typical) | Contents | Default |
|-------|--------------------|----------|---------|
| SQLite memory | `data/atticus_memory.sqlite3` | Notes, preferences, conversation summaries, tool approval audit rows | Enabled when `privacy.memory_enabled` |
| Config | `config/atticus.yaml` (optional, gitignored) | Machine-specific settings | Example config used if missing |
| Env secrets | `.env` (gitignored) | API tokens | Placeholders only in `.env.example` |

Raw chat transcripts are **not** stored by default (`privacy.store_raw_conversations: false`).

## Data not collected for the open repo

- No third-party production datasets are bundled.
- Tests use synthetic fixtures and mocks only.
- No confidential employer information, private mail, or personal health/legal/financial dumps belong in the repository.

## Provenance expectations (Track B target)

When Track B file/research tools mature, source-derived records should retain source URI, retrieval time, content checksum, license/usage notes, and parser version (`SPEC.md` §6). Track A file tools today read approved paths but do not yet persist a full provenance artifact model.

## Retention and deletion

- Soft-delete for memory notes (`deleted_at`)
- `/forget` flows and high-friction confirmation for bulk delete
- Boss can clear preferences and summaries via CLI commands

Document any future cloud retention separately before enabling hosted storage.

## License and contribution data rule

Use only public, synthetic, or explicitly licensed data in fixtures, demos, and docs. Choose and document a project license before accepting external contributions (see portfolio bootstrap guidance).
