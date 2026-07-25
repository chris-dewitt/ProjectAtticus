"""Phase 6–8 CLI tool commands (files, git, GitHub, integration stubs)."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from atticus.core.approvals import ConsoleYesNoSource, confirm_exact_token, request_tool_approval
from atticus.core.config import AppConfig
from atticus.core.errors import AtticusError, PermissionDenied, WorkspaceError
from atticus.core.permissions import PermissionClass
from atticus.core.router import ProviderRouter
from atticus.core.tool_request import ToolCallRequest
from atticus.integrations import deferred
from atticus.integrations import gmail as gmail_api
from atticus.integrations import github_public as gh_api
from atticus.memory.store import MemoryStore
from atticus.services.git_runner import run_git
from atticus.services.paths import approved_roots, resolve_under_approved
from atticus.services import workspace_files as wf

_GMAIL_SEND_TOKEN = "SEND"


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


def _ensure_email(ctx: ToolCliContext) -> None:
    if not ctx.cfg.tools.enabled or not ctx.cfg.tools.email.enabled:
        raise WorkspaceError("Enable tools.enabled and tools.email.enabled for Gmail commands.")


def _gmail_paths(ctx: ToolCliContext) -> tuple[Path | None, Path]:
    secrets = gmail_api.resolve_path(ctx.cfg.tools.email.gmail_client_secrets_path)
    token = gmail_api.resolve_path(ctx.cfg.tools.email.gmail_token_path) or Path("data/gmail_token.json").resolve()
    return secrets, token


def _gmail_service(ctx: ToolCliContext, *, scopes: list[str]):
    secrets, token = _gmail_paths(ctx)
    if secrets is None:
        raise WorkspaceError(
            "Set tools.email.gmail_client_secrets_path to your Google OAuth Desktop client JSON."
        )
    creds = gmail_api.load_credentials(client_secrets=secrets, token_path=token, scopes=scopes)
    return gmail_api.build_service(creds)


def handle_tool_slash(cmd: str, args: list[str], ctx: ToolCliContext) -> bool:
    """Return True if this module handled the slash command."""
    try:
        if cmd == "/integrations":
            ctx.console.print(deferred.gmail_status())
            ctx.console.print(deferred.calendar_status())
            ctx.console.print(deferred.browser_status())
            return True

        if cmd == "/gmail":
            _ensure_email(ctx)
            if not args:
                ctx.console.print(
                    "Usage: /gmail status | auth [readonly|compose] | inbox [n] | "
                    "read <id> | draft <to> <subject> || <body> | send <draft_id>"
                )
                return True
            sub = args[0].lower()
            secrets, token = _gmail_paths(ctx)

            if sub == "status":
                ctx.console.print(
                    gmail_api.status_text(
                        client_secrets=secrets,
                        token_path=token,
                        deps_ok=gmail_api.gmail_deps_installed(),
                    )
                )
                return True

            if sub == "auth":
                mode = args[1].lower() if len(args) >= 2 else "readonly"
                if mode not in {"readonly", "compose"}:
                    ctx.console.print("Usage: /gmail auth [readonly|compose]")
                    return True
                scopes = (
                    list(ctx.cfg.tools.email.gmail_scopes_readonly)
                    if mode == "readonly"
                    else list(ctx.cfg.tools.email.gmail_scopes_compose)
                )
                req = ToolCallRequest(
                    tool_name="gmail_auth",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=(
                        f"Run Google OAuth ({mode}) in the local browser and cache a token at {token}. "
                        "No email content is sent to Atticus cloud providers in this step."
                    ),
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Gmail auth cancelled.[/dim]")
                    return True
                _gmail_service(ctx, scopes=scopes)
                ctx.console.print(f"[green]Gmail authenticated[/green] ({mode}). Token cached locally.")
                return True

            if sub == "inbox":
                limit = int(ctx.cfg.tools.email.gmail_inbox_limit)
                if len(args) >= 2:
                    try:
                        limit = int(args[1])
                    except ValueError:
                        ctx.console.print("Usage: /gmail inbox [n]")
                        return True
                req = ToolCallRequest(
                    tool_name="gmail_inbox",
                    permission_class=PermissionClass.SENSITIVE_READ,
                    action_summary=f"Read up to {limit} Gmail INBOX message headers/snippets via Google API.",
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Inbox cancelled.[/dim]")
                    return True
                service = _gmail_service(ctx, scopes=list(ctx.cfg.tools.email.gmail_scopes_readonly))
                rows = gmail_api.list_inbox(service, limit=limit)
                if not rows:
                    ctx.console.print("Inbox is empty (or no messages returned).")
                    return True
                for row in rows:
                    ctx.console.print(
                        f"[bold]{row.id}[/bold] | {row.date} | {row.from_addr}\n"
                        f"  {row.subject}\n"
                        f"  {row.snippet}"
                    )
                return True

            if sub == "read" and len(args) >= 2:
                mid = args[1]
                req = ToolCallRequest(
                    tool_name="gmail_read",
                    permission_class=PermissionClass.SENSITIVE_READ,
                    action_summary=f"Fetch Gmail message body for id {mid} (local display only).",
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Read cancelled.[/dim]")
                    return True
                service = _gmail_service(ctx, scopes=list(ctx.cfg.tools.email.gmail_scopes_readonly))
                header, body = gmail_api.read_message(service, mid)
                ctx.console.print(
                    f"[bold]{header.subject}[/bold]\nFrom: {header.from_addr}\nDate: {header.date}\n\n{body}"
                )
                return True

            if sub == "draft" and len(args) >= 2:
                joined = " ".join(args[1:]).strip()
                if "||" not in joined:
                    ctx.console.print(
                        "Usage: /gmail draft <to> <subject> || <body>\n"
                        "Example: /gmail draft boss@example.com Quick hello || Just checking in."
                    )
                    return True
                head, body = joined.split("||", 1)
                head_parts = head.strip().split(None, 1)
                if len(head_parts) < 2:
                    ctx.console.print("Draft needs <to> and <subject> before ||.")
                    return True
                to_addr, subject = head_parts[0], head_parts[1].strip()
                body_text = body.strip()
                req = ToolCallRequest(
                    tool_name="gmail_draft",
                    permission_class=PermissionClass.WRITE,
                    action_summary=(
                        f"Create a Gmail draft to {to_addr!r} subject {subject!r} "
                        f"({len(body_text)} chars). Does not send."
                    ),
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Draft cancelled.[/dim]")
                    return True
                service = _gmail_service(ctx, scopes=list(ctx.cfg.tools.email.gmail_scopes_compose))
                draft_id = gmail_api.create_draft(service, to=to_addr, subject=subject, body=body_text)
                ctx.console.print(f"[green]Draft created[/green] id=[bold]{draft_id}[/bold]. Use /gmail send {draft_id}")
                return True

            if sub == "send" and len(args) >= 2:
                draft_id = args[1]
                if not ctx.cfg.tools.email.require_confirmation_for_send:
                    raise WorkspaceError(
                        "Refusing to send: tools.email.require_confirmation_for_send must remain true."
                    )
                req = ToolCallRequest(
                    tool_name="gmail_send",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=f"SEND Gmail draft {draft_id} to the recipient (irreversible).",
                    external_data=True,
                    destructive=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Send cancelled.[/dim]")
                    return True
                if not confirm_exact_token(
                    ctx.yesno,
                    "Type SEND in capitals to confirm the message leaves your account: ",
                    _GMAIL_SEND_TOKEN,
                ):
                    ctx.console.print("[dim]Send cancelled (token mismatch).[/dim]")
                    return True
                service = _gmail_service(ctx, scopes=list(ctx.cfg.tools.email.gmail_scopes_compose))
                sent_id = gmail_api.send_draft(service, draft_id)
                ctx.console.print(f"[green]Sent[/green] message id=[bold]{sent_id}[/bold].")
                return True

            ctx.console.print(
                "Usage: /gmail status | auth [readonly|compose] | inbox [n] | "
                "read <id> | draft <to> <subject> || <body> | send <draft_id>"
            )
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

        if cmd in {"/gh", "/github"} and args:
            _ensure_github(ctx)
            sub = args[0].lower()
            env_name = ctx.cfg.tools.github.token_env
            tok = gh_api.github_token_from_config(env_name)

            if sub == "me":
                token = gh_api.require_github_token(tok, token_env=env_name, for_action="/gh me")
                req = ToolCallRequest(
                    tool_name="github_user",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary="Call GitHub GET /user with your token (login + display name only).",
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Cancelled.[/dim]")
                    return True
                login, name = gh_api.fetch_authenticated_profile(token)
                ctx.console.print(f"[bold]login:[/bold] {login}")
                if name:
                    ctx.console.print(f"[bold]name:[/bold] {name}")
                return True

            if sub == "repos":
                token = gh_api.require_github_token(tok, token_env=env_name, for_action="/gh repos")
                lim = int(ctx.cfg.tools.github.repo_list_limit)
                req = ToolCallRequest(
                    tool_name="github_repos",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=f"Call GitHub GET /user/repos (up to {lim} repos, affiliation owner/collaborator/org).",
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Cancelled.[/dim]")
                    return True
                for line in gh_api.fetch_authenticated_repos(token, limit=lim):
                    ctx.console.print(line)
                return True

            if sub == "prs" and len(args) >= 3:
                owner, repo = args[1], args[2]
                state = args[3].lower() if len(args) >= 4 else "open"
                if state not in {"open", "closed", "all"}:
                    state = "open"
                lim = int(ctx.cfg.tools.github.pr_list_limit)
                req = ToolCallRequest(
                    tool_name="github_pulls",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=f"Call GitHub GET /repos/{owner}/{repo}/pulls (state={state}, up to {lim}).",
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Cancelled.[/dim]")
                    return True
                for line in gh_api.fetch_pull_requests(owner, repo, token=tok, limit=lim, state=state):
                    ctx.console.print(line)
                return True

            if sub == "issues" and len(args) >= 3:
                owner, repo = args[1], args[2]
                for line in gh_api.fetch_recent_issue_titles(owner, repo, token=tok):
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
