from __future__ import annotations

from atticus.core.errors import AtticusError, ConfigurationError, PermissionDenied


def test_legacy_message_construction_still_works() -> None:
    err = ConfigurationError("bad config")
    assert str(err) == "bad config"
    assert err.message == "bad config"
    assert err.code == "configuration_error"
    assert err.status_code == 500


def test_structured_fields_and_payload() -> None:
    err = PermissionDenied(
        "nope",
        safe_details={"tool": "shell"},
    )
    payload = err.to_dict(correlation_id="abc123")
    assert payload == {
        "code": "permission_denied",
        "message": "nope",
        "details": {"tool": "shell"},
        "correlation_id": "abc123",
    }


def test_base_error_defaults() -> None:
    err = AtticusError()
    assert err.code == "atticus_error"
    assert "details" in err.to_dict()
