"""SQLite persistence for immutable policy decisions and approval audit."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from atticus.core.errors import AtticusError
from atticus.core.permissions import PermissionClass
from atticus.policy.models import (
    ApprovalRequest,
    ApprovalStatus,
    PolicyDecision,
    PolicyEffect,
    PolicyInput,
    RiskLevel,
    new_id,
)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _sanitize_inputs_for_storage(inputs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in inputs.items():
        if isinstance(value, str) and len(value) > 200_000:
            out[key] = value[:200_000] + "…[truncated]"
        else:
            out[key] = value
    return out


class ApprovalNotFound(AtticusError):
    code = "approval_not_found"
    status_code = 404


class ApprovalConflict(AtticusError):
    code = "approval_conflict"
    status_code = 409


class ApprovalAuthenticationError(AtticusError):
    code = "approval_authentication_failed"
    status_code = 401


class ApprovalStore:
    """Durable, append-oriented policy/approval store."""

    def __init__(self, sqlite_path: Path) -> None:
        self._path = sqlite_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS policy_decisions (
              id TEXT PRIMARY KEY,
              effect TEXT NOT NULL,
              risk TEXT NOT NULL,
              reasons_json TEXT NOT NULL,
              action_digest TEXT NOT NULL,
              tool_name TEXT NOT NULL,
              permission_class TEXT NOT NULL,
              action_summary TEXT NOT NULL,
              actor TEXT NOT NULL,
              created_at TEXT NOT NULL,
              correlation_id TEXT
            );

            CREATE TABLE IF NOT EXISTS approval_requests (
              id TEXT PRIMARY KEY,
              policy_decision_id TEXT NOT NULL,
              action_digest TEXT NOT NULL,
              tool_name TEXT NOT NULL,
              permission_class TEXT NOT NULL,
              action_summary TEXT NOT NULL,
              risk TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              decided_at TEXT,
              actor TEXT,
              rationale TEXT,
              execution_result TEXT,
              correlation_id TEXT,
              inputs_json TEXT NOT NULL DEFAULT '{}',
              resource TEXT,
              request_actor TEXT NOT NULL DEFAULT 'boss',
              external_data INTEGER NOT NULL DEFAULT 0,
              destructive INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY (policy_decision_id) REFERENCES policy_decisions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_approvals_status_created
              ON approval_requests (status, created_at);

            CREATE TABLE IF NOT EXISTS policy_audit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_type TEXT NOT NULL,
              entity_type TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              actor TEXT,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_policy_audit_entity
              ON policy_audit_events (entity_type, entity_id, id);

            CREATE TABLE IF NOT EXISTS idempotency_records (
              idempotency_key TEXT PRIMARY KEY,
              approval_id TEXT NOT NULL,
              result_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (approval_id) REFERENCES approval_requests(id)
            );
            """
        )
        self._migrate_approval_columns()
        self._conn.commit()

    def _migrate_approval_columns(self) -> None:
        cols = {
            str(row[1])
            for row in self._conn.execute("PRAGMA table_info(approval_requests)").fetchall()
        }
        migrations = {
            "inputs_json": "ALTER TABLE approval_requests ADD COLUMN inputs_json TEXT NOT NULL DEFAULT '{}'",
            "resource": "ALTER TABLE approval_requests ADD COLUMN resource TEXT",
            "request_actor": "ALTER TABLE approval_requests ADD COLUMN request_actor TEXT NOT NULL DEFAULT 'boss'",
            "external_data": "ALTER TABLE approval_requests ADD COLUMN external_data INTEGER NOT NULL DEFAULT 0",
            "destructive": "ALTER TABLE approval_requests ADD COLUMN destructive INTEGER NOT NULL DEFAULT 0",
        }
        for name, sql in migrations.items():
            if name not in cols:
                self._conn.execute(sql)

    def record_decision(self, decision: PolicyDecision) -> PolicyDecision:
        self._conn.execute(
            """
            INSERT INTO policy_decisions (
              id, effect, risk, reasons_json, action_digest, tool_name,
              permission_class, action_summary, actor, created_at, correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.id,
                decision.effect.value,
                decision.risk.value,
                json.dumps(list(decision.reasons)),
                decision.action_digest,
                decision.tool_name,
                decision.permission_class.value,
                decision.action_summary,
                decision.actor,
                decision.created_at,
                decision.correlation_id,
            ),
        )
        self._audit(
            "policy_evaluated",
            "policy_decision",
            decision.id,
            decision.actor,
            {
                "effect": decision.effect.value,
                "risk": decision.risk.value,
                "action_digest": decision.action_digest,
            },
        )
        self._conn.commit()
        return decision

    def create_approval(
        self,
        decision: PolicyDecision,
        *,
        intent: PolicyInput,
        ttl_seconds: int,
    ) -> ApprovalRequest:
        if decision.effect != PolicyEffect.REQUIRE_APPROVAL:
            raise ApprovalConflict(
                f"Policy effect is {decision.effect.value}; no approval request is needed.",
                safe_details={"policy_decision_id": decision.id},
            )
        if intent.action_digest != decision.action_digest:
            raise ApprovalConflict(
                "Intent digest does not match policy decision digest.",
                safe_details={"policy_decision_id": decision.id},
            )
        now = _utc_now()
        approval = ApprovalRequest(
            id=new_id("apr"),
            policy_decision_id=decision.id,
            action_digest=decision.action_digest,
            tool_name=decision.tool_name,
            permission_class=decision.permission_class,
            action_summary=decision.action_summary,
            risk=decision.risk,
            status=ApprovalStatus.PENDING,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=max(30, ttl_seconds))).isoformat(),
            inputs=_sanitize_inputs_for_storage(intent.inputs),
            resource=intent.resource,
            request_actor=intent.actor,
            external_data=intent.external_data,
            destructive=intent.destructive,
            correlation_id=decision.correlation_id,
        )
        self._conn.execute(
            """
            INSERT INTO approval_requests (
              id, policy_decision_id, action_digest, tool_name, permission_class,
              action_summary, risk, status, created_at, expires_at, correlation_id,
              inputs_json, resource, request_actor, external_data, destructive
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval.id,
                approval.policy_decision_id,
                approval.action_digest,
                approval.tool_name,
                approval.permission_class.value,
                approval.action_summary,
                approval.risk.value,
                approval.status.value,
                approval.created_at,
                approval.expires_at,
                approval.correlation_id,
                json.dumps(approval.inputs, sort_keys=True, default=str),
                approval.resource,
                approval.request_actor,
                1 if approval.external_data else 0,
                1 if approval.destructive else 0,
            ),
        )
        self._audit(
            "approval_requested",
            "approval",
            approval.id,
            decision.actor,
            {
                "action_digest": approval.action_digest,
                "risk": approval.risk.value,
                "tool_name": approval.tool_name,
            },
        )
        self._conn.commit()
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        row = self._conn.execute(
            "SELECT * FROM approval_requests WHERE id = ?",
            (approval_id,),
        ).fetchone()
        if row is None:
            raise ApprovalNotFound(
                f"Approval not found: {approval_id}",
                safe_details={"approval_id": approval_id},
            )
        approval = self._row_to_approval(row)
        if (
            approval.status == ApprovalStatus.PENDING
            and datetime.fromisoformat(approval.expires_at) <= _utc_now()
        ):
            self._conn.execute(
                "UPDATE approval_requests SET status = ? WHERE id = ?",
                (ApprovalStatus.EXPIRED.value, approval.id),
            )
            self._audit(
                "approval_expired",
                "approval",
                approval.id,
                None,
                {"action_digest": approval.action_digest},
            )
            self._conn.commit()
            return self.get_approval(approval_id)
        return approval

    def list_approvals(
        self,
        *,
        status: ApprovalStatus | None = None,
        limit: int = 50,
    ) -> list[ApprovalRequest]:
        if status is None:
            rows = self._conn.execute(
                "SELECT id FROM approval_requests ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id FROM approval_requests
                WHERE status = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (status.value, max(1, min(limit, 200))),
            ).fetchall()
        approvals = [self.get_approval(str(row["id"])) for row in rows]
        if status is not None:
            approvals = [item for item in approvals if item.status == status]
        return approvals

    def decide(
        self,
        approval_id: str,
        *,
        approve: bool,
        actor: str,
        action_digest: str,
        confirmation: str,
        rationale: str | None = None,
    ) -> ApprovalRequest:
        approval = self.get_approval(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalConflict(
                f"Approval is already {approval.status.value}.",
                safe_details={"approval_id": approval.id, "status": approval.status.value},
            )
        if action_digest != approval.action_digest:
            raise ApprovalConflict(
                "Action digest does not match the approved request.",
                safe_details={"approval_id": approval.id},
            )
        verb = "APPROVE" if approve else "DENY"
        expected = f"{verb} {approval.confirmation_hint}"
        if confirmation != expected:
            raise ApprovalConflict(
                f"Confirmation mismatch. Required exact phrase: {expected}",
                safe_details={"approval_id": approval.id, "required_confirmation": expected},
            )
        now = _utc_now().isoformat()
        status = ApprovalStatus.APPROVED if approve else ApprovalStatus.DENIED
        self._conn.execute(
            """
            UPDATE approval_requests
            SET status = ?, decided_at = ?, actor = ?, rationale = ?
            WHERE id = ?
            """,
            (status.value, now, actor, rationale, approval.id),
        )
        self._audit(
            "approval_decided",
            "approval",
            approval.id,
            actor,
            {
                "decision": status.value,
                "action_digest": approval.action_digest,
                "rationale": rationale,
            },
        )
        self._conn.commit()
        return self.get_approval(approval.id)

    def record_execution(
        self,
        approval_id: str,
        *,
        succeeded: bool,
        result_summary: str,
        actor: str,
    ) -> ApprovalRequest:
        approval = self.get_approval(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise ApprovalConflict(
                "Only an approved request can record execution.",
                safe_details={"approval_id": approval.id, "status": approval.status.value},
            )
        status = ApprovalStatus.EXECUTED if succeeded else ApprovalStatus.FAILED
        self._conn.execute(
            """
            UPDATE approval_requests
            SET status = ?, execution_result = ?
            WHERE id = ?
            """,
            (status.value, result_summary, approval.id),
        )
        self._audit(
            "approval_execution_recorded",
            "approval",
            approval.id,
            actor,
            {"status": status.value, "result_summary": result_summary},
        )
        self._conn.commit()
        return self.get_approval(approval.id)

    def get_idempotency_record(self, key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT idempotency_key, approval_id, result_json, created_at
            FROM idempotency_records
            WHERE idempotency_key = ?
            """,
            (key,),
        ).fetchone()
        if row is None:
            return None
        return {
            "idempotency_key": str(row["idempotency_key"]),
            "approval_id": str(row["approval_id"]),
            "result": json.loads(row["result_json"]),
            "created_at": str(row["created_at"]),
        }

    def put_idempotency_record(
        self,
        key: str,
        *,
        approval_id: str,
        result: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO idempotency_records (
              idempotency_key, approval_id, result_json, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                key,
                approval_id,
                json.dumps(result, sort_keys=True, default=str),
                _utc_now().isoformat(),
            ),
        )
        self._audit(
            "idempotency_recorded",
            "approval",
            approval_id,
            None,
            {"idempotency_key": key},
        )
        self._conn.commit()

    def list_audit_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM policy_audit_events
            ORDER BY id DESC LIMIT ?
            """,
            (max(1, min(limit, 500)),),
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "event_type": str(row["event_type"]),
                "entity_type": str(row["entity_type"]),
                "entity_id": str(row["entity_id"]),
                "actor": row["actor"],
                "payload": json.loads(row["payload_json"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def _audit(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str | None,
        payload: dict[str, Any],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO policy_audit_events (
              event_type, entity_type, entity_id, actor, payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                entity_type,
                entity_id,
                actor,
                json.dumps(payload, sort_keys=True, default=str),
                _utc_now().isoformat(),
            ),
        )

    @staticmethod
    def _row_to_approval(row: sqlite3.Row) -> ApprovalRequest:
        keys = set(row.keys())
        inputs_raw = row["inputs_json"] if "inputs_json" in keys else "{}"
        return ApprovalRequest(
            id=str(row["id"]),
            policy_decision_id=str(row["policy_decision_id"]),
            action_digest=str(row["action_digest"]),
            tool_name=str(row["tool_name"]),
            permission_class=PermissionClass(str(row["permission_class"])),
            action_summary=str(row["action_summary"]),
            risk=RiskLevel(str(row["risk"])),
            status=ApprovalStatus(str(row["status"])),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]),
            inputs=json.loads(inputs_raw or "{}"),
            resource=row["resource"] if "resource" in keys else None,
            request_actor=str(row["request_actor"]) if "request_actor" in keys and row["request_actor"] else "boss",
            external_data=bool(row["external_data"]) if "external_data" in keys else False,
            destructive=bool(row["destructive"]) if "destructive" in keys else False,
            decided_at=row["decided_at"],
            actor=row["actor"],
            rationale=row["rationale"],
            execution_result=row["execution_result"],
            correlation_id=row["correlation_id"],
        )
