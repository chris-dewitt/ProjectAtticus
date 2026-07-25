from __future__ import annotations

from atticus.memory.summarizer import should_auto_summarize, summarize_conversation


def test_summarize_conversation_local_bullets() -> None:
    summary = summarize_conversation(
        [
            {"role": "system", "content": "ignore me"},
            {"role": "user", "content": "Remind me to water the plants"},
            {"role": "assistant", "content": "Of course, Boss. I'll note that."},
            {"role": "user", "content": "Also schedule a walk"},
        ],
        max_chars=900,
        max_bullets=8,
    )
    assert "Session summary" in summary
    assert "water the plants" in summary
    assert "schedule a walk" in summary
    # Must not dump a raw transcript dump marker.
    assert "role\":" not in summary


def test_summarize_empty() -> None:
    assert summarize_conversation([{"role": "system", "content": "only system"}]) == ""


def test_should_auto_summarize_gates() -> None:
    assert should_auto_summarize(
        enabled=True,
        store_summaries=True,
        memory_enabled=True,
        user_turns_since_summary=6,
        every_n_turns=6,
    )
    assert not should_auto_summarize(
        enabled=True,
        store_summaries=True,
        memory_enabled=True,
        user_turns_since_summary=5,
        every_n_turns=6,
    )
    assert not should_auto_summarize(
        enabled=False,
        store_summaries=True,
        memory_enabled=True,
        user_turns_since_summary=10,
        every_n_turns=6,
    )
