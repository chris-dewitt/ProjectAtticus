# Model Card — ProjectAtticus

Status: Honest inventory of models in use or planned  
Related: `atticus/providers/`, `config/atticus.example.yaml`, `SPEC.md`

## Purpose

Atticus uses cloud LLM providers as interchangeable “brains” behind a local orchestration and permission layer. Models do not authorize tools or perform policy decisions; the local app does.

## Models in configuration (example defaults)

| Provider | Config model string | Implementation status |
|----------|---------------------|------------------------|
| OpenAI | `gpt-4o-mini` | Live (`OpenAIProvider`) |
| Anthropic | `claude-3-5-sonnet-20241022` | Stub (`AnthropicProviderStub`) |
| Gemini | `gemini-1.5-flash` | Stub (`GeminiProviderStub`) |

Defaults may change via `config/atticus.yaml`. The Speaker may switch providers with `/provider` when implementations exist; stub providers raise a clear error.

## Intended use

- Conversational assistance in the Atticus persona (Track A)
- Optional file summarization after approval
- Future Track B bounded agent workflows with traces and evals

## Out of scope for models

- Authoritative arithmetic, authorization, or policy decisions
- Silent fallback across providers (must be configured and recorded — Track B)
- Processing confidential employer data in fixtures or public demos

## Evaluation status

No pinned regression suite comparing model quality/cost/latency is published yet. See `docs/EVALUATION.md`. Until that exists, treat model choice as a local preference, not a benchmarked claim.

## Safety and privacy notes

- API keys via environment (and optional keyring helper for some integrations); never commit secrets
- Ask before sending local file contents to a cloud provider
- Retrieved or uploaded document text is untrusted data, not instructions
