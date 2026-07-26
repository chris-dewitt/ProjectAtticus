"""HTTP memory controls (Track B M4 / Track A parity)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_telemetry
from atticus.memory.store import MemoryStore


class MemoryDisabled(AtticusError):
    code = "memory_disabled"
    status_code = 403


class RememberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=4000)
    kind: str = Field(default="note", max_length=40)


class ForgetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=400)
    clear_all_matching: bool = True


def _item_dict(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "content": item.content,
        "created_at": item.created_at,
        "confidence": item.confidence,
    }


def build_memory_router() -> APIRouter:
    router = APIRouter(prefix="/v1/memory", tags=["memory"])

    def _store(request: Request) -> MemoryStore:
        cfg = request.app.state.config
        if not cfg.privacy.memory_enabled:
            raise MemoryDisabled("Memory is disabled in privacy config.")
        store = getattr(request.app.state, "memory_store", None)
        if store is None:
            store = MemoryStore(Path(cfg.memory.sqlite_path).expanduser())
            request.app.state.memory_store = store
        return store

    @router.get("/notes")
    async def list_notes(request: Request, limit: int = 50) -> dict[str, Any]:
        store = _store(request)
        notes = store.list_items(limit=max(1, min(limit, 200)))
        return {"items": [_item_dict(n) for n in notes]}

    @router.get("/search")
    async def search_memory(request: Request, q: str, limit: int = 20) -> dict[str, Any]:
        store = _store(request)
        hits = store.search_items(q, limit=max(1, min(limit, 100)))
        get_telemetry().emit("api.memory_search", query_chars=len(q), hits=len(hits))
        return {"query": q, "items": [_item_dict(h) for h in hits]}

    @router.post("/remember")
    async def remember(request: Request, body: RememberRequest) -> dict[str, Any]:
        store = _store(request)
        note_id = store.add_item(body.text, kind=body.kind)
        get_telemetry().emit("api.memory_remember", note_id=note_id, kind=body.kind)
        return {"id": note_id, "kind": body.kind, "text": body.text}

    @router.post("/forget")
    async def forget(request: Request, body: ForgetRequest) -> dict[str, Any]:
        cfg = request.app.state.config
        if not cfg.memory.allow_forget:
            raise MemoryDisabled("Forget is disabled in memory config.")
        store = _store(request)
        if body.clear_all_matching:
            removed = store.forget_items_matching(body.query)
        else:
            hits = store.search_items(body.query, limit=1)
            removed = 0
            if hits:
                removed = 1 if store.forget_id(hits[0].id) else 0
        get_telemetry().emit("api.memory_forget", removed=removed)
        return {"removed": removed, "query": body.query}

    return router
