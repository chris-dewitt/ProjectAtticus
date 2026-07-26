"""Track B M2 citation / provenance API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from atticus.services import citations as cite_svc


def build_citations_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["citations"])

    @router.get("/citations")
    async def list_citations(request: Request, limit: int = 20) -> dict[str, Any]:
        cite_dir = _citation_dir(request)
        records = cite_svc.list_records(cite_dir, limit=max(1, min(limit, 100)))
        return {"items": [record.to_dict() for record in records]}

    @router.get("/citations/{citation_id}")
    async def get_citation(request: Request, citation_id: str) -> dict[str, Any]:
        cite_dir = _citation_dir(request)
        return cite_svc.get_record(cite_dir, citation_id).to_dict()

    return router


def _citation_dir(request: Request):
    cfg = request.app.state.config
    return cite_svc.citation_dir_from_config(cfg.tools.browser.citation_dir)
