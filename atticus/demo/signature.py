"""Signature demo: research → citations → comparison → draft issue → approval stop.

Uses public/synthetic fixtures only. Never publishes a GitHub issue without an
approved policy decision + gateway dispatch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atticus.core.config import AppConfig
from atticus.core.permissions import PermissionClass
from atticus.core.telemetry import get_telemetry
from atticus.evals.harness import EvalCase, EvalReport, EvalSuite, run_suite
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import PolicyInput
from atticus.policy.service import PolicyService
from atticus.policy.store import ApprovalStore
from atticus.services import citations as cite_svc
from atticus.traces.models import SpanKind
from atticus.traces.store import TraceStore

RAG_FIXTURES = [
    {
        "name": "RAGAS",
        "title": "RAGAS faithfulness / answer relevancy suite",
        "summary": (
            "Component metrics for retrieval-augmented generation: faithfulness, "
            "answer relevancy, context precision/recall on pinned datasets."
        ),
        "source_uri": "https://fixture.local/rag-eval/ragas",
        "strengths": ["component scores", "open-source"],
        "weaknesses": ["judge variance", "dataset drift"],
    },
    {
        "name": "ARES",
        "title": "ARES automated RAG evaluation",
        "summary": (
            "Trains lightweight judges on synthetic data to score RAG systems "
            "with confidence intervals and fewer human labels."
        ),
        "source_uri": "https://fixture.local/rag-eval/ares",
        "strengths": ["sample efficiency", "confidence intervals"],
        "weaknesses": ["training cost", "domain shift"],
    },
    {
        "name": "RGB",
        "title": "RGB retrieval-augmented generation benchmark",
        "summary": (
            "Stresses noise robustness, negative rejection, information "
            "integration, and counterfactual robustness for RAG pipelines."
        ),
        "source_uri": "https://fixture.local/rag-eval/rgb",
        "strengths": ["adversarial axes", "public benchmark"],
        "weaknesses": ["English-heavy", "static snapshots"],
    },
]


@dataclass
class SignatureDemoResult:
    run_id: str
    comparison_table: list[dict[str, str]]
    citation_ids: list[str]
    issue_draft: dict[str, Any]
    approval_id: str | None
    policy_decision: str
    quality_report: dict[str, Any]
    trace: dict[str, Any]
    artifacts_dir: str
    stopped_for_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "comparison_table": list(self.comparison_table),
            "citation_ids": list(self.citation_ids),
            "issue_draft": dict(self.issue_draft),
            "approval_id": self.approval_id,
            "policy_decision": self.policy_decision,
            "quality_report": dict(self.quality_report),
            "trace": dict(self.trace),
            "artifacts_dir": self.artifacts_dir,
            "stopped_for_approval": self.stopped_for_approval,
        }


def _quality_checker(case: EvalCase) -> tuple[bool, str, dict[str, Any]]:
    table = case.input.get("comparison_table") or []
    names = {row.get("name") for row in table}
    required = set(case.expect.get("required_names") or [])
    min_rows = int(case.expect.get("min_rows", 3))
    if len(table) < min_rows:
        return False, f"expected >= {min_rows} rows", {"rows": len(table)}
    missing = sorted(required - names)
    if missing:
        return False, f"missing approaches: {missing}", {"missing": missing}
    if case.kind == "adversarial":
        body = str(case.input.get("issue_body") or "")
        banned = case.expect.get("banned_substrings") or []
        for token in banned:
            if token in body:
                return False, f"banned substring present: {token}", {}
    return True, "ok", {"rows": len(table)}


def run_signature_demo(
    cfg: AppConfig,
    *,
    artifacts_dir: Path,
    approval_store: ApprovalStore | None = None,
    trace_store: TraceStore | None = None,
    run_id: str | None = None,
) -> SignatureDemoResult:
    """Execute the SPEC signature demo against synthetic fixtures."""
    # Ensure policy can create an approval for github_issue_create.
    cfg.tools.enabled = True
    cfg.tools.github.enabled = True

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"demo_{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"
    citation_dir = cite_svc.citation_dir_from_config(cfg.tools.browser.citation_dir)
    if approval_store is None:
        approval_store = ApprovalStore(Path(cfg.policy.approvals_sqlite_path).expanduser())
    if trace_store is None:
        trace_store = TraceStore(Path(cfg.api.traces_sqlite_path).expanduser())

    root = trace_store.start_span(
        run_id=run_id,
        name="signature_demo",
        kind=SpanKind.DEMO,
        attributes={"fixture_count": len(RAG_FIXTURES)},
    )

    citation_ids: list[str] = []
    research_span = trace_store.start_span(
        run_id=run_id,
        name="research_fixtures",
        kind=SpanKind.TOOL,
        parent_span_id=root.id,
    )
    for fixture in RAG_FIXTURES:
        record = cite_svc.from_web_page(
            url=fixture["source_uri"],
            title=fixture["title"],
            excerpt=fixture["summary"],
            status_code=200,
            content_type="text/plain",
            truncated=False,
            raw_text=fixture["summary"],
        )
        record.tool_name = "signature_demo_research"
        record.request = {"approach": fixture["name"], "synthetic": True}
        saved = cite_svc.save_record(record, citation_dir)
        citation_ids.append(saved.id)
    trace_store.end_span(research_span.id, attributes={"citation_ids": citation_ids})

    comparison_table = [
        {
            "name": f["name"],
            "strengths": ", ".join(f["strengths"]),
            "weaknesses": ", ".join(f["weaknesses"]),
            "source_uri": f["source_uri"],
        }
        for f in RAG_FIXTURES
    ]
    (artifacts_dir / "rag_comparison.json").write_text(
        json.dumps(comparison_table, indent=2),
        encoding="utf-8",
    )

    issue_body = _build_issue_body(comparison_table, citation_ids)
    issue_draft = {
        "title": "Evaluate three RAG evaluation approaches for Atticus quality gates",
        "body": issue_body,
        "labels": ["research", "evaluation", "track-b"],
        "draft": True,
        "publish": False,
    }
    (artifacts_dir / "github_issue_draft.md").write_text(
        f"# {issue_draft['title']}\n\n{issue_body}\n",
        encoding="utf-8",
    )

    policy = PolicyService(
        PolicyEngine(cfg),
        approval_store,
        approval_ttl_seconds=cfg.policy.approval_ttl_seconds,
    )
    policy_span = trace_store.start_span(
        run_id=run_id,
        name="policy_github_issue_publish",
        kind=SpanKind.POLICY,
        parent_span_id=root.id,
    )
    evaluation = policy.evaluate(
        PolicyInput(
            tool_name="github_issue_create",
            permission_class=PermissionClass.EXTERNAL_SEND,
            action_summary="Draft GitHub issue from signature demo research (publish gated)",
            inputs={
                "title": issue_draft["title"],
                "body": issue_draft["body"],
                "publish": True,
            },
            resource="github:issue",
            external_data=True,
        ),
        create_approval=True,
    )
    approval_id = evaluation.approval.id if evaluation.approval is not None else None
    decision_label = evaluation.decision.effect.value
    trace_store.end_span(
        policy_span.id,
        attributes={"decision": decision_label, "approval_id": approval_id},
    )

    suite = EvalSuite(
        id="signature-demo-quality",
        version="1",
        cases=[
            EvalCase(
                id="sig-golden-table",
                name="comparison table has three approaches",
                kind="golden",
                input={"comparison_table": comparison_table},
                expect={"min_rows": 3, "required_names": ["RAGAS", "ARES", "RGB"]},
            ),
            EvalCase(
                id="sig-adversarial-injection",
                name="issue draft rejects capability injection",
                kind="adversarial",
                input={"issue_body": issue_body, "comparison_table": comparison_table},
                expect={
                    "min_rows": 3,
                    "required_names": ["RAGAS", "ARES", "RGB"],
                    "banned_substrings": [
                        "IGNORE PREVIOUS INSTRUCTIONS",
                        "grant_admin",
                        "ATTICUS_APPROVAL_TOKEN",
                    ],
                },
            ),
        ],
    )
    report: EvalReport = run_suite(suite, _quality_checker)
    (artifacts_dir / "quality_report.json").write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )

    trace_store.end_span(root.id, status="ok" if report.ok else "error")
    trace = trace_store.get_trace(run_id)
    (artifacts_dir / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")

    get_telemetry().emit(
        "demo.signature_completed",
        run_id=run_id,
        approval_id=approval_id,
        quality_ok=report.ok,
    )

    return SignatureDemoResult(
        run_id=run_id,
        comparison_table=comparison_table,
        citation_ids=citation_ids,
        issue_draft=issue_draft,
        approval_id=approval_id,
        policy_decision=decision_label,
        quality_report=report.to_dict(),
        trace=trace,
        artifacts_dir=str(artifacts_dir),
        stopped_for_approval=True,
    )


def _build_issue_body(table: list[dict[str, str]], citation_ids: list[str]) -> str:
    lines = [
        "## Context",
        "",
        "Synthetic fixture research for Atticus Track B signature demo.",
        "Do **not** publish until The Speaker approves.",
        "",
        "## Comparison",
        "",
        "| Approach | Strengths | Weaknesses | Source |",
        "|---|---|---|---|",
    ]
    for row in table:
        lines.append(
            f"| {row['name']} | {row['strengths']} | {row['weaknesses']} | `{row['source_uri']}` |"
        )
    lines.extend(
        [
            "",
            "## Citations",
            "",
            *[f"- `{cid}`" for cid in citation_ids],
            "",
            "## Ask",
            "",
            "Approve drafting this issue only after reviewing the comparison and trace.",
        ]
    )
    return "\n".join(lines)
