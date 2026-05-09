from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from atticus.core.config import load_app_config, resolve_repo_root
from atticus.core.errors import AtticusError, ConfigurationError, ProviderError
from atticus.core.persona import build_system_prompt
from atticus.core.router import ProviderRouter
from atticus.memory.store import MemoryStore
from atticus.prompts.modes import valid_modes
from atticus.voice.tts import maybe_speak

console = Console()


def _split_command(line: str) -> tuple[str, list[str]]:
    parts = shlex.split(line, posix=False)
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def _help_text() -> str:
    return (
        "Slash commands:\n"
        "  /help              Show this message\n"
        "  /exit              Leave the chat\n"
        "  /provider [name]   Show or set provider: openai | anthropic | gemini\n"
        "  /mode [name]       Show or set mode (e.g. default, coding_partner)\n"
        "  /memory            List saved memory items\n"
        "  /remember <text>   Save a note to local memory\n"
        "  /forget <id>|all   Forget one id or everything\n"
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
        system_prompt = build_system_prompt(repo_root, cfg.assistant.default_mode)
    except ConfigurationError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2

    mode = cfg.assistant.default_mode
    router = ProviderRouter(cfg)
    mem_path = Path(cfg.memory.sqlite_path)
    if not mem_path.is_absolute():
        mem_path = (Path.cwd() / mem_path).resolve()
    memory = MemoryStore(mem_path)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

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

        if raw.startswith("/"):
            cmd, args = _split_command(raw)
            if cmd in {"/exit", "/quit"}:
                console.print("Until next time, Boss.")
                memory.close()
                return 0
            if cmd == "/help":
                console.print(_help_text())
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
                system_prompt = build_system_prompt(repo_root, mode)
                if messages and messages[0].get("role") == "system":
                    messages[0] = {"role": "system", "content": system_prompt}
                else:
                    messages.insert(0, {"role": "system", "content": system_prompt})
                console.print(f"Mode set to [bold]{mode}[/bold].")
                continue
            if cmd == "/memory":
                items = memory.list_items()
                if not items:
                    console.print("No saved memory items yet, Boss.")
                else:
                    for it in items:
                        console.print(f"[bold]{it.id}[/bold] [{it.kind}] {it.content} — {it.created_at}")
                continue
            if cmd == "/remember":
                if not args:
                    console.print("Usage: /remember <text>")
                    continue
                text = " ".join(args).strip()
                mid = memory.add_item(text)
                console.print(f"Remembered as item [bold]{mid}[/bold].")
                continue
            if cmd == "/forget":
                if not cfg.memory.allow_forget:
                    console.print("[red]Forget flow is disabled in config.[/red]")
                    continue
                if not args:
                    console.print("Usage: /forget <id> | /forget all")
                    continue
                if args[0].lower() == "all":
                    n = memory.forget_all()
                    console.print(f"Forgot [bold]{n}[/bold] items.")
                    continue
                try:
                    item_id = int(args[0])
                except ValueError:
                    console.print("Usage: /forget <id> | /forget all")
                    continue
                ok = memory.forget_id(item_id)
                console.print("Forgotten." if ok else f"No active item with id {item_id}.")
                continue
            console.print(f"[red]Unknown command: {cmd}[/red]")
            continue

        messages.append({"role": "user", "content": raw})
        try:
            reply = router.generate(messages, mode=mode)
        except ProviderError as exc:
            console.print(f"[red]{exc}[/red]")
            messages.pop()
            continue
        except AtticusError as exc:
            console.print(f"[red]{exc}[/red]")
            messages.pop()
            continue
        except Exception as exc:
            console.print(f"[red]Unexpected error: {exc}[/red]")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        _render_reply(reply)
        try:
            maybe_speak(reply, enabled=cfg.voice.spoken_responses)
        except Exception:
            # TTS must never take down the chat loop
            console.print("[dim]TTS skipped due to an internal error.[/dim]")


def main() -> None:
    sys.exit(run_cli())
