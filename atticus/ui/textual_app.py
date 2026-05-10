"""Minimal Textual desk — companion to the main CLI (Phase 9 preview)."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Markdown, TabbedContent, TabPane


class AtticusDesk(App):
    """Lightweight status window; full chat remains `python -m atticus`."""

    TITLE = "Atticus"
    SUB_TITLE = "Local desk (Phase 9)"

    BINDINGS = [("q", "quit", "Quit"), ("escape", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Desk"):
                yield Markdown(
                    "## Boss\n\n"
                    "This window is a **status hub**. Run the full assistant in a terminal:\n\n"
                    "`python -m atticus`\n\n"
                    "Future builds can add memory panels, provider switching, and tray controls here."
                )
            with TabPane("Voice"):
                yield Markdown(
                    "- `/voice`, `/mute`, `/unmute` in the CLI\n"
                    "- `/ptt` and `/wake` for speech (local Vosk)\n"
                    "- `/voice-kill` mic kill switch"
                )
            with TabPane("Tools"):
                yield Markdown(
                    "- Phase 6: `/file`, `/code-search`, `/summarize`\n"
                    "- Phase 7: `/git` (allow-listed)\n"
                    "- Phase 8: `/integrations`, `/gh`, `/open`\n"
                    "- Enable in `config/atticus.yaml` under `tools`."
                )
        yield Footer()

    def action_quit(self) -> None:
        self.exit()


def run_desktop() -> None:
    AtticusDesk().run()
