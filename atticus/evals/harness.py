"""Deterministic evaluation harness (golden + adversarial cases)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from atticus.core.telemetry import get_telemetry


@dataclass(frozen=True)
class EvalCase:
    id: str
    name: str
    kind: str  # golden | adversarial | smoke
    input: dict[str, Any]
    expect: dict[str, Any]


@dataclass
class EvalCaseResult:
    case_id: str
    name: str
    kind: str
    passed: bool
    detail: str
    duration_ms: float
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "kind": self.kind,
            "passed": self.passed,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "metrics": dict(self.metrics),
        }


@dataclass
class EvalReport:
    suite_id: str
    version: str
    passed: int
    failed: int
    results: list[EvalCaseResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "version": self.version,
            "passed": self.passed,
            "failed": self.failed,
            "ok": self.ok,
            "metrics": dict(self.metrics),
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class EvalSuite:
    id: str
    version: str
    cases: list[EvalCase]

    @classmethod
    def load(cls, path: Path) -> "EvalSuite":
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = [
            EvalCase(
                id=str(c["id"]),
                name=str(c["name"]),
                kind=str(c.get("kind", "golden")),
                input=dict(c.get("input") or {}),
                expect=dict(c.get("expect") or {}),
            )
            for c in data.get("cases", [])
        ]
        return cls(id=str(data["id"]), version=str(data.get("version", "1")), cases=cases)


Checker = Callable[[EvalCase], tuple[bool, str, dict[str, Any]]]


def run_suite(suite: EvalSuite, checker: Checker) -> EvalReport:
    results: list[EvalCaseResult] = []
    passed = 0
    failed = 0
    started = time.perf_counter()
    for case in suite.cases:
        t0 = time.perf_counter()
        ok, detail, metrics = checker(case)
        duration = round((time.perf_counter() - t0) * 1000, 3)
        results.append(
            EvalCaseResult(
                case_id=case.id,
                name=case.name,
                kind=case.kind,
                passed=ok,
                detail=detail,
                duration_ms=duration,
                metrics=metrics,
            )
        )
        if ok:
            passed += 1
        else:
            failed += 1
    total_ms = round((time.perf_counter() - started) * 1000, 3)
    report = EvalReport(
        suite_id=suite.id,
        version=suite.version,
        passed=passed,
        failed=failed,
        results=results,
        metrics={"duration_ms": total_ms, "case_count": len(suite.cases)},
    )
    get_telemetry().emit(
        "eval.suite_completed",
        suite_id=suite.id,
        passed=passed,
        failed=failed,
        duration_ms=total_ms,
    )
    return report
