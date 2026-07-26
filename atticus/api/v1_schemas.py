"""Pydantic schemas for Track B /v1 conversation and run APIs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str | None = None
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: Literal["system", "user", "assistant"]
    content: str
    created_at: str


class CreateMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    role: Literal["user"] = "user"
    mode: str | None = None
    provider: str | None = None
    execute: bool = True
    """When true, create and execute a bounded run for this message."""


class CreateMessageResponse(BaseModel):
    message: MessageResponse
    run: dict[str, Any] | None = None


class RunError(BaseModel):
    code: str
    message: str


class CheckpointResponse(BaseModel):
    name: str
    at: str
    detail: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    conversation_id: str
    status: str
    provider: str
    mode: str
    created_at: str
    updated_at: str
    input_messages: list[dict[str, str]]
    output_text: str | None = None
    error: RunError | None = None
    cancel_requested: bool = False
    checkpoints: list[CheckpointResponse] = Field(default_factory=list)
    correlation_id: str | None = None


class CreateRunRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[dict[str, str]] = Field(min_length=1)
    mode: str | None = None
    provider: str | None = None
    execute: bool = True
    title: str | None = None
