"""Read-only Textual status desk — companion to the main CLI and tray."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Markdown, TabbedContent, TabPane

from atticus.core.config import load_app_config
from atticus.services.desktop_status import DesktopSnapshot, build_snapshot
from atticus.services.windows_autostart import status as autostart_status


def _flag(value: bool) -> str:
    return "enabled" if value else "disabled"


def _overview(snapshot: DesktopSnapshot) -> str:
    keys = " · ".join(
        f"{name}: {'configured' if present else 'missing'}"
        for name, present in snapshot.provider_keys.items()
    )
    startup = (
        f"{_flag(snapshot.autostart.enabled)} — `{snapshot.autostart.path}`"
        if snapshot.autostart.supported
        else snapshot.autostart.detail
    )
    return (
        "## Atticus status\n\n"
        f"- **Default provider:** `{snapshot.provider}`\n"
        f"- **Default mode:** `{snapshot.mode}`\n"
        f"- **Provider credentials:** {keys}\n"
        f"- **Config:** `{snapshot.config_path}`\n"
        f"- **Windows autostart:** {startup}\n\n"
        "### Launch surfaces\n\n"
        "- Full chat: `atticus` or `python -m atticus`\n"
        "- System tray: `atticus-desktop tray`\n"
        "- Autostart: `atticus-desktop autostart status|enable|disable`\n\n"
        "This desk is read-only. Risky changes remain in explicit CLI confirmation flows."
    )


def _memory(snapshot: DesktopSnapshot) -> str:
    counts = snapshot.memory
    return (
        "## Local memory\n\n"
        f"- **Memory:** {_flag(snapshot.memory_enabled)}\n"
        f"- **Raw transcript storage:** {_flag(snapshot.raw_transcripts)}\n"
        f"- **Active notes:** {counts.notes}\n"
        f"- **Preferences:** {counts.preferences}\n"
        f"- **Conversation summaries:** {counts.summaries}\n"
        f"- **Approval audit rows:** {counts.approvals}\n"
        f"- **Database:** `{snapshot.memory_path}`\n\n"
        "Inspect or delete memory from the CLI with `/memory` and `/forget`."
    )


def _voice(snapshot: DesktopSnapshot) -> str:
    return (
        "## Voice\n\n"
        f"- **Spoken responses (config):** {_flag(snapshot.spoken_responses)}\n"
        "- Runtime controls: `/voice`, `/mute`, `/unmute`\n"
        "- Local speech input: `/ptt`, `/wake`\n"
        "- Mic kill switch: `/voice-kill`; restore with `/voice-arm`\n\n"
        "The tray does not arm the microphone or capture audio."
    )


def _tools(snapshot: DesktopSnapshot) -> str:
    lines = "\n".join(
        f"- **{name}:** {_flag(value)}"
        for name, value in snapshot.tool_flags.items()
    )
    return (
        "## Permissioned tools\n\n"
        f"- **Global tools gate:** {_flag(snapshot.tools_enabled)}\n"
        f"{lines}\n\n"
        "Tools remain off by default. Writes, execution, OAuth, external sends, "
        "and destructive actions use the CLI's approval and audit flow."
    )


def load_snapshot() -> DesktopSnapshot:
    cfg, config_path = load_app_config()
    return build_snapshot(
        cfg,
        config_path=config_path,
        autostart=autostart_status(),
        cwd=Path.cwd(),
    )


class AtticusDesk(App):
    """Read-only status window; full chat remains `python -m atticus`."""

    TITLE = "Atticus"
    SUB_TITLE = "Local desk"

    BINDINGS = [
        ("r", "refresh_status", "Refresh"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, snapshot: DesktopSnapshot) -> None:
        super().__init__()
        self.snapshot = snapshot

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Desk"):
                yield Markdown(_overview(self.snapshot), id="overview")
            with TabPane("Memory"):
                yield Markdown(_memory(self.snapshot), id="memory")
            with TabPane("Voice"):
                yield Markdown(_voice(self.snapshot), id="voice")
            with TabPane("Tools"):
                yield Markdown(_tools(self.snapshot), id="tools")
        yield Footer()

    def action_refresh_status(self) -> None:
        self.snapshot = load_snapshot()
        self.query_one("#overview", Markdown).update(_overview(self.snapshot))
        self.query_one("#memory", Markdown).update(_memory(self.snapshot))
        self.query_one("#voice", Markdown).update(_voice(self.snapshot))
        self.query_one("#tools", Markdown).update(_tools(self.snapshot))
        self.notify("Status refreshed")

    def action_quit(self) -> None:
        self.exit()


def run_desktop() -> None:
    AtticusDesk(load_snapshot()).run()
