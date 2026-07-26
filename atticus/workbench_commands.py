"""Phase 6–8 CLI tool commands (files, git, GitHub, calendar, browse, patch/test)."""

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
from atticus.integrations import calendar as cal_api
from atticus.integrations import deferred
from atticus.integrations import gmail as gmail_api
from atticus.integrations import github_public as gh_api
from atticus.memory.store import MemoryStore
from atticus.services import patch_apply as patch_svc
from atticus.services import test_runner as test_svc
from atticus.services import web_browse as browse_svc
from atticus.services.git_runner import run_git
from atticus.services.paths import approved_roots, resolve_under_approved
from atticus.services import workspace_files as wf

_GMAIL_SEND_TOKEN = "SEND"
_CAL_CREATE_TOKEN = "CREATE"
_CAL_DELETE_TOKEN = "DELETE"


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


def _ensure_calendar(ctx: ToolCliContext) -> None:
    if not ctx.cfg.tools.enabled or not ctx.cfg.tools.calendar.enabled:
        raise WorkspaceError("Enable tools.enabled and tools.calendar.enabled for calendar commands.")


def _calendar_paths(ctx: ToolCliContext) -> tuple[Path | None, Path]:
    secrets_raw = ctx.cfg.tools.calendar.client_secrets_path or ctx.cfg.tools.email.gmail_client_secrets_path
    secrets = cal_api.resolve_path(secrets_raw)
    token = cal_api.resolve_path(ctx.cfg.tools.calendar.token_path) or Path("data/calendar_token.json").resolve()
    return secrets, token


def _calendar_service(ctx: ToolCliContext, *, scopes: list[str]):
    secrets, token = _calendar_paths(ctx)
    if secrets is None:
        raise WorkspaceError(
            "Set tools.calendar.client_secrets_path (or tools.email.gmail_client_secrets_path) "
            "to your Google OAuth Desktop client JSON."
        )
    creds = cal_api.authenticate(client_secrets=secrets, token_path=token, scopes=scopes)
    return cal_api.calendar_service(creds)


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
                        "Example: /gmail draft speaker@example.com Quick hello || Just checking in."
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

        if cmd in {"/cal", "/calendar"}:
            _ensure_calendar(ctx)
            if not args:
                ctx.console.print(
                    "Usage: /cal status | auth [readonly|write] | list [days] | "
                    "create <summary> || <start> || <end> [|| <description>] | delete <event_id>"
                )
                return True
            sub = args[0].lower()
            secrets, token = _calendar_paths(ctx)
            if sub == "status":
                ctx.console.print(
                    cal_api.status_text(
                        client_secrets=secrets,
                        token_path=token,
                        deps_ok=cal_api.calendar_deps_installed(),
                    )
                )
                return True
            if sub == "auth":
                mode = args[1].lower() if len(args) >= 2 else "readonly"
                if mode not in {"readonly", "write"}:
                    ctx.console.print("Usage: /cal auth [readonly|write]")
                    return True
                scopes = (
                    list(ctx.cfg.tools.calendar.scopes_readonly)
                    if mode == "readonly"
                    else list(ctx.cfg.tools.calendar.scopes_write)
                )
                req = ToolCallRequest(
                    tool_name="calendar_auth",
                    permission_class=PermissionClass.EXTERNAL_SEND,
                    action_summary=(
                        f"Run Google Calendar OAuth ({mode}) and cache a token at {token}."
                    ),
                    external_data=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Calendar auth cancelled.[/dim]")
                    return True
                _calendar_service(ctx, scopes=scopes)
                ctx.console.print(f"[green]Calendar authenticated[/green] ({mode}).")
                return True
            if sub == "list":
                days = int(ctx.cfg.tools.calendar.list_days)
                if len(args) >= 2:
                    try:
                        days = int(args[1])
                    except ValueError:
                        ctx.console.print("Usage: /cal list [days]")
                        return True
                req = ToolCallRequest(
                    tool_name="calendar_list",
                    permission_class=PermissionClass.SENSITIVE_READ,
                    action_summary=f"List upcoming Google Calendar events for {days} day(s).",
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Calendar list cancelled.[/dim]")
                    return True
                service = _calendar_service(ctx, scopes=list(ctx.cfg.tools.calendar.scopes_readonly))
                events = cal_api.list_events(
                    service,
                    calendar_id=ctx.cfg.tools.calendar.calendar_id,
                    days=days,
                    max_events=int(ctx.cfg.tools.calendar.max_events),
                )
                if not events:
                    ctx.console.print("No upcoming events in that window.")
                    return True
                for ev in events:
                    loc = f" @ {ev.location}" if ev.location else ""
                    ctx.console.print(
                        f"[bold]{ev.id}[/bold] | {ev.start} → {ev.end}\n  {ev.summary}{loc}"
                    )
                return True
            if sub == "create" and len(args) >= 2:
                joined = " ".join(args[1:]).strip()
                parts = [p.strip() for p in joined.split("||")]
                if len(parts) < 3:
                    ctx.console.print(
                        "Usage: /cal create <summary> || <start ISO> || <end ISO> [|| <description>]\n"
                        "Example: /cal create Dentist || 2026-08-01T15:00:00-04:00 || 2026-08-01T16:00:00-04:00"
                    )
                    return True
                summary, start_iso, end_iso = parts[0], parts[1], parts[2]
                description = parts[3] if len(parts) >= 4 else ""
                if not ctx.cfg.tools.calendar.require_confirmation_for_write:
                    raise WorkspaceError(
                        "Refusing write: tools.calendar.require_confirmation_for_write must remain true."
                    )
                req = ToolCallRequest(
                    tool_name="calendar_create",
                    permission_class=PermissionClass.WRITE,
                    action_summary=(
                        f"CREATE calendar event {summary!r} from {start_iso} to {end_iso} "
                        f"on {ctx.cfg.tools.calendar.calendar_id}."
                    ),
                    destructive=False,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Create cancelled.[/dim]")
                    return True
                if not confirm_exact_token(
                    ctx.yesno,
                    "Type CREATE in capitals to confirm the calendar write: ",
                    _CAL_CREATE_TOKEN,
                ):
                    ctx.console.print("[dim]Create cancelled (token mismatch).[/dim]")
                    return True
                service = _calendar_service(ctx, scopes=list(ctx.cfg.tools.calendar.scopes_write))
                ev = cal_api.create_event(
                    service,
                    calendar_id=ctx.cfg.tools.calendar.calendar_id,
                    summary=summary,
                    start_iso=start_iso,
                    end_iso=end_iso,
                    description=description,
                )
                ctx.console.print(f"[green]Created[/green] id=[bold]{ev.id}[/bold] {ev.summary} ({ev.start} → {ev.end})")
                return True
            if sub == "delete" and len(args) >= 2:
                event_id = args[1]
                if not ctx.cfg.tools.calendar.require_confirmation_for_write:
                    raise WorkspaceError(
                        "Refusing write: tools.calendar.require_confirmation_for_write must remain true."
                    )
                req = ToolCallRequest(
                    tool_name="calendar_delete",
                    permission_class=PermissionClass.DESTRUCTIVE,
                    action_summary=f"DELETE calendar event id {event_id}",
                    destructive=True,
                )
                if not request_tool_approval(ctx.yesno, ctx.memory, req):
                    ctx.console.print("[dim]Delete cancelled.[/dim]")
                    return True
                if not confirm_exact_token(
                    ctx.yesno,
                    "Type DELETE in capitals to confirm removing the event: ",
                    _CAL_DELETE_TOKEN,
                ):
                    ctx.console.print("[dim]Delete cancelled (token mismatch).[/dim]")
                    return True
                service = _calendar_service(ctx, scopes=list(ctx.cfg.tools.calendar.scopes_write))
                cal_api.delete_event(
                    service,
                    calendar_id=ctx.cfg.tools.calendar.calendar_id,
                    event_id=event_id,
                )
                ctx.console.print(f"[green]Deleted[/green] event {event_id}.")
                return True
            ctx.console.print(
                "Usage: /cal status | auth [readonly|write] | list [days] | "
                "create <summary> || <start> || <end> [|| <description>] | delete <event_id>"
            )
            return True

        if cmd == "/file" and args:
            sub = args[0].lower()
            if sub == "read" and len(args) >= 2:
                _ensure_file_tools(ctx)
                path = resolve_under_approved(ctx.cfg, " ".join(args[1:]))
                text = wf.read_text(path, max_bytes=ctx.cfg.tools.files.max_read_bytes)
                from atticus.services import citations as cite_svc

                cite_dir = cite_svc.citation_dir_from_config(ctx.cfg.tools.browser.citation_dir)
                record = cite_svc.from_local_file(
                    path=path,
                    text=text,
                    max_bytes=ctx.cfg.tools.files.max_read_bytes,
                    tool_name="file_read",
                )
                saved = cite_svc.save_record(record, cite_dir)
                ctx.console.print(f"[dim]{path}[/dim]\n{text[:8000]}")
                if len(text) > 8000:
                    ctx.console.print("[dim](output truncated in console; full text read from disk)[/dim]")
                ctx.console.print(f"[dim]Citation:[/dim] {saved.id}  →  {saved.saved_path}")
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
                from atticus.services import citations as cite_svc

                cite_dir = cite_svc.citation_dir_from_config(ctx.cfg.tools.browser.citation_dir)
                for p, line in hits[:100]:
                    record = cite_svc.from_code_search(path=p, line=line, pattern=pattern)
                    saved = cite_svc.save_record(record, cite_dir)
                    ctx.console.print(f"{p}: {line}")
                    ctx.console.print(f"[dim]  Citation:[/dim] {saved.id}")
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

        if cmd == "/patch" and args:
            _ensure_shell(ctx)
            if not ctx.cfg.tools.shell.allow_patch_apply:
                raise WorkspaceError("Patch apply disabled (tools.shell.allow_patch_apply=false).")
            sub = args[0].lower()
            if sub in {"plan", "apply"} and len(args) >= 2:
                diff_path = resolve_under_approved(ctx.cfg, " ".join(args[1:]))
                diff_text = wf.read_text(diff_path, max_bytes=ctx.cfg.tools.files.max_read_bytes)
                roots = approved_roots(ctx.cfg)
                plan = patch_svc.plan_patch(diff_text, approved_roots=roots, cwd=ctx.repo_root)
                summary = (
                    f"{sub} unified diff {diff_path} → {len(plan.target_paths)} file(s), "
                    f"{plan.hunk_count} hunk(s)"
                )
                if sub == "plan":
                    ctx.console.print(summary)
                    for p in plan.target_paths:
                        ctx.console.print(f"  - {p}")
                    return True
                req = ToolCallRequest(
                    tool_name="patch_apply",
                    permission_class=PermissionClass.WRITE,
                    action_summary=f"APPLY patch {diff_path} ({len(plan.target_paths)} targets, {plan.hunk_count} hunks)",
                )
                if ctx.cfg.tools.shell.require_confirmation and not request_tool_approval(
                    ctx.yesno, ctx.memory, req
                ):
                    ctx.console.print("[dim]Patch cancelled.[/dim]")
                    return True
                out = patch_svc.apply_unified_diff(
                    diff_text, cwd=ctx.repo_root, approved_roots=roots, dry_run=False
                )
                ctx.console.print(out)
                return True
            ctx.console.print("Usage: /patch plan <file.diff> | /patch apply <file.diff>")
            return True

        if cmd == "/test" and args:
            _ensure_shell(ctx)
            if not ctx.cfg.tools.shell.allow_test_commands:
                raise WorkspaceError("Test commands disabled (tools.shell.allow_test_commands=false).")
            inner = " ".join(args)
            # Convenience: `/test -q` => `pytest -q`
            if not inner.lstrip().startswith(("pytest", "python", "py.test")):
                inner = "pytest " + inner
            req = ToolCallRequest(
                tool_name="test_run",
                permission_class=PermissionClass.EXECUTE,
                action_summary=f"Run allow-listed tests: {inner}",
            )
            if ctx.cfg.tools.shell.require_confirmation and not request_tool_approval(
                ctx.yesno, ctx.memory, req
            ):
                ctx.console.print("[dim]Tests cancelled.[/dim]")
                return True
            out = test_svc.run_tests(
                inner,
                cwd=ctx.repo_root,
                timeout=int(ctx.cfg.tools.shell.test_timeout_seconds),
            )
            ctx.console.print(out)
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

        if cmd == "/browse" and args:
            _ensure_browser(ctx)
            url = args[0].strip()
            req = ToolCallRequest(
                tool_name="browse_fetch",
                permission_class=PermissionClass.EXTERNAL_SEND,
                action_summary=(
                    f"Fetch URL for local citation capture (no JS browser): {url}. "
                    f"Allowlist={ctx.cfg.tools.browser.allowed_hosts or 'any non-local host'}."
                ),
                external_data=True,
            )
            if ctx.cfg.tools.browser.require_confirmation and not request_tool_approval(
                ctx.yesno, ctx.memory, req
            ):
                ctx.console.print("[dim]Browse cancelled.[/dim]")
                return True
            citation = browse_svc.fetch_page(
                url,
                allowed_hosts=list(ctx.cfg.tools.browser.allowed_hosts),
                max_bytes=int(ctx.cfg.tools.browser.max_response_bytes),
                user_agent=ctx.cfg.tools.browser.user_agent,
            )
            cite_dir = Path(ctx.cfg.tools.browser.citation_dir)
            if not cite_dir.is_absolute():
                cite_dir = (Path.cwd() / cite_dir).resolve()
            saved = browse_svc.save_citation(citation, cite_dir)
            ctx.console.print(f"[bold]{saved.title}[/bold]  (HTTP {saved.status_code})")
            ctx.console.print(f"[dim]{saved.url}[/dim]")
            ctx.console.print(saved.excerpt[:1500])
            ctx.console.print(f"[dim]Citation:[/dim] {saved.citation_id}")
            ctx.console.print(f"[dim]Saved:[/dim] {saved.saved_path}")
            return True

        if cmd == "/citations":
            from atticus.services import citations as cite_svc

            cite_dir = cite_svc.citation_dir_from_config(ctx.cfg.tools.browser.citation_dir)
            sub = args[0].lower() if args else "list"
            if sub in {"list", "ls"}:
                records = cite_svc.list_records(cite_dir, limit=20)
                if not records:
                    ctx.console.print(
                        "No citations saved yet. Use /browse, /file read, or /code-search."
                    )
                    return True
                for record in records:
                    ctx.console.print(
                        f"{record.id}  [{record.kind}]  {record.title}  →  {record.source_uri}"
                    )
                return True
            if sub == "show" and len(args) >= 2:
                record = cite_svc.get_record(cite_dir, args[1].strip())
                ctx.console.print_json(data=record.to_dict())
                return True
            ctx.console.print("Usage: /citations [list] | /citations show <citation_id>")
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
            sys_prompt = head[:4000] + "\nThe Speaker asked for a concise summary of a local file excerpt. Stay factual."
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
