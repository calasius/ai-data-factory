# Strategy: faker_pure

Use when all fields are structured (IDs, dates, numbers, enums) — no free-text or LLM needed.

## Patterns

- Seed all randomness: `Faker.seed(seed)`, `np.random.seed(seed)`, `random.seed(seed)`.
- Use weighted choices for correlated categorical fields (`np.random.choice(values, p=probs)`).
- Use `np.random.lognormal` / `normal` for realistic numeric distributions (income, revenue, age).
- Multi-table datasets: generate parent table first, then build FK mappings.
- Cross-field correlations: derive child fields from parent (`if age < 25: income *= 0.6`).

## Locale

- `generation_config.yaml` has a required `locale` field (use `null` for locale-neutral datasets).
- All `Faker()` instances are initialized with this locale. Never mix locales in one run.
- CLI flag `--locale` overrides the config value at runtime.

## Output

- CSV via `pandas.DataFrame.to_csv(index=False)`.
- One row per record, deterministic given the seed.
