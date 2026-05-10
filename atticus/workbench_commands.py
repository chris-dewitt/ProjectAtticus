"""Phase 6–8 CLI tool commands (files, git, GitHub, integration stubs)."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from atticus.core.approvals import ConsoleYesNoSource, request_tool_approval
from atticus.core.config import AppConfig
from atticus.core.errors import AtticusError, PermissionDenied, WorkspaceError
from atticus.core.permissions import PermissionClass
from atticus.core.router import ProviderRouter
from atticus.core.tool_request import ToolCallRequest
from atticus.integrations import deferred
from atticus.integrations.github_public import fetch_recent_issue_titles, github_token_from_config
from atticus.memory.store import MemoryStore
from atticus.services.git_runner import run_git
from atticus.services.paths import approved_roots, resolve_under_approved
from atticus.services import workspace_files as wf


@dataclass
class ToolCliContext:
    cfg: AppConfig
    repo_root: Path
    memory: MemoryStore
    yesno: ConsoleYesNoSource
    router: ProviderRouter
    mode: str
    persona_core: str
    console: Console


def _ensure_file_tools(ctx: ToolCliContext) -> None:
    if not ctx.cfg.tools.enabled or not ctx.cfg.tools.files.enabled:
        raise WorkspaceError("Enable tools.enabled and tools.files.enabled in config for file commands.")


def _ensure_shell(ctx: ToolCliContext) -> None:
    if not ctx.cfg.tools.enabled or not ctx.cfg.tools.shell.enabled:
        raise WorkspaceError("Enable tools.enabled and tools.shell.enabled for git commands.")


def _ensure_github(ctx: ToolCliContext) -> None:
    if not ctx.cfg.tools.enabled or not ctx.cfg.tools.github.enabled:
        raise WorkspaceError("Enable tools.enabled and tools.github.enabled for GitHub commands.")


def _ensure_browser(ctx: ToolCliContext) -> None:
    if not ctx.cfg.tools.enabled or not ctx.cfg.tools.browser.enabled:
        raise WorkspaceError("Enable tools.enabled and tools.browser.enabled to open URLs from Atticus.")


def handle_tool_slash(cmd: str, args: list[str], ctx: ToolCliContext) -> bool:
    """Return True if this module handled the slash command."""
    try:
        if cmd == "/integrations":
            ctx.console.print(deferred.gmail_status())
            ctx.console.print(deferred.calendar_status())
            ctx.console.print(deferred.browser_status())
            return True

        if cmd == "/file" and args:
            sub = args[0].lower()
            if sub == "read" and len(args) >= 2:
                _ensure_file_tools(ctx)
                path = resolve_under_approved(ctx.cfg, " ".join(args[1:]))
                text = wf.read_text(path, max_bytes=ctx.cfg.tools.files.max_read_bytes)
                ctx.console.print(f"[dim]{path}[/dim]\n{text[:8000]}")
                if len(text) > 8000:
                    ctx.console.print("[dim](output truncated in console; full text read from disk)[/dim]")
                return True
            if sub == "search" and len(args) >= 2:
                _ensure_file_tools(ctx)
                glob_pat = args[1]
                roots = approved_roots(ctx.cfg)
                hits = wf.search_names(roots, glob_pat, limit=ctx.cfg.tools.files.max_search_files)
                if not hits:
                    ctx.console.print("No matching files.")
                else:
                    for p in hits[:200]:
                        ctx.console.print(str(p))
                    if len(hits) > 200:
                        ctx.console.print(f"[dim]…and {len(hits) - 200} more[/dim]")
                return True
            if sub == "write" and len(args) >= 3:
                _ensure_file_tools(ctx)
                path = resolve_under_approved(ctx.cfg, args[1])
                content = " ".join(args[2:])
                req = ToolCallRequest(
                    tool_name="file_write",
                    permission_class=PermissionClass.WRITE,
                    action_summary=f"Write text to {path}",
                )
                if ctx.cfg.tools.files.require_confirmation_for_edits and not request_tool_approval(
                    ctx.yesno, ctx.memory, req
                ):
                    ctx.console.print("[dim]Write cancelled.[/dim]")
                    return True
                wf.write_text(path, content + ("\n" if not content.endswith("\n") else ""), append=False)
                ctx.console.print(f"[green]Wrote[/green] {path}")
                return True

        if cmd == "/code-search" and args:
            _ensure_file_tools(ctx)
            pattern = " ".join(args).strip()
            roots = approved_roots(ctx.cfg)
            req = ToolCallRequest(
                tool_name="code_search",
                permission_class=PermissionClass.SENSITIVE_READ,
                action_summary=f"Search file contents for regex: {pattern!r} under approved_paths",
            )
            if not request_tool_approval(ctx.yesno, ctx.memory, req):
                ctx.console.print("[dim]Search cancelled.[/dim]")
                return True
            hits = wf.search_content(
                roots,
                pattern,
                limit_files=ctx.cfg.tools.files.max_search_files,
                max_bytes_per_file=min(200_000, ctx.cfg.tools.files.max_read_bytes),
                glob_filter="*.py",
            )
            if not hits:
                ctx.console.print("No matches in *.py files (narrow filter). Try a simpler pattern.")
            else:
                for p, line in hits[:100]:
                    ctx.console.print(f"{p}: {line}")
            return True

        if cmd == "/git" and args:
            _ensure_shell(ctx)
            inner = " ".join(args)
            req = ToolCallRequest(
                tool_name="git",
                permission_class=PermissionClass.EXECUTE,
                action_summary=f"Run read-only git: {inner}",
            )
            if ctx.cfg.tools.shell.require_confirmation and not request_tool_approval(ctx.yesno, ctx.memory, req):
                ctx.console.print("[dim]git cancelled.[/dim]")
                return True
            out = run_git(inner, cwd=ctx.repo_root)
            ctx.console.print(out or "(no output)")
            return True

        if cmd in {"/gh", "/github"} and args and args[0].lower() == "issues" and len(args) >= 3:
            _ensure_github(ctx)
            owner, repo = args[1], args[2]
            tok = github_token_from_config(ctx.cfg.tools.github.token_env)
            titles = fetch_recent_issue_titles(owner, repo, token=tok)
            for line in titles:
                ctx.console.print(line)
            return True

        if cmd == "/open" and args:
            _ensure_browser(ctx)
            url = args[0].strip()
            if not url.lower().startswith(("https://", "http://")):
                ctx.console.print("Only http(s) URLs are allowed.")
                return True
            if ctx.cfg.privacy.ask_before_open_url:
                req = ToolCallRequest(
                    tool_name="open_url",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=f"Open URL in default browser: {url}",
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Open cancelled.[/dim]")
                    return True
            webbrowser.open(url)
            ctx.console.print(f"[dim]Opened[/dim] {url}")
            return True

        if cmd == "/summarize" and len(args) >= 1:
            _ensure_file_tools(ctx)
            path = resolve_under_approved(ctx.cfg, " ".join(args))
            max_b = ctx.cfg.tools.files.max_read_bytes
            if path.suffix.lower() == ".pdf":
                excerpt = wf.extract_pdf_text(path, max_bytes=max_b)
            else:
                excerpt = wf.read_text(path, max_bytes=max_b)
            if len(excerpt) > 24_000:
                excerpt = excerpt[:24_000] + "\n…(truncated before model)"
            if ctx.cfg.privacy.ask_before_sending_files_to_cloud:
                req = ToolCallRequest(
                    tool_name="summarize_file",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=f"Send excerpt of {path} ({len(excerpt)} chars) to LLM for summary",
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Summarize cancelled.[/dim]")
                    return True
            head = ctx.persona_core.split("\n---\n", 1)[0] if "---" in ctx.persona_core else ctx.persona_core
            sys_prompt = head[:4000] + "\nBoss asked for a concise summary of a local file excerpt. Stay factual."
            msgs = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"File: {path}\n\n---\n\n{excerpt}"},
            ]
            try:
                reply = ctx.router.generate(msgs, mode=ctx.mode)
            except AtticusError as exc:
                ctx.console.print(f"[red]{exc}[/red]")
                return True
            ctx.console.print(reply)
            return True

    except WorkspaceError as exc:
        ctx.console.print(f"[red]{exc}[/red]")
        return True
    except PermissionDenied as exc:
        ctx.console.print(f"[red]{exc}[/red]")
        return True
    except Exception as exc:
        ctx.console.print(f"[red]{exc}[/red]")
        return True

    return False
