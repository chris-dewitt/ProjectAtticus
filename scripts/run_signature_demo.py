#!/usr/bin/env python3
"""CLI entry for the Track B signature demo (synthetic fixtures)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from a checkout without install.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atticus.core.config import load_app_config
from atticus.demo.signature import run_signature_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Atticus signature demo fixtures")
    parser.add_argument(
        "--artifacts",
        default="data/artifacts/signature_demo",
        help="Directory for comparison table, issue draft, trace, quality report",
    )
    args = parser.parse_args()
    cfg, _ = load_app_config()
    result = run_signature_demo(cfg, artifacts_dir=Path(args.artifacts))
    print(json.dumps(result.to_dict(), indent=2))
    print(
        "\nStopped for approval before publishing."
        f" Approval id: {result.approval_id}"
        f" Decision: {result.policy_decision}"
        f" Quality ok: {result.quality_report.get('ok')}",
        file=sys.stderr,
    )
    return 0 if result.quality_report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
