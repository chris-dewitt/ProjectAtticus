#!/usr/bin/env python3
"""Run versioned evaluation suites from evals/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atticus.core.config import load_app_config
from atticus.core.permissions import PermissionClass
from atticus.evals.harness import EvalCase, EvalSuite, run_suite
from atticus.policy.engine import PolicyEngine
from atticus.policy.models import PolicyInput


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Atticus eval suites")
    parser.add_argument("--suite", default="platform", help="Suite file stem under evals/")
    args = parser.parse_args()
    path = ROOT / "evals" / f"{args.suite}.json"
    if not path.is_file():
        print(f"Suite not found: {path}", file=sys.stderr)
        return 2
    cfg, _ = load_app_config()
    engine = PolicyEngine(cfg)
    suite = EvalSuite.load(path)

    def checker(case: EvalCase) -> tuple[bool, str, dict]:
        if case.input.get("check") != "policy_effect":
            return False, "unsupported check", {}
        if case.input.get("tools_enabled", True):
            cfg.tools.enabled = True
            cfg.tools.files.enabled = True
            cfg.tools.github.enabled = True
        else:
            cfg.tools.enabled = False
        decision = engine.evaluate(
            PolicyInput(
                tool_name=str(case.input.get("tool_name", "local_echo")),
                permission_class=PermissionClass(
                    str(case.input.get("permission_class", "safe_read"))
                ),
                action_summary=str(case.input.get("action_summary", "eval")),
                inputs=dict(case.input.get("inputs") or {}),
                external_data=bool(case.input.get("external_data", False)),
                destructive=bool(case.input.get("destructive", False)),
            )
        )
        expected = str(case.expect.get("effect"))
        ok = decision.effect.value == expected
        return ok, f"effect={decision.effect.value}", {"effect": decision.effect.value}

    report = run_suite(suite, checker)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
