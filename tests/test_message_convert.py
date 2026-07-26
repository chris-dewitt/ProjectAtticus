from __future__ import annotations

from atticus.providers.message_convert import (
    anthropic_messages,
    gemini_contents,
    split_system_and_turns,
)


def test_split_system_and_turns() -> None:
    system, turns = split_system_and_turns(
        [
            {"role": "system", "content": "Be helpful."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "system", "content": "Extra"},
        ]
    )
    assert "Be helpful." in system
    assert "Extra" in system
    assert turns == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]


def test_anthropic_drops_leading_assistant() -> None:
    msgs = anthropic_messages(
        [
            {"role": "assistant", "content": "orphan"},
            {"role": "user", "content": "hi"},
        ]
    )
    assert msgs[0]["role"] == "user"


def test_gemini_role_mapping() -> None:
    contents = gemini_contents(
        [
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a"},
        ]
    )
    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"
    assert contents[1]["parts"][0]["text"] == "a"
