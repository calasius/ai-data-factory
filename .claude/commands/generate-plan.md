Read `data_schema_spec.md` and all strategy templates in `tools/templates/`.

Select the best strategy:
- faker_pure: all structured fields, no free-text
- faker_llm: mostly structured + some free-text/classification
- llm: deep semantic consistency required across fields
- data_driven: real CSV exists in `data/`

Produce `implementation_dataset.md` with:

# Implementation Plan: {Dataset Name}

## Locale

Copy `locale` from the schema spec. State explicitly how it propagates:
- Faker/mimesis instances → initialized with this locale
- Seed prompts marked `locale_aware=True` → receive this locale
- LLM enricher prompts → include locale in system context
If `locale=null`, all generators run locale-neutral and seed prompts must not reference nationality/region.

## Entities & Anchors

Copy from the schema spec and state how it flows into the generator:

| Entity | Type | Count rule |
|---|---|---|
| orders | anchor | `num_records` |
| customers | derived | `num_records / 10` (Poisson λ=10) |
| order_items | derived | `num_records * 3` (Poisson λ=3) |
| subscription_plans | fixed | 3 (from schema catalog) |

- Anchor(s): copy the anchor or list of anchors from the schema.
- Shared entities (multi-anchor only): count must come from `overrides.entity_counts` in the run config.
- If archetypes exist, state the resolution formula explicitly, e.g.:
  `N_customers × Σ(share_i × λ_i) = num_records_anchor → solve for N_customers`

## Selected Strategy + Justification
## Tech Stack
## Project Structure
## Generator Name
## Field Implementation Map
| Field | Generator | Source | Locale-sensitive | Diversity axes | Correlation logic |

`Source` is one of: `faker:<locale>`, `mimesis`, `seeds/<file>.json`, `inline` (only for closed domains <10 items), `derived` (computed from other fields).
`Locale-sensitive` copied from the schema spec.
`Diversity axes`: for LLM-invented seeds only, list the axes the prompt must balance (e.g. `region, size, segment`). Empty for Faker/mimesis/CSV sources.

**All columns are required.** Render the full table — do not compress fields
into a generic "Implementation Notes" column. Use `—` for cells that don't
apply (e.g. `Diversity axes` for Faker sources), never omit the column.

## LLM provider (use this, nothing else)

The runtime container provides Azure OpenAI credentials via these env vars,
already set:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

**All LLM enrichment MUST use `openai.AzureOpenAI`.** Do NOT import or depend
on the `anthropic` package. Do NOT assume `ANTHROPIC_API_KEY` is set — it
isn't. The Python dependency in `pyproject.toml` is `openai>=1.54.0`.

Example client instantiation to include in the plan:

```python
from openai import AzureOpenAI
client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)
# model arg uses the deployment name:
resp = client.chat.completions.create(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    messages=[...],
)
```

## Archetype distribution parametrization

When the plan declares a distribution per archetype, always specify the full
parametrization: family + parameters + clipping bounds.

- **Good**: `high_producer: lognormal(μ=6.5, σ=0.4), clipped [500, 2000]`
- **Bad**:  `high_producer: lognormal clipped [500, 2000]`  *(missing params)*
- **Bad**:  `high_producer: 500-2000 bopd`  *(family + params implicit)*

The coder needs μ/σ (or equivalent) concretely — do not leave it implicit.

## Correlations Implementation
(concrete Python code patterns)

## Config YAML
## Validation Spec
| Rule | Check | Failure condition |

## CLI Commands

Map every constraint to a specific check in validator.py.
