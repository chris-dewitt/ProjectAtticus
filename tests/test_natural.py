from __future__ import annotations

from atticus.core.natural import parse_natural_command


def test_natural_remember() -> None:
    assert parse_natural_command("Atticus, remember that the milk is oat") == (
        "remember",
        "the milk is oat",
    )


def test_natural_forget() -> None:
    assert parse_natural_command("Hey Atticus forget that old draft") == ("forget", "old draft")


def test_natural_recall() -> None:
    assert parse_natural_command("Atticus, what do you remember about taxes?") == ("recall", "taxes?")


def test_natural_recall_empty_suffix() -> None:
    assert parse_natural_command("Atticus, what do you remember") == ("recall", "")


def test_natural_none() -> None:
    assert parse_natural_command("hello there") is None
