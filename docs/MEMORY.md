# Memory Design — ProjectAtticus

## Memory principles

Atticus should remember useful context, but not hoard private data.

Memory is enabled by default because Boss requested default memory. However, raw conversations are not stored by default. Store summaries and preferences.

## Memory types

### Preferences

Examples:

- preferred name: Boss;
- preferred provider: OpenAI;
- project repo path;
- voice response preference;
- privacy preferences.

### Project summaries

Examples:

- ProjectAtticus purpose;
- current milestone;
- architecture decisions;
- known bugs.

### Conversation summaries

Short local summaries of important sessions.

### Tool approval history

Records that an action was requested and approved/denied. Do not store excessive input content.

## Minimum commands

- `/memory`: list memory summary.
- `/remember <text>`: save a memory.
- `/forget <query>`: forget matching memories.
- `/what-do-you-remember <query>`: inspect memory.

Natural language equivalents:

- "Atticus, remember that..."
- "Atticus, forget that..."
- "Atticus, what do you remember about...?"

## Suggested schema

```sql
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    source TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE conversation_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,
    mode TEXT,
    provider TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE tool_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    permission_class TEXT NOT NULL,
    action_summary TEXT NOT NULL,
    approved INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
```

## Forget behavior

Forget should mark matching records deleted or remove them from active retrieval. Prefer soft delete first for auditability, but provide hard delete later.

When forgetting, Atticus should confirm what was forgotten.

## Sensitive memory handling

Do not store health, legal, financial, political, religious, or intimate details unless Boss explicitly requests it. If such a detail appears incidental, summarize around it rather than storing it directly.

## Future vector memory

Do not start with vector memory. Add it only after the SQLite summary store works.

Future options:

- SQLite FTS5;
- Chroma;
- LanceDB;
- local embedding model;
- provider embedding with explicit consent.
