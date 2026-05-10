from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from atticus.core.approvals import ConsoleYesNoSource, confirm_exact_token, request_tool_approval
from atticus.core.config import load_app_config, resolve_repo_root
from atticus.core.errors import AtticusError, ConfigurationError, ProviderError, VoiceInputError
from atticus.core.natural import parse_natural_command
from atticus.core.permissions import PermissionClass
from atticus.core.persona import build_system_prompt
from atticus.core.router import ProviderRouter
from atticus.core.tool_request import ToolCallRequest
from atticus.memory.context import build_memory_context_block
from atticus.memory.store import MemoryStore
from atticus.prompts.modes import valid_modes
from atticus.voice.audio_state import VoiceSessionState
from atticus.voice.stt import record_and_transcribe
from atticus.voice.tts import VoiceOutput
from atticus.voice.wake_word import wake_match
from atticus.workbench_commands import ToolCliContext, handle_tool_slash

console = Console()

_FORGET_ALL_TOKEN = "YES"


def _split_command(line: str) -> tuple[str, list[str]]:
    parts = shlex.split(line, posix=False)
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def _help_text() -> str:
    return (
        "Slash commands:\n"
        "  /help                 Show this message\n"
        "  /exit                 Leave the chat\n"
        "  /provider [name]      Show or set provider: openai | anthropic | gemini\n"
        "  /mode [name]          Show or set mode (e.g. default, coding_partner)\n"
        "  /memory [section]     Overview, or: items | prefs | summaries | audit\n"
        "  /remember <text>      Save a note to local memory\n"
        "  /recall <query>       Search saved notes (substring)\n"
        "  /what-do-you-remember <query>   Same as /recall (docs name)\n"
        "  /pref list|get|set|forget ...\n"
        "  /summary add <text>   Store a conversation/session summary locally\n"
        "  /forget ...           Forget by id, all (requires YES), match <text>, pref <key>, summary <id>\n"
        "  /mute | /unmute       Pause or resume spoken replies (runtime; text always works)\n"
        "  /voice                Show speech-related settings\n"
        "  /ptt [seconds]        Push-to-talk: local Vosk STT (requires .[stt] + model path)\n"
        "  /listen [seconds]     Same as /ptt\n"
        "  /wake                 Wake phrase clip, then command clip (Phase 5; all local)\n"
        "  /voice-kill | /voice-arm   Kill switch for all mic capture vs restore\n"
        "  /file read|search|write …  Local file tools (tools.enabled + tools.files.enabled)\n"
        "  /code-search <regex>   Search *.py under approved_paths (approval)\n"
        "  /git <git …>          Allow-listed read-only git (tools.shell.enabled)\n"
        "  /gh issues <o> <r>    Recent GitHub issues (tools.github.enabled)\n"
        "  /open <url>           Browser open with approval when configured\n"
        "  /summarize <path>     Send file excerpt to LLM (approval if privacy flag on)\n"
        "  /integrations         Phase 8 placeholder status (Gmail/Calendar/Browser)\n"
        "\n"
        "Natural language (examples):\n"
        '  Atticus, remember that ...\n'
        '  Atticus, forget that ...   (substring soft-delete; asks approval)\n'
        '  Atticus, what do you remember about ...?\n'
    )


def _render_reply(text: str) -> None:
    console.print(Markdown(text))


def run_cli() -> int:
    try:
        cfg, config_path = load_app_config()
    except ConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    repo_root = resolve_repo_root(cfg, config_file=config_path)
    try:
        persona_core = build_system_prompt(repo_root, cfg.assistant.default_mode)
    except ConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    mode = cfg.assistant.default_mode
    router = ProviderRouter(cfg)
    voice_out = VoiceOutput(cfg.voice, console)
    voice_state = VoiceSessionState()
    mem_path = Path(cfg.memory.sqlite_path)
    if not mem_path.is_absolute():
        mem_path = (Path.cwd() / mem_path).resolve()
    memory = MemoryStore(mem_path)

    messages: list[dict[str, Any]] = [{"role": "system", "content": persona_core}]
    yesno = ConsoleYesNoSource(console)

    def refresh_system_message() -> None:
        block = build_memory_context_block(memory, cfg) if cfg.privacy.memory_enabled else ""
        if block.strip():
            messages[0] = {
                "role": "system",
                "content": f"{persona_core}\n\n---\n\n## Local memory context\n\n{block}",
            }
        else:
            messages[0] = {"role": "system", "content": persona_core}

    def require_memory() -> bool:
        if not cfg.privacy.memory_enabled:
            console.print("[red]Memory is disabled in config (privacy.memory_enabled=false).[/red]")
            return False
        return True

    def process_chat_turn(user_text: str) -> None:
        nonlocal messages, mode
        refresh_system_message()
        messages.append({"role": "user", "content": user_text})
        try:
            reply = router.generate(messages, mode=mode)
        except ProviderError as exc:
            console.print(f"[red]{exc}[/red]")
            messages.pop()
            return
        except AtticusError as exc:
            console.print(f"[red]{exc}[/red]")
            messages.pop()
            return
        except Exception as exc:
            console.print(f"[red]Unexpected error: {exc}[/red]")
            messages.pop()
            return
        messages.append({"role": "assistant", "content": reply})
        _render_reply(reply)
        voice_out.speak(reply)

    def try_ptt(seconds: float) -> None:
        try:
            text = record_and_transcribe(
                cfg.voice, seconds=seconds, console=console, label="Push-to-talk"
            )
        except VoiceInputError as exc:
            console.print(f"[red]{exc}[/red]")
            return
        if text.strip():
            process_chat_turn(text.strip())

    def try_wake_flow() -> None:
        if not voice_state.voice_input_armed:
            console.print(
                "[red]Voice input kill switch is active — mic capture is disabled. "
                "Use /voice-arm when you are ready.[/red]"
            )
            return
        console.print(
            "[bold red]●[/bold red] [yellow]LISTENING for a wake phrase (local Vosk; no cloud audio)…[/yellow]"
        )
        try:
            t_wake = record_and_transcribe(
                cfg.voice,
                seconds=float(cfg.voice.wake_listen_seconds),
                console=console,
                label="Wake listen",
            )
        except VoiceInputError as exc:
            console.print(f"[red]{exc}[/red]")
            return
        if not wake_match(t_wake, cfg.voice):
            console.print(
                "[yellow]No wake phrase detected in that clip. Try /wake again, or use /ptt without wake.[/yellow]"
            )
            return
        console.print("[bold green]Wake heard.[/bold green] Recording your command…")
        try:
            t_cmd = record_and_transcribe(
                cfg.voice,
                seconds=float(cfg.voice.wake_command_seconds),
                console=console,
                label="Command",
            )
        except VoiceInputError as exc:
            console.print(f"[red]{exc}[/red]")
            return
        if t_cmd.strip():
            process_chat_turn(t_cmd.strip())

    refresh_system_message()

    console.print(
        f"[bold green]Atticus[/bold green] online — provider={router.current}, mode={mode}. "
        "Type /help for commands."
    )

    while True:
        try:
            raw = console.input("[bold cyan]Boss>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nFair enough, Boss. Stepping away.")
            memory.close()
            return 0

        if not raw:
            continue

        natural = parse_natural_command(raw)
        if natural:
            verb, payload = natural
            if not require_memory():
                continue
            if verb == "remember":
                if not payload:
                    console.print("Tell me what to remember, Boss.")
                    continue
                mid = memory.add_item(payload)
                console.print(f"Remembered as item [bold]{mid}[/bold].")
                refresh_system_message()
                continue
            if verb == "forget":
                if not cfg.memory.allow_forget:
                    console.print("[red]Forget flow is disabled in config.[/red]")
                    continue
                if not payload:
                    console.print("Tell me what to forget (substring match), Boss.")
                    continue
                req = ToolCallRequest(
                    tool_name="memory_forget_match",
                    permission_class=PermissionClass.DESTRUCTIVE,
                    action_summary=f"Soft-delete all memory notes matching substring: {payload!r}",
                    destructive=True,
                )
                if not request_tool_approval(yesno, memory, req):
                    console.print("[dim]Cancelled. Nothing was forgotten.[/dim]")
                    continue
                n = memory.forget_items_matching(payload)
                console.print(f"Soft-deleted [bold]{n}[/bold] matching note(s).")
                refresh_system_message()
                continue
            if verb == "recall":
                if payload:
                    hits = memory.search_items(payload)
                    if not hits:
                        console.print("No matching notes found, Boss.")
                    else:
                        for it in hits:
                            console.print(f"[bold]{it.id}[/bold] [{it.kind}] {it.content} — {it.created_at}")
                else:
                    items = memory.list_items(limit=10)
                    if not items:
                        console.print("No saved notes yet, Boss.")
                    else:
                        for it in items:
                            console.print(f"[bold]{it.id}[/bold] [{it.kind}] {it.content} — {it.created_at}")
                continue

        if raw.startswith("/"):
            cmd, args = _split_command(raw)
            if cmd in {"/exit", "/quit"}:
                console.print("Until next time, Boss.")
                memory.close()
                return 0
            if cmd == "/help":
                console.print(_help_text())
                continue
            if cmd == "/mute":
                voice_out.set_muted(True)
                console.print("[dim]Speech muted. You will still see every reply here, Boss.[/dim]")
                continue
            if cmd == "/unmute":
                voice_out.set_muted(False)
                if not cfg.voice.spoken_responses:
                    console.print(
                        "[yellow]Config has voice.spoken_responses=false; enable it to hear replies aloud.[/yellow]"
                    )
                else:
                    console.print("[dim]Speech unmuted (when TTS is available).[/dim]")
                continue
            if cmd == "/voice":
                console.print(
                    f"voice.spoken_responses (config): [bold]{cfg.voice.spoken_responses}[/bold]\n"
                    f"runtime muted: [bold]{voice_out.runtime_muted}[/bold]\n"
                    f"voice.tts_engine: [bold]{cfg.voice.tts_engine}[/bold]\n"
                    f"voice.tts_rate: [bold]{cfg.voice.tts_rate}[/bold]\n"
                    f"voice.stt_engine: [bold]{cfg.voice.stt_engine}[/bold]\n"
                    f"voice.vosk_model_path: [bold]{cfg.voice.vosk_model_path}[/bold]\n"
                    f"voice.push_to_talk_default_seconds: [bold]{cfg.voice.push_to_talk_default_seconds}[/bold]\n"
                    f"voice.wake_listen_seconds / wake_command_seconds: "
                    f"[bold]{cfg.voice.wake_listen_seconds}[/bold] / [bold]{cfg.voice.wake_command_seconds}[/bold]\n"
                    f"voice_input_armed (kill switch): [bold]{voice_state.voice_input_armed}[/bold]"
                )
                continue
            if cmd == "/voice-kill":
                voice_state.disarm()
                console.print("[red]Voice kill switch: microphone capture disabled for /ptt and /wake.[/red]")
                continue
            if cmd == "/voice-arm":
                voice_state.arm()
                console.print("[dim]Voice input re-armed. /ptt and /wake work again.[/dim]")
                continue
            if cmd in {"/ptt", "/listen"}:
                if not voice_state.voice_input_armed:
                    console.print("[red]Voice input is disarmed. Use /voice-arm first.[/red]")
                    continue
                sec = float(cfg.voice.push_to_talk_default_seconds)
                if args:
                    try:
                        sec = float(args[0])
                    except ValueError:
                        console.print("Usage: /ptt [seconds]")
                        continue
                try_ptt(sec)
                continue
            if cmd == "/wake":
                try_wake_flow()
                continue
            if cmd == "/provider":
                if not args:
                    console.print(f"Current provider: [bold]{router.current}[/bold]")
                    continue
                try:
                    router.set_provider(args[0])
                    console.print(f"Provider set to [bold]{router.current}[/bold].")
                except ValueError as exc:
                    console.print(f"[red]{exc}[/red]")
                continue
            if cmd == "/mode":
                if not args:
                    console.print(f"Current mode: [bold]{mode}[/bold]")
                    continue
                new_mode = args[0].strip()
                if new_mode not in valid_modes():
                    console.print(f"[red]Unknown mode: {new_mode}[/red]")
                    continue
                mode = new_mode
                persona_core = build_system_prompt(repo_root, mode)
                refresh_system_message()
                console.print(f"Mode set to [bold]{mode}[/bold].")
                continue
            if cmd == "/memory":
                if not require_memory():
                    continue
                section = (args[0].lower() if args else "overview")
                if not args or section == "overview":
                    n_notes = memory.count_active_items()
                    n_prefs = memory.count_preferences()
                    n_sum = memory.count_summaries()
                    n_aud = memory.count_tool_approvals()
                    console.print(
                        f"Memory overview — notes: [bold]{n_notes}[/bold], preferences: [bold]{n_prefs}[/bold], "
                        f"summaries: [bold]{n_sum}[/bold], audit rows: [bold]{n_aud}[/bold].\n"
                        "Sections: [bold]/memory items|prefs|summaries|audit[/bold]"
                    )
                    continue
                if section == "items":
                    items = memory.list_items()
                    if not items:
                        console.print("No saved memory items yet, Boss.")
                    else:
                        for it in items:
                            console.print(f"[bold]{it.id}[/bold] [{it.kind}] {it.content} — {it.created_at}")
                    continue
                if section == "prefs":
                    prefs = memory.list_preferences()
                    if not prefs:
                        console.print("No preferences stored yet, Boss.")
                    else:
                        for p in prefs:
                            src = f" ({p.source})" if p.source else ""
                            console.print(f"[bold]{p.key}[/bold] = {p.value}{src}")
                    continue
                if section in {"summaries", "summary"}:
                    sums = memory.list_summaries()
                    if not sums:
                        console.print("No conversation summaries yet, Boss.")
                    else:
                        for s in sums:
                            console.print(
                                f"[bold]{s.id}[/bold] [{s.mode or '-'} / {s.provider or '-'}] {s.summary} — {s.created_at}"
                            )
                    continue
                if section == "audit":
                    rows = memory.list_tool_approvals(limit=40)
                    if not rows:
                        console.print("No tool approval records yet, Boss.")
                    else:
                        for r in rows:
                            flag = "approved" if r.approved else "denied"
                            console.print(
                                f"[bold]{r.id}[/bold] [{r.permission_class}] {r.tool_name} — {flag}\n"
                                f"    {r.action_summary}\n"
                                f"    {r.created_at}"
                            )
                    continue
                console.print("[red]Unknown /memory section. Use items, prefs, summaries, or audit.[/red]")
                continue
            if cmd == "/remember":
                if not require_memory():
                    continue
                if not args:
                    console.print("Usage: /remember <text>")
                    continue
                text = " ".join(args).strip()
                mid = memory.add_item(text)
                console.print(f"Remembered as item [bold]{mid}[/bold].")
                refresh_system_message()
                continue
            if cmd in {"/recall", "/what-do-you-remember"}:
                if not require_memory():
                    continue
                if not args:
                    console.print("Usage: /recall <substring>  (or /what-do-you-remember <substring>)")
                    continue
                q = " ".join(args).strip()
                hits = memory.search_items(q)
                if not hits:
                    console.print("No matching notes found, Boss.")
                else:
                    for it in hits:
                        console.print(f"[bold]{it.id}[/bold] [{it.kind}] {it.content} — {it.created_at}")
                continue
            if cmd == "/pref":
                if not require_memory():
                    continue
                if not args:
                    console.print("Usage: /pref list | /pref get <key> | /pref set <key> <value...> | /pref forget <key>")
                    continue
                sub = args[0].lower()
                if sub == "list":
                    prefs = memory.list_preferences()
                    if not prefs:
                        console.print("No preferences stored yet, Boss.")
                    else:
                        for p in prefs:
                            console.print(f"[bold]{p.key}[/bold] = {p.value}")
                    continue
                if sub == "get" and len(args) >= 2:
                    val = memory.get_preference(args[1])
                    console.print(val if val is not None else f"No preference for key {args[1]!r}.")
                    continue
                if sub == "set" and len(args) >= 3:
                    key = args[1]
                    value = " ".join(args[2:]).strip()
                    memory.upsert_preference(key, value, source="cli")
                    console.print(f"Preference [bold]{key}[/bold] saved.")
                    refresh_system_message()
                    continue
                if sub == "forget" and len(args) >= 2:
                    ok = memory.delete_preference(args[1])
                    console.print("Removed." if ok else "No such preference key.")
                    refresh_system_message()
                    continue
                console.print("Usage: /pref list | /pref get <key> | /pref set <key> <value...> | /pref forget <key>")
                continue
            if cmd == "/summary":
                if not require_memory():
                    continue
                if len(args) >= 2 and args[0].lower() == "add":
                    text = " ".join(args[1:]).strip()
                    sid = memory.add_conversation_summary(text, mode=mode, provider=router.current)
                    console.print(f"Summary stored as [bold]{sid}[/bold].")
                    refresh_system_message()
                    continue
                console.print("Usage: /summary add <text>")
                continue
            if cmd == "/forget":
                if not require_memory():
                    continue
                if not cfg.memory.allow_forget:
                    console.print("[red]Forget flow is disabled in config.[/red]")
                    continue
                if not args:
                    console.print(
                        "Usage: /forget <id> | /forget all | /forget match <text> | /forget pref <key> | "
                        "/forget summary <id>"
                    )
                    continue
                sub = args[0].lower()
                if sub == "all":
                    if not confirm_exact_token(
                        yesno,
                        "Type YES in capitals to confirm deleting every memory note: ",
                        _FORGET_ALL_TOKEN,
                    ):
                        console.print("[dim]Bulk forget cancelled.[/dim]")
                        continue
                    n = memory.forget_all()
                    console.print(f"Forgot [bold]{n}[/bold] notes (soft delete).")
                    refresh_system_message()
                    continue
                if sub == "match" and len(args) >= 2:
                    needle = " ".join(args[1:]).strip()
                    req = ToolCallRequest(
                        tool_name="memory_forget_match",
                        permission_class=PermissionClass.DESTRUCTIVE,
                        action_summary=f"Soft-delete notes matching substring: {needle!r}",
                        destructive=True,
                    )
                    if not request_tool_approval(yesno, memory, req):
                        console.print("[dim]Cancelled.[/dim]")
                        continue
                    n = memory.forget_items_matching(needle)
                    console.print(f"Soft-deleted [bold]{n}[/bold] note(s).")
                    refresh_system_message()
                    continue
                if sub == "pref" and len(args) >= 2:
                    ok = memory.delete_preference(args[1])
                    console.print("Preference removed." if ok else "No such preference key.")
                    refresh_system_message()
                    continue
                if sub == "summary" and len(args) >= 2:
                    try:
                        sid = int(args[1])
                    except ValueError:
                        console.print("Usage: /forget summary <id>")
                        continue
                    ok = memory.forget_summary_id(sid)
                    console.print("Summary removed." if ok else f"No summary with id {sid}.")
                    refresh_system_message()
                    continue
                try:
                    item_id = int(args[0])
                except ValueError:
                    console.print(
                        "Usage: /forget <id> | /forget all | /forget match <text> | /forget pref <key> | "
                        "/forget summary <id>"
                    )
                    continue
                ok = memory.forget_id(item_id)
                console.print("Forgotten." if ok else f"No active item with id {item_id}.")
                refresh_system_message()
                continue
            tctx = ToolCliContext(
                cfg=cfg,
                repo_root=repo_root,
                memory=memory,
                yesno=yesno,
                router=router,
                mode=mode,
                persona_core=persona_core,
                console=console,
            )
            if handle_tool_slash(cmd, args, tctx):
                continue
            console.print(f"[red]Unknown command: {cmd}[/red]")
            continue

        process_chat_turn(raw)


def main() -> None:
    sys.exit(run_cli())
