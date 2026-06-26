Read `implementation_dataset.md`, `data_schema_spec.md`, and the selected strategy template.

Implement all files:
- `pyproject.toml`
- `config/generation_config.yaml`
- `src/config.py`
- `src/cli.py`
- `src/generators/main.py`
- `src/writers/csv_writer.py`
- `src/validators/validator.py`
- `src/models/schemas.py` + LLM enricher (if llm or faker_llm)
- `src/generators/seed_prompts.py` + `src/generators/seeds.py` (if strategy uses seed files)
- `seeds/*.json` (one per field that needs a runtime-loaded vocabulary)
- `tests/test_generator.py` + `tests/test_validator.py` (>80% coverage)

Validator must encode the exact rules from the schema spec — not generic.
Checks: nulls, enum values, numeric ranges, distribution rates, cross-field consistency.
Print PASS / FAIL with observed vs expected on failures.

## LLM provider

All LLM enrichment MUST use Azure OpenAI via the `openai` SDK. The runtime
container has these env vars set:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

**Do NOT import `anthropic` and do NOT require `ANTHROPIC_API_KEY`.** The
Python dependency must be `openai>=1.54.0`. Use `openai.AzureOpenAI` as the
client. Pass `model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]` to
`chat.completions.create`.

If the strategy requires no LLM enrichment (e.g. `faker_pure`, `data_driven`
without augmentation), skip this entirely — do not add Azure OpenAI as a
dependency for nothing.

## Distribution-level validation tolerance

Distribution-level checks (downtime fraction, success rate, severity mix,
archetype proportions, etc.) must use **≥10% tolerance from the target**.
Tighter bands cause false failures on small stochastic runs.

- **Good**: `assert 0.65 <= zero_dt_frac <= 0.85` (target 75% ± 10pp)
- **Bad**:  `assert 0.70 <= zero_dt_frac <= 0.80` (target 75% ± 5pp — too tight)

For ratio targets (e.g. "minor incidents ≥ 50%"), a one-sided margin of
≥5pp below the target is acceptable (`assert minor_frac >= 0.45`).

Exception: hard invariants (non-negative counts, FK integrity, enum
membership, date ordering) are NOT distribution-level — those stay strict.

## Configuration YAML

Generate `config/generation_config.yaml` coherent with the schema. Structure:

```yaml
# Run-level parameters
locale: <from_schema>         # or null
num_records: <typical_scale>  # default from schema "Typical scale"
seed: 42

# Multi-table: single anchor
anchor_entity: <from_schema>
# or multi-anchor (only if schema declared it):
# anchors:
#   - orders: 10000
#   - support_tickets: 500

output:
  format: csv
  path: output/           # directory — multi-table writes one CSV per entity inside, single-table writes dataset.csv

run_options:
  regenerate_seeds: false
  seed_count_override: null

# Optional overrides — if absent, schema defaults apply.
# overrides:
#   entity_counts:           # force exact count per entity (required for `shared` entities)
#     customers: 500
#   fan_out:                 # override fan-out mean per relation
#     customer_order: 20
#   archetype_shares:        # change segmentation mix
#     power_user: 0.20
#     regular: 0.60
#     one_off: 0.20
```

Rules:
- Keep the `overrides` block commented in the default file, but fully documented — the user sees what's possible when they open the editor.
- `src/config.py` must merge user overrides on top of schema-derived defaults. Never ignore schema ratios when an override key is missing/null.
- For `shared` entities (multi-anchor), the generator must fail fast if the user didn't supply a count in `overrides.entity_counts`.

### Comments are mandatory

**Every key in the generated YAML MUST have an inline comment.** The YAML doubles as user-facing documentation — when the user opens the editor, they must understand each key without leaving the file.

Comment format per key:
- What the key does (one clear line)
- Source: `schema` (inferred from the data spec), `run-level` (execution parameter), or `override` (optional user override)
- Accepted values / format constraints when relevant (locale format, enum values, numeric range)
- Reference to the schema source when derived (e.g. `# Source: schema typical_scale`)

Example of well-commented YAML:
```yaml
locale: es_AR            # ISO locale (e.g. es_AR, en_US) or null. Source: schema. Used by Faker, mimesis, LLM prompts.
num_records: 10000       # Rows of the anchor entity (not total dataset). Source: run-level. Schema typical_scale: 10,000.
seed: 42                 # Random seed for reproducibility. Source: run-level.

anchor_entity: orders    # Which entity scales with num_records. Source: schema.

output:
  format: csv            # Output format: csv | json | parquet. Source: run-level.
  path: output/          # Directory (not a file path) where the generator writes its output. Relative to project root.
                         # Multi-table: one file per entity (customers.csv, orders.csv, ...). Single-table: dataset.csv.

run_options:
  regenerate_seeds: false        # If true, regenerate seeds/*.json via LLM before dataset generation.
  seed_count_override: null      # Force N items per seed file; null = use default_count from seed_prompts.

# overrides:              # OPTIONAL — leave commented to use schema defaults.
#   entity_counts:        # Force exact count per entity. Required for `shared` entities (multi-anchor).
#     customers: 500      # Schema default: derived from 1:10 ratio from orders.
#   fan_out:              # Override fan-out λ per relation. Format: <parent>_<child>: <mean>
#     customer_order: 20  # Schema default: 10 (Poisson).
#   archetype_shares:     # Override segmentation mix. Must sum to 1.0.
#     power_user: 0.20    # Schema default: 0.05.
#     regular: 0.60       # Schema default: 0.60.
#     one_off: 0.20       # Schema default: 0.35.
```

Rule of thumb: a reader who never saw the schema should understand what each line does and what they can safely change.

## Seeds

- Create `seeds/*.json` files per the rules in the strategy template. Do not hardcode long vocabularies in `.py`.
- If a vocabulary needs to be invented, generate ≥100 items via LLM in this step and write to the seed file.
- `src/generators/seed_prompts.py` holds a dict entry per field with: `prompt`, `default_count`, `locale_aware`, `diversity_axes`, `temperature`.
- `src/generators/seeds.py` exposes `load_seed(field)` (reads JSON, caches) and `regenerate_seed(field, count, locale, force)` (calls LLM, writes file).
- When generating seed files via LLM:
  - Read `diversity_axes` from `seed_prompts.py` and include them in the prompt.
  - Use `temperature` from the entry (default 0.9).
  - Post-generation checks: dedup ratio `n_unique / n_generated ≥ 0.95` AND each axis value present in ≥1 item. Retry once on failure.
  - Print per-axis histogram and dedup ratio before writing the file.

## Locale

- `config/generation_config.yaml` has a required `locale` field. Validate on startup: accepted values are valid Faker locales or `null`.
- `src/config.py` exposes `Config.locale`. All generators read from here.
- All `Faker()` and `mimesis` instances initialize with this locale. Never mix locales in one run.
- LLM enricher system prompt includes the locale when non-null.
- If `locale` is null and any seed prompt is `locale_aware=True`, print a WARNING (not an error — let the user proceed knowing seeds will be generic).

## CLI

- `generate --config <path> [--regenerate-seeds] [--locale=<xx_YY>]` → generate dataset; if `--regenerate-seeds`, run `seed --all` first.
- `validate --config <path>` → run validator.
- `seed --field=<name> | --all [--count=N] [--locale=<xx_YY>] [--force]` → regenerate seed files. Without `--force`, backup existing seeds to `seeds/_backup/<field>_<timestamp>.json` before overwrite.

## Diversity check (in validator)

For every open-domain categorical field (those with seed-file or LLM source):
- Compute `n_unique / n_rows` and print per-field cardinality report.
- Log WARNING if ratio < 0.05 for fields sourced from seeds — the seed file is likely too small.
- Log a locale-consistency check: sample 20 text values and verify expected language/script. PASS/WARNING (never fail — heuristic).

After implementing run both commands and fix until they succeed:
  uv run generate-{name} generate --config config/generation_config.yaml
  uv run generate-{name} validate --config config/generation_config.yaml
