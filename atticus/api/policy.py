"""Track B M3 policy and approval API routes."""

from __future__ import annotations

import hmac
from typing import Any, Literal

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field

from atticus.core.errors import DependencyUnavailable
from atticus.core.permissions import PermissionClass
from atticus.core.secrets import get_credential
from atticus.core.telemetry import get_telemetry
from atticus.policy.models import ApprovalStatus, PolicyInput
from atticus.policy.service import PolicyService
from atticus.policy.store import ApprovalAuthenticationError


class PolicyIntentRequest(BaseModel):
    tool_name: str = Field(min_length=1, max_length=120)
    permission_class: PermissionClass
    action_summary: str = Field(min_length=1, max_length=2000)
    inputs: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="boss", min_length=1, max_length=120)
    resource: str | None = Field(default=None, max_length=2000)
    external_data: bool = False
    destructive: bool = False


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "deny"]
    actor: str = Field(min_length=1, max_length=120)
    action_digest: str = Field(min_length=64, max_length=64)
    confirmation: str = Field(min_length=1, max_length=80)
    rationale: str | None = Field(default=None, max_length=2000)


class ExecutionResultRequest(BaseModel):
    succeeded: bool
    actor: str = Field(min_length=1, max_length=120)
    result_summary: str = Field(min_length=1, max_length=2000)


def build_policy_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["policy", "approvals"])

    @router.post("/policy/evaluate")
    async def evaluate_policy(
        request: Request,
        body: PolicyIntentRequest,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, object]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        result = service.evaluate(_to_intent(body), create_approval=False)
        return result.to_dict()

    @router.post("/approvals")
    async def request_approval(
        request: Request,
        body: PolicyIntentRequest,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, object]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        result = service.evaluate(_to_intent(body), create_approval=True)
        return result.to_dict()

    @router.get("/approvals")
    async def list_approvals(
        request: Request,
        status: ApprovalStatus | None = None,
        limit: int = 50,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, object]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        items = service.store.list_approvals(status=status, limit=limit)
        return {"items": [item.to_dict() for item in items]}

    @router.get("/approvals/{approval_id}")
    async def get_approval(
        request: Request,
        approval_id: str,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, Any]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        return service.store.get_approval(approval_id).to_dict()

    @router.post("/approvals/{approval_id}/decision")
    async def decide_approval(
        request: Request,
        approval_id: str,
        body: ApprovalDecisionRequest,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, Any]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        approval = service.store.decide(
            approval_id,
            approve=body.decision == "approve",
            actor=body.actor,
            action_digest=body.action_digest,
            confirmation=body.confirmation,
            rationale=body.rationale,
        )
        get_telemetry().emit(
            "approval.decided",
            approval_id=approval.id,
            status=approval.status.value,
            actor=body.actor,
        )
        return approval.to_dict()

    @router.post("/approvals/{approval_id}/execution")
    async def record_execution(
        request: Request,
        approval_id: str,
        body: ExecutionResultRequest,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, Any]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        approval = service.store.record_execution(
            approval_id,
            succeeded=body.succeeded,
            result_summary=body.result_summary,
            actor=body.actor,
        )
        return approval.to_dict()

    @router.get("/audit/policy")
    async def list_policy_audit(
        request: Request,
        limit: int = 100,
        approval_token: str | None = Header(default=None, alias="X-Atticus-Approval-Token"),
    ) -> dict[str, object]:
        _require_approval_token(request, approval_token)
        service: PolicyService = request.app.state.policy_service
        return {"items": service.store.list_audit_events(limit=limit)}

    return router


def _to_intent(body: PolicyIntentRequest) -> PolicyInput:
    return PolicyInput(
        tool_name=body.tool_name,
        permission_class=body.permission_class,
        action_summary=body.action_summary,
        inputs=body.inputs,
        actor=body.actor,
        resource=body.resource,
        external_data=body.external_data,
        destructive=body.destructive,
    )


def _require_approval_token(request: Request, supplied: str | None) -> None:
    env_name = request.app.state.config.policy.approval_token_env
    expected = get_credential(env_name)
    if not expected:
        raise DependencyUnavailable(
            f"Approval decisions are disabled until {env_name} is configured.",
            code="approval_token_not_configured",
            status_code=503,
            safe_details={"environment_variable": env_name},
        )
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise ApprovalAuthenticationError("Invalid or missing approval token.")
