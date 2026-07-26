"""Map Atticus errors to structured HTTP JSON bodies."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from atticus.api.schemas import ErrorBody, ErrorResponse
from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_correlation_id, get_telemetry


async def atticus_error_handler(request: Request, exc: AtticusError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None) or get_correlation_id()
    get_telemetry().emit(
        "api.error",
        path=str(request.url.path),
        code=exc.code,
        status_code=exc.status_code,
    )
    body = ErrorResponse(
        error=ErrorBody(**exc.to_dict(correlation_id=correlation_id))
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None) or get_correlation_id()
    get_telemetry().emit(
        "api.unhandled_error",
        path=str(request.url.path),
        error_type=type(exc).__name__,
    )
    body = ErrorResponse(
        error=ErrorBody(
            code="internal_error",
            message="An unexpected error occurred.",
            correlation_id=correlation_id,
            details={},
        )
    )
    return JSONResponse(status_code=500, content=body.model_dump())


def error_payload(
    *,
    code: str,
    message: str,
    correlation_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            correlation_id=correlation_id,
            details=dict(details or {}),
        )
    ).model_dump()
