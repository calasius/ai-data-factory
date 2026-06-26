# Strategy: faker_llm

Use when the dataset is mostly structured + has some free-text or classification fields.

## Patterns

- Phase 1: Faker for structured fields, generates the full table without LLM.
- Phase 2: LLM enriches only the text fields, called per-row or per-batch.
- Use `concurrent.futures.ThreadPoolExecutor` with a shared client; `max_workers=8` is safe.
- Always include a deterministic rules-based fallback enricher for offline runs.

## Prompt rules

- ALWAYS list CRITICAL OUTPUT RULES at the top: format, length, no markdown, single value only.
- Validate LLM output before writing — drop or fallback if it doesn't match expected format.

## Seeds

- Vocabularies >20 items → `seeds/<field>.json`, loaded at runtime. Never inline in `.py`.
- Prefer `Faker(locale)` / `mimesis` / `faker_commerce` before inventing.
- When inventing, generate ≥100 items in one LLM call and write to the seed file.
- Each seed file regenerable via `generate-{name} seed --field=<name> [--locale=...]`.
- Keep prompts in `src/generators/seed_prompts.py` as a dict with fields:
  `prompt`, `default_count`, `locale_aware`, `diversity_axes`, `temperature`.
- Validator prints `n_unique / n_rows` per categorical field (info, not hard fail).

## Seed diversity (when the LLM invents the list)

Generating N items is not enough — LLMs cluster around the most frequent examples.

- Each seed prompt declares **diversity axes** relevant to the domain:
  - cities → region, size tier, economic profile
  - complaints → category, severity, channel, tone
  - products → category, price range, target segment
- Use **stratified prompting**: split N across axis combinations.
  e.g. 200 cities = 5 regions × 4 size tiers × 10 items, requested explicitly in the prompt.
- Set `temperature ≥ 0.9` for seed generation (higher than enricher calls).
- If generating in batches, pass previously-generated items as "avoid these" in the next batch.
- After generation:
  - Dedup ratio `n_unique / n_generated ≥ 0.95` → else retry once.
  - Axis coverage: each declared axis value should appear in ≥1 item → else retry.
  - Log a per-axis histogram; flag WARN if any axis bucket has <50% of expected count.

## Locale

- `generation_config.yaml` has a required `locale` field (use `null` for locale-neutral datasets).
- All `Faker()` instances are initialized with this locale. Never mix locales in one run.
- Seed prompts marked `locale_aware=True` inject the locale; `False` prompts ignore it.
- LLM enricher system prompt must mention the locale when non-null ("outputs should reflect {locale} conventions").
- CLI flag `--locale` overrides the config value at runtime.
