"""Entry point for the Phase 9 Textual desk (`atticus-desktop` script)."""

from __future__ import annotations


def main() -> None:
    try:
        from atticus.ui.textual_app import run_desktop
    except ImportError as exc:
        raise SystemExit(
            'Install the desktop extra: pip install -e ".[desktop]"'
        ) from exc
    run_desktop()


if __name__ == "__main__":
    main()
