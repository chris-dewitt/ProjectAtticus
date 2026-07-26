"""Bounded run orchestrator (Track B M1 + M4 trace spans).

Framework-independent state machine with persisted checkpoints. Provider calls
go through the injected ``LLMProvider`` protocol — tests use ``MockProvider``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from atticus.core.errors import AtticusError, ProviderError
from atticus.core.persona import build_system_prompt
from atticus.core.telemetry import get_correlation_id, get_telemetry
from atticus.providers.base import LLMProvider
from atticus.runs.models import CheckpointRecord, RunRecord, RunStatus
from atticus.runs.store import RunStore
from atticus.traces.models import SpanKind
from atticus.traces.store import TraceStore


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class RunConflict(AtticusError):
    code = "run_conflict"
    status_code = 409


class BoundedRunOrchestrator:
    """Execute a single-turn bounded run with cancel and terminal failure."""

    def __init__(
        self,
        store: RunStore,
        *,
        provider_factory: Callable[[str], LLMProvider],
        repo_root: Path | None = None,
        max_messages: int = 32,
        include_system_prompt: bool = True,
        trace_store: TraceStore | None = None,
    ) -> None:
        self._store = store
        self._provider_factory = provider_factory
        self._repo_root = repo_root
        self._max_messages = max_messages
        self._include_system_prompt = include_system_prompt
        self._trace_store = trace_store

    def execute(self, run_id: str) -> RunRecord:
        run = self._store.get_run(run_id)
        if run.status.terminal:
            return run
        if run.status != RunStatus.QUEUED:
            raise RunConflict(
                f"Run {run_id} is not executable from status={run.status.value}",
                safe_details={"run_id": run_id, "status": run.status.value},
            )

        run = self._store.get_run(run_id)
        if run.cancel_requested:
            return self._mark_cancelled(run, reason="cancel_requested_before_start")

        root_span_id = None
        if self._trace_store is not None:
            root = self._trace_store.start_span(
                run_id=run.id,
                name="bounded_run",
                kind=SpanKind.RUN,
                attributes={"provider": run.provider, "mode": run.mode},
                correlation_id=run.correlation_id or get_correlation_id(),
            )
            root_span_id = root.id

        run.status = RunStatus.RUNNING
        self._checkpoint(run, "validate_request", {"message_count": len(run.input_messages)})
        self._store.save_run(run)

        try:
            messages = self._assemble_messages(run)
            self._checkpoint(run, "assemble_context", {"assembled_count": len(messages)})
            self._store.save_run(run)

            run = self._store.get_run(run_id)
            if run.cancel_requested:
                return self._mark_cancelled(
                    run,
                    reason="cancel_requested_before_provider",
                    root_span_id=root_span_id,
                )

            provider = self._provider_factory(run.provider)
            self._checkpoint(
                run,
                "execute_provider",
                {"provider": provider.name},
            )
            self._store.save_run(run)

            provider_span_id = None
            if self._trace_store is not None:
                provider_span = self._trace_store.start_span(
                    run_id=run.id,
                    name="provider.generate",
                    kind=SpanKind.PROVIDER,
                    parent_span_id=root_span_id,
                    attributes={"provider": provider.name},
                )
                provider_span_id = provider_span.id

            with get_telemetry().span(
                "run.provider_generate",
                run_id=run.id,
                provider=provider.name,
            ):
                output = provider.generate(messages, mode=run.mode)

            if self._trace_store is not None and provider_span_id:
                self._trace_store.end_span(
                    provider_span_id,
                    attributes={"output_chars": len(output)},
                )

            run = self._store.get_run(run_id)
            if run.cancel_requested:
                return self._mark_cancelled(
                    run,
                    reason="cancel_requested_after_provider",
                    root_span_id=root_span_id,
                )

            run.output_text = output
            run.status = RunStatus.SUCCEEDED
            self._checkpoint(run, "finalize", {"output_chars": len(output)})
            self._store.save_run(run)
            if run.conversation_id and output:
                self._store.add_message(
                    run.conversation_id,
                    role="assistant",
                    content=output,
                )
            if self._trace_store is not None and root_span_id:
                self._trace_store.end_span(root_span_id, status="ok")
            get_telemetry().emit(
                "run.succeeded",
                run_id=run.id,
                provider=run.provider,
                correlation_id=get_correlation_id(),
            )
            return run
        except AtticusError as exc:
            return self._mark_failed(
                run_id,
                code=exc.code,
                message=exc.message,
                root_span_id=root_span_id,
            )
        except Exception as exc:  # noqa: BLE001 — normalize unexpected provider failures
            return self._mark_failed(
                run_id,
                code="provider_error",
                message=f"Provider failed: {exc.__class__.__name__}",
                root_span_id=root_span_id,
            )

    def cancel(self, run_id: str) -> RunRecord:
        run = self._store.get_run(run_id)
        if run.status.terminal:
            raise RunConflict(
                f"Cannot cancel terminal run in status={run.status.value}",
                safe_details={"run_id": run_id, "status": run.status.value},
            )
        run.cancel_requested = True
        if run.status == RunStatus.QUEUED:
            return self._mark_cancelled(run, reason="cancelled_while_queued")
        self._store.save_run(run)
        get_telemetry().emit("run.cancel_requested", run_id=run.id)
        return run

    def _assemble_messages(self, run: RunRecord) -> list[dict[str, Any]]:
        if len(run.input_messages) > self._max_messages:
            raise ProviderError(
                f"Run exceeds max_messages={self._max_messages}",
                code="run_too_large",
                status_code=400,
                safe_details={"max_messages": self._max_messages},
            )
        messages: list[dict[str, Any]] = []
        if self._include_system_prompt and self._repo_root is not None:
            try:
                system = build_system_prompt(self._repo_root, run.mode)
            except Exception:  # noqa: BLE001 — persona optional for API smoke
                system = (
                    "You are Atticus, a local-first assistant. Be helpful, precise, "
                    "and never claim actions you did not take."
                )
            messages.append({"role": "system", "content": system})
        for item in run.input_messages:
            role = str(item.get("role", "user"))
            content = str(item.get("content", ""))
            if role not in {"system", "user", "assistant"}:
                raise ProviderError(
                    f"Unsupported message role: {role}",
                    code="invalid_message",
                    status_code=400,
                )
            if not content.strip():
                raise ProviderError(
                    "Message content must not be empty",
                    code="invalid_message",
                    status_code=400,
                )
            messages.append({"role": role, "content": content})
        if not any(m["role"] == "user" for m in messages):
            raise ProviderError(
                "At least one user message is required",
                code="invalid_message",
                status_code=400,
            )
        return messages

    def _checkpoint(self, run: RunRecord, name: str, detail: dict[str, Any]) -> None:
        run.checkpoints.append(CheckpointRecord(name=name, at=_utc_now(), detail=detail))

    def _mark_cancelled(
        self,
        run: RunRecord,
        *,
        reason: str,
        root_span_id: str | None = None,
    ) -> RunRecord:
        run.status = RunStatus.CANCELLED
        run.cancel_requested = True
        run.error_code = "cancelled"
        run.error_message = reason
        self._checkpoint(run, "cancelled", {"reason": reason})
        self._store.save_run(run)
        if self._trace_store is not None and root_span_id:
            self._trace_store.end_span(root_span_id, status="cancelled", attributes={"reason": reason})
        get_telemetry().emit("run.cancelled", run_id=run.id, reason=reason)
        return run

    def _mark_failed(
        self,
        run_id: str,
        *,
        code: str,
        message: str,
        root_span_id: str | None = None,
    ) -> RunRecord:
        run = self._store.get_run(run_id)
        run.status = RunStatus.FAILED
        run.error_code = code
        run.error_message = message
        self._checkpoint(run, "failed", {"code": code})
        self._store.save_run(run)
        if self._trace_store is not None and root_span_id:
            self._trace_store.end_span(root_span_id, status="error", attributes={"code": code})
        get_telemetry().emit("run.failed", run_id=run.id, code=code)
        return run
