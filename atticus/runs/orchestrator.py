"""Bounded run orchestrator (Track B M1).

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
    ) -> None:
        self._store = store
        self._provider_factory = provider_factory
        self._repo_root = repo_root
        self._max_messages = max_messages
        self._include_system_prompt = include_system_prompt

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

        run.status = RunStatus.RUNNING
        self._checkpoint(run, "validate_request", {"message_count": len(run.input_messages)})
        self._store.save_run(run)

        try:
            messages = self._assemble_messages(run)
            self._checkpoint(run, "assemble_context", {"assembled_count": len(messages)})
            self._store.save_run(run)

            run = self._store.get_run(run_id)
            if run.cancel_requested:
                return self._mark_cancelled(run, reason="cancel_requested_before_provider")

            provider = self._provider_factory(run.provider)
            self._checkpoint(
                run,
                "execute_provider",
                {"provider": provider.name},
            )
            self._store.save_run(run)

            with get_telemetry().span(
                "run.provider_generate",
                run_id=run.id,
                provider=provider.name,
            ):
                output = provider.generate(messages, mode=run.mode)

            run = self._store.get_run(run_id)
            if run.cancel_requested:
                # Provider already returned; still honor cooperative cancel if flagged mid-flight.
                return self._mark_cancelled(run, reason="cancel_requested_after_provider")

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
            get_telemetry().emit(
                "run.succeeded",
                run_id=run.id,
                provider=run.provider,
                correlation_id=get_correlation_id(),
            )
            return run
        except AtticusError as exc:
            return self._mark_failed(run_id, code=exc.code, message=exc.message)
        except Exception as exc:  # noqa: BLE001 — normalize unexpected provider failures
            return self._mark_failed(
                run_id,
                code="provider_error",
                message=f"Provider failed: {exc.__class__.__name__}",
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

    def _mark_cancelled(self, run: RunRecord, *, reason: str) -> RunRecord:
        run.status = RunStatus.CANCELLED
        run.cancel_requested = True
        run.error_code = "cancelled"
        run.error_message = reason
        self._checkpoint(run, "cancelled", {"reason": reason})
        self._store.save_run(run)
        get_telemetry().emit("run.cancelled", run_id=run.id, reason=reason)
        return run

    def _mark_failed(self, run_id: str, *, code: str, message: str) -> RunRecord:
        run = self._store.get_run(run_id)
        run.status = RunStatus.FAILED
        run.error_code = code
        run.error_message = message
        self._checkpoint(run, "failed", {"code": code})
        self._store.save_run(run)
        get_telemetry().emit("run.failed", run_id=run.id, code=code)
        return run
