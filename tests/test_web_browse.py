from __future__ import annotations

import pytest

from atticus.core.errors import WorkspaceError
from atticus.services.web_browse import assert_http_url, host_allowed


def test_host_allowed_empty_allowlist() -> None:
    assert host_allowed("https://example.com/x", [])


def test_host_allowed_suffix() -> None:
    assert host_allowed("https://docs.example.com/a", ["example.com"])
    assert not host_allowed("https://evil.com", ["example.com"])


def test_assert_http_url_blocks_localhost() -> None:
    with pytest.raises(WorkspaceError, match="Local"):
        assert_http_url("http://localhost:8080/x")
