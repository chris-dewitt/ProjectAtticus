"""HTTP + CLI-adjacent evaluation endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_telemetry
from atticus.evals.harness import EvalCase, EvalSuite, run_suite
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import PolicyInput
from atticus.core.permissions import PermissionClass


class EvalSuiteMissing(AtticusError):
    code = "eval_suite_missing"
    status_code = 404


def _default_checker_factory(request: Request):
    cfg = request.app.state.config
    engine = PolicyEngine(cfg)

    def checker(case: EvalCase) -> tuple[bool, str, dict[str, Any]]:
        kind = case.input.get("check")
        if kind == "policy_effect":
            intent = PolicyInput(
                tool_name=str(case.input.get("tool_name", "local_echo")),
                permission_class=PermissionClass(
                    str(case.input.get("permission_class", "safe_read"))
                ),
                action_summary=str(case.input.get("action_summary", "eval case")),
                inputs=dict(case.input.get("inputs") or {}),
                external_data=bool(case.input.get("external_data", False)),
                destructive=bool(case.input.get("destructive", False)),
            )
            if case.input.get("tools_enabled", True):
                cfg.tools.enabled = True
                cfg.tools.files.enabled = True
                cfg.tools.github.enabled = True
            else:
                cfg.tools.enabled = False
            decision = engine.evaluate(intent)
            expected = str(case.expect.get("effect"))
            ok = decision.effect.value == expected
            return ok, f"effect={decision.effect.value}", {"effect": decision.effect.value}
        if kind == "citation_count":
            from atticus.services import citations as cite_svc

            cite_dir = cite_svc.citation_dir_from_config(cfg.tools.browser.citation_dir)
            records = cite_svc.list_records(cite_dir, limit=100)
            minimum = int(case.expect.get("min_count", 0))
            ok = len(records) >= minimum
            return ok, f"count={len(records)}", {"count": len(records)}
        return False, f"unknown check: {kind}", {}

    return checker


def build_evals_router() -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["evals"])

    @router.post("/evals/run")
    async def run_evals(request: Request, suite: str = "platform") -> dict[str, Any]:
        root = Path(__file__).resolve().parents[2]
        path = root / "evals" / f"{suite}.json"
        if not path.is_file():
            raise EvalSuiteMissing(f"Eval suite not found: {suite}")
        loaded = EvalSuite.load(path)
        report = run_suite(loaded, _default_checker_factory(request))
        get_telemetry().emit(
            "api.evals_run",
            suite_id=loaded.id,
            passed=report.passed,
            failed=report.failed,
        )
        return report.to_dict()

    return router
