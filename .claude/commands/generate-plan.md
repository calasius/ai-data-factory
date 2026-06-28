Read `data_schema_spec.md` and all strategy templates in `tools/templates/`.

**First, inspect the `data/` directory** (e.g. `ls data/` / glob `data/*`).

Select the strategy in this priority order:

1. **If a real source file exists in `data/` → you MUST use `data_driven`.**
   The user provided real data; the generator must statistically match it.
   **Read `data_profile.md`** (a precomputed pandas/scipy profile of the source):
   use its real dtypes, fitted distributions, and correlations to choose the
   algorithm, set distribution parameters, and define the KS / chi-squared
   validation targets. Never fall back to faker_*/llm when `data/` has a source file.
2. Otherwise, pick by field types:
   - faker_pure: all structured fields, no free-text
   - faker_llm: mostly structured + some free-text/classification
   - llm: deep semantic consistency required across fields

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

The runtime provides a DeepSeek API key via env. DeepSeek is OpenAI-compatible,
so use the `openai` library pointed at DeepSeek's endpoint:

- `DEEPSEEK_API_KEY` (already set in the environment)
- `DEEPSEEK_MODEL` (optional; default `deepseek-chat`)

**All LLM enrichment MUST use the `openai` library against DeepSeek.** Do NOT
use Azure OpenAI, the `anthropic` package, or `ANTHROPIC_API_KEY` — they are not
available. The Python dependency in `pyproject.toml` is `openai>=1.54.0`.

For structured/batch output, use DeepSeek JSON mode
(`response_format={"type": "json_object"}`) and validate the parsed JSON. Do NOT
use OpenAI strict structured outputs (`.parse()` / Pydantic
`response_format=Model`) — DeepSeek does not support them.

Always include a deterministic rules-based fallback enricher for offline runs.

Example client instantiation to include in the plan:

```python
import os
from openai import OpenAI
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.environ["DEEPSEEK_API_KEY"],
)
resp = client.chat.completions.create(
    model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
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

---

**Output:** Respond with ONLY the complete plan as markdown (it will be saved as
`implementation_dataset.md`). No preamble, no code-fence wrapper, no summary —
just the plan, starting with the `# Implementation Plan:` heading.
