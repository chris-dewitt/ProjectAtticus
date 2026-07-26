# Tool Design — ProjectAtticus

## Tool principle

Atticus may eventually act on The Speaker's laptop, but all action must be permissioned.

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

## Tool interface

Suggested base model:

```python
from dataclasses import dataclass
from enum import Enum

class PermissionClass(str, Enum):
    SAFE_READ = "safe_read"
    SENSITIVE_READ = "sensitive_read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL_SEND = "external_send"
    EXECUTE = "execute"

@dataclass
class ToolCallRequest:
    tool_name: str
    permission_class: PermissionClass
    action_summary: str
    inputs: dict
    external_data: bool = False
    destructive: bool = False

@dataclass
class ToolCallResult:
    ok: bool
    summary: str
    data: dict | None = None
    error: str | None = None
```

## Permission gate

All tools go through a permission gate. Tools should not ask for approval themselves; the permission gate should handle approvals consistently.

## Tool implementation order

### v0.1

- Tool interface only.
- Permission gate skeleton.
- No dangerous actions.

### v0.2

- Local memory commands.
- Safe file listing inside approved repo path.

### v0.3

- File search.
- Markdown note creation with approval.
- PDF text extraction with approval.

### v0.4

- Shell command proposal with approval.
- Code edit proposal with diff.

### Later

- Gmail draft/send.
- Calendar read/write.
- GitHub issues/PRs.
- Web browsing.

## Confirmation copy examples

### File read to cloud provider

```text
The Speaker, I need your say-so before I send file content outside the laptop.

Provider: OpenAI
File: C:\Users\DELL\Documents\GitHub\ProjectAtticus\docs\notes.pdf
Purpose: summarize the document
Payload: extracted text excerpt, not the full PDF binary

Approve? [y/N]
```

### Shell command

```text
The Speaker, Atticus would like to run this command:

Command: pytest
Working directory: C:\Users\DELL\Documents\GitHub\ProjectAtticus
Reason: verify the latest code changes
Risk: low, but it executes local code

Approve? [y/N]
```

### File edit

```text
The Speaker, Atticus would like to edit:
C:\Users\DELL\Documents\GitHub\ProjectAtticus\atticus\core\config.py

Summary: add environment variable loading for OPENAI_API_KEY.

Approve? [y/N]
```
