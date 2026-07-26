# Signature demo

Research three RAG-evaluation approaches (synthetic fixtures), save citations,
build a comparison table, draft a GitHub issue, and **stop for approval** before
publish — with trace + quality report.

```powershell
cd C:\Users\DELL\Documents\GitHub\ProjectAtticus
pip install -e ".[api]"
python scripts/run_signature_demo.py --artifacts data\artifacts\signature_demo
```

Or via API after `atticus-api`:

```powershell
Invoke-RestMethod -Method POST http://127.0.0.1:8000/v1/demo/signature `
  -ContentType 'application/json' `
  -Body '{"artifacts_subdir":"signature_demo"}'
```

Artifacts:

- `rag_comparison.json`
- `github_issue_draft.md`
- `trace.json`
- `quality_report.json`

Publishing still requires token-gated approval + idempotent dispatch.
