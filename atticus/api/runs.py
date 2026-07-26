"""FastAPI routes for Track B conversations and bounded runs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Request

from atticus.api.v1_schemas import (
    ConversationResponse,
    CreateConversationRequest,
    CreateMessageRequest,
    CreateMessageResponse,
    CreateRunRequest,
    MessageResponse,
    RunResponse,
)
from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_correlation_id, get_telemetry
from atticus.runs.models import RunRecord
from atticus.runs.orchestrator import BoundedRunOrchestrator
from atticus.runs.store import RunStore


def build_runs_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["runs"])

    @router.post("/conversations", response_model=ConversationResponse)
    async def create_conversation(
        request: Request,
        body: CreateConversationRequest,
    ) -> ConversationResponse:
        store: RunStore = request.app.state.run_store
        record = store.create_conversation(title=body.title)
        get_telemetry().emit("api.conversation_created", conversation_id=record.id)
        return ConversationResponse(
            id=record.id,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
    async def get_conversation(request: Request, conversation_id: str) -> ConversationResponse:
        store: RunStore = request.app.state.run_store
        record = store.get_conversation(conversation_id)
        return ConversationResponse(
            id=record.id,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @router.get("/conversations/{conversation_id}/messages")
    async def list_messages(request: Request, conversation_id: str) -> dict[str, Any]:
        store: RunStore = request.app.state.run_store
        messages = store.list_messages(conversation_id)
        return {
            "items": [
                MessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at,
                ).model_dump()
                for m in messages
            ]
        }

    @router.post(
        "/conversations/{conversation_id}/messages",
        response_model=CreateMessageResponse,
    )
    async def create_message(
        request: Request,
        conversation_id: str,
        body: CreateMessageRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> CreateMessageResponse:
        store: RunStore = request.app.state.run_store
        orchestrator: BoundedRunOrchestrator = request.app.state.orchestrator
        default_provider: str = request.app.state.default_provider
        default_mode: str = request.app.state.default_mode

        if idempotency_key:
            existing = store.get_run_by_idempotency_key(idempotency_key)
            if existing is not None:
                messages = store.list_messages(conversation_id)
                last_user = next((m for m in reversed(messages) if m.role == "user"), None)
                if last_user is None:
                    last_user = store.add_message(
                        conversation_id,
                        role="user",
                        content=body.content,
                    )
                return CreateMessageResponse(
                    message=MessageResponse(
                        id=last_user.id,
                        conversation_id=last_user.conversation_id,
                        role=last_user.role,
                        content=last_user.content,
                        created_at=last_user.created_at,
                    ),
                    run=_run_response(existing).model_dump(),
                )

        message = store.add_message(
            conversation_id,
            role=body.role,
            content=body.content,
        )
        run_payload = None
        if body.execute:
            history = [
                {"role": m.role, "content": m.content}
                for m in store.list_messages(conversation_id)
                if m.role in {"user", "assistant", "system"}
            ]
            # Bound input to user/assistant turns for the run (system assembled by orchestrator).
            input_messages = [
                item for item in history if item["role"] in {"user", "assistant"}
            ]
            run = store.create_run(
                conversation_id=conversation_id,
                provider=(body.provider or default_provider).lower(),
                mode=body.mode or default_mode,
                input_messages=input_messages,
                correlation_id=get_correlation_id(),
                idempotency_key=idempotency_key,
            )
            if run.status.value == "queued":
                run = orchestrator.execute(run.id)
            run_payload = _run_response(run).model_dump()
        return CreateMessageResponse(
            message=MessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            ),
            run=run_payload,
        )

    @router.post("/runs", response_model=RunResponse)
    async def create_run(
        request: Request,
        body: CreateRunRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> RunResponse:
        store: RunStore = request.app.state.run_store
        orchestrator: BoundedRunOrchestrator = request.app.state.orchestrator
        default_provider: str = request.app.state.default_provider
        default_mode: str = request.app.state.default_mode

        if body.conversation_id:
            conversation_id = body.conversation_id
            store.get_conversation(conversation_id)
        else:
            conversation_id = store.create_conversation(title=body.title).id

        for item in body.messages:
            role = str(item.get("role", "user"))
            content = str(item.get("content", ""))
            if role not in {"user", "assistant", "system"}:
                raise AtticusError(
                    f"Unsupported message role: {role}",
                    code="invalid_message",
                    status_code=400,
                )
            if role != "system":
                store.add_message(conversation_id, role=role, content=content)  # type: ignore[arg-type]

        input_messages = [
            {"role": str(m.get("role", "user")), "content": str(m.get("content", ""))}
            for m in body.messages
            if str(m.get("role", "user")) in {"user", "assistant"}
        ]
        run = store.create_run(
            conversation_id=conversation_id,
            provider=(body.provider or default_provider).lower(),
            mode=body.mode or default_mode,
            input_messages=input_messages,
            correlation_id=get_correlation_id(),
            idempotency_key=idempotency_key,
        )
        if body.execute and run.status.value == "queued":
            run = orchestrator.execute(run.id)
        return _run_response(run)

    @router.get("/runs/{run_id}", response_model=RunResponse)
    async def get_run(request: Request, run_id: str) -> RunResponse:
        store: RunStore = request.app.state.run_store
        return _run_response(store.get_run(run_id))

    @router.post("/runs/{run_id}/cancel", response_model=RunResponse)
    async def cancel_run(request: Request, run_id: str) -> RunResponse:
        orchestrator: BoundedRunOrchestrator = request.app.state.orchestrator
        return _run_response(orchestrator.cancel(run_id))

    return router


def _run_response(run: RunRecord) -> RunResponse:
    payload = run.to_public_dict()
    return RunResponse.model_validate(payload)
