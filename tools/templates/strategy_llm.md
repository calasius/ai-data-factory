# Strategy: llm

Use when deep semantic consistency is required across many fields (e.g. realistic claims narratives where amount, date, and description must align).

## Patterns

- Use Pydantic `response_format` with a `BatchResponse` schema for structured batches.
- Set `max_completion_tokens ≈ 150 × batch_size`.
- Log batch count mismatches (LLM sometimes returns N-1 records).
- For rate limits: reduce `max_workers` first, then `batch_size`.

## Determinism

- Pure LLM is non-deterministic. Use `temperature=0` + a `seed` parameter where supported.
- Run validation on every batch — reject and retry malformed batches.

## Locale

- `generation_config.yaml` has a required `locale` field (use `null` for locale-neutral datasets).
- LLM system prompt must mention the locale when non-null ("outputs should reflect {locale} conventions: language, names, places, currency").
- CLI flag `--locale` overrides the config value at runtime.
- When `locale=null`, prompts must not reference nationality/region.
