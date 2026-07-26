"""Pydantic response schemas for the Track B M0 HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    correlation_id: str


class ReadyCheck(BaseModel):
    name: str
    ok: bool
    detail: str = ""


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: str
    version: str
    correlation_id: str
    checks: list[ReadyCheck] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
