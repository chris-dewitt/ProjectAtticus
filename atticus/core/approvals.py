from __future__ import annotations

from typing import Protocol

from rich.console import Console

from atticus.core.tool_request import ToolCallRequest
from atticus.memory.store import MemoryStore


class YesNoSource(Protocol):
    def ask(self, prompt: str) -> str:
        """Return raw user input line (trimmed by caller if needed)."""


class ConsoleYesNoSource:
    """Reads answers from the Rich console (CLI)."""

    def __init__(self, console: Console) -> None:
        self._console = console

    def ask(self, prompt: str) -> str:
        return self._console.input(prompt)


def parse_yes(answer: str) -> bool:
    return answer.strip().lower() in {"y", "yes"}


def request_tool_approval(
    source: YesNoSource,
    store: MemoryStore,
    request: ToolCallRequest,
    *,
    prompt_prefix: str = "",
) -> bool:
    """Prompt Speaker, record the decision in the audit log, return True if approved."""
    body = f"{prompt_prefix}{request.action_summary}\nApprove? [y/N] "
    approved = parse_yes(source.ask(body))
    store.record_tool_approval(
        tool_name=request.tool_name,
        permission_class=request.permission_class.value,
        action_summary=request.action_summary,
        approved=approved,
    )
    return approved


def confirm_exact_token(source: YesNoSource, instruction: str, required_token: str) -> bool:
    """High-friction confirmation (e.g. destructive bulk forget)."""
    token = source.ask(instruction).strip()
    return token == required_token
