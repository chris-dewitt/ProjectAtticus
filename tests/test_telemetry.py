from __future__ import annotations

from atticus.core.telemetry import (
    Telemetry,
    bind_correlation_id,
    get_correlation_id,
    get_telemetry,
    set_telemetry,
)


def test_redacts_secret_fields() -> None:
    tel = Telemetry(enabled=True, emit_stderr=False)
    event = tel.emit(
        "unit.test",
        api_key="sk-should-not-leak",
        nested={"token": "abc", "ok": 1},
        path="/tmp/file",
    )
    assert event is not None
    assert event.attributes["api_key"] == "[redacted]"
    assert event.attributes["nested"]["token"] == "[redacted]"
    assert event.attributes["nested"]["ok"] == 1
    assert event.attributes["path"] == "/tmp/file"


def test_correlation_id_context() -> None:
    with bind_correlation_id("fixed-id") as cid:
        assert cid == "fixed-id"
        assert get_correlation_id() == "fixed-id"
        tel = Telemetry(enabled=True)
        event = tel.emit("bound")
        assert event is not None
        assert event.correlation_id == "fixed-id"
    assert get_correlation_id() is None


def test_span_records_duration() -> None:
    tel = Telemetry(enabled=True)
    with tel.span("work", label="x") as bag:
        bag["result"] = "ok"
    assert tel.events[-1].name == "work"
    assert tel.events[-1].attributes["result"] == "ok"
    assert "duration_ms" in tel.events[-1].attributes


def test_disabled_emits_nothing() -> None:
    previous = get_telemetry()
    try:
        set_telemetry(Telemetry(enabled=False))
        assert get_telemetry().emit("noop") is None
    finally:
        set_telemetry(previous)
