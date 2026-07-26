# Evaluation

Canonical evaluation docs: [`docs/EVALUATION.md`](docs/EVALUATION.md).

Runnable suites:

```powershell
python scripts/run_evals.py --suite platform
# or
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/evals/run?suite=platform
```

Suite files live under `evals/` (versioned JSON). Signature demo quality checks
also emit `data/artifacts/signature_demo/quality_report.json`.
