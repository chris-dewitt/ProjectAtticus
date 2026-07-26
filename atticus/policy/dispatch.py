"""Idempotent gateway for executing approved mutating tools (M3 remainder)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from atticus.core.config import AppConfig
from atticus.core.errors import AtticusError, WorkspaceError
from atticus.core.telemetry import get_telemetry
from atticus.policy.models import ApprovalStatus
from atticus.policy.store import ApprovalConflict, ApprovalStore
from atticus.services import workspace_files as wf
from atticus.services.paths import resolve_under_approved

ToolHandler = Callable[[AppConfig, dict[str, Any]], dict[str, Any]]


class ToolNotDispatchable(AtticusError):
    code = "tool_not_dispatchable"
    status_code = 400


class DispatchDenied(AtticusError):
    code = "dispatch_denied"
    status_code = 409


@dataclass(frozen=True)
class DispatchResult:
    approval_id: str
    tool_name: str
    status: str
    idempotency_key: str
    replayed: bool
    result: dict[str, Any]
    action_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "idempotency_key": self.idempotency_key,
            "replayed": self.replayed,
            "result": self.result,
            "action_digest": self.action_digest,
        }


def _handle_local_echo(_cfg: AppConfig, inputs: dict[str, Any]) -> dict[str, Any]:
    message = str(inputs.get("message", "")).strip()
    if not message:
        raise WorkspaceError("local_echo requires inputs.message")
    if len(message) > 4000:
        raise WorkspaceError("local_echo message exceeds 4000 characters")
    return {"echo": message, "chars": len(message)}


def _handle_file_write(cfg: AppConfig, inputs: dict[str, Any]) -> dict[str, Any]:
    path_raw = str(inputs.get("path", "")).strip()
    content = inputs.get("content")
    if not path_raw:
        raise WorkspaceError("file_write requires inputs.path")
    if not isinstance(content, str):
        raise WorkspaceError("file_write requires string inputs.content")
    if len(content.encode("utf-8", errors="replace")) > 200_000:
        raise WorkspaceError("file_write content exceeds 200KB safety cap")
    path = resolve_under_approved(cfg, path_raw)
    append = bool(inputs.get("append", False))
    text = content if content.endswith("\n") or append else content + "\n"
    wf.write_text(path, text, append=append)
    return {
        "path": str(path),
        "bytes_written": len(text.encode("utf-8")),
        "append": append,
    }


DEFAULT_HANDLERS: dict[str, ToolHandler] = {
    "local_echo": _handle_local_echo,
    "file_write": _handle_file_write,
}


class ToolGateway:
    """Execute only previously approved actions, with idempotent replay."""

    def __init__(
        self,
        cfg: AppConfig,
        store: ApprovalStore,
        *,
        handlers: dict[str, ToolHandler] | None = None,
    ) -> None:
        self._cfg = cfg
        self._store = store
        self._handlers = dict(handlers or DEFAULT_HANDLERS)

    def execute(
        self,
        approval_id: str,
        *,
        idempotency_key: str,
        actor: str,
    ) -> DispatchResult:
        key = idempotency_key.strip()
        if not key:
            raise DispatchDenied("Idempotency-Key is required for approved tool dispatch.")
        if len(key) > 200:
            raise DispatchDenied("Idempotency-Key exceeds 200 characters.")

        cached = self._store.get_idempotency_record(key)
        if cached is not None:
            if cached["approval_id"] != approval_id:
                raise ApprovalConflict(
                    "Idempotency key is already bound to a different approval.",
                    safe_details={
                        "idempotency_key": key,
                        "approval_id": cached["approval_id"],
                    },
                )
            get_telemetry().emit(
                "dispatch.replayed",
                approval_id=approval_id,
                idempotency_key=key,
            )
            payload = cached["result"]
            return DispatchResult(
                approval_id=approval_id,
                tool_name=str(payload.get("tool_name") or "unknown"),
                status=str(payload.get("status") or "executed"),
                idempotency_key=key,
                replayed=True,
                result=dict(payload.get("result") or {}),
                action_digest=str(payload.get("action_digest") or ""),
            )

        approval = self._store.get_approval(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise DispatchDenied(
                f"Approval status is {approval.status.value}; only approved requests may execute.",
                safe_details={"approval_id": approval.id, "status": approval.status.value},
            )

        handler = self._handlers.get(approval.tool_name)
        if handler is None:
            raise ToolNotDispatchable(
                f"Tool is not registered for gateway dispatch: {approval.tool_name}",
                safe_details={"tool_name": approval.tool_name},
            )

        intent = approval.to_policy_input()
        if intent.action_digest != approval.action_digest:
            raise DispatchDenied(
                "Stored approval inputs no longer match the approved action digest.",
                safe_details={"approval_id": approval.id},
            )

        try:
            result_payload = handler(self._cfg, intent.inputs)
            updated = self._store.record_execution(
                approval.id,
                succeeded=True,
                result_summary=f"Executed {approval.tool_name}",
                actor=actor,
            )
            status = updated.status.value
        except AtticusError as exc:
            self._store.record_execution(
                approval.id,
                succeeded=False,
                result_summary=f"Dispatch failed: {exc.message}"[:2000],
                actor=actor,
            )
            get_telemetry().emit(
                "dispatch.failed",
                approval_id=approval.id,
                tool_name=approval.tool_name,
            )
            raise
        except Exception as exc:  # noqa: BLE001 — normalize unexpected handler failures
            summary = f"Dispatch failed: {exc.__class__.__name__}"
            self._store.record_execution(
                approval.id,
                succeeded=False,
                result_summary=summary,
                actor=actor,
            )
            get_telemetry().emit(
                "dispatch.failed",
                approval_id=approval.id,
                tool_name=approval.tool_name,
            )
            raise DispatchDenied(
                summary,
                code="dispatch_failed",
                status_code=500,
                safe_details={"approval_id": approval.id, "tool_name": approval.tool_name},
            ) from exc

        envelope = {
            "tool_name": approval.tool_name,
            "status": status,
            "action_digest": approval.action_digest,
            "result": result_payload,
        }
        self._store.put_idempotency_record(
            key,
            approval_id=approval.id,
            result=envelope,
        )
        get_telemetry().emit(
            "dispatch.executed",
            approval_id=approval.id,
            tool_name=approval.tool_name,
            idempotency_key=key,
        )
        return DispatchResult(
            approval_id=approval.id,
            tool_name=approval.tool_name,
            status=status,
            idempotency_key=key,
            replayed=False,
            result=result_payload,
            action_digest=approval.action_digest,
        )
