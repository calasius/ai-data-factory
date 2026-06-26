Read `dataset_description.md` in the current working directory.

Produce `data_schema_spec.md` with:

# Data Schema Spec: {Dataset Name}

## Overview
## Fields
| Field | Type | Description | Example |

## Constraints
(label inferred ones with *(inferred)*)

## Correlations & Dependencies
{field_a} → {field_b}: {rule description}

## Relationships (multi-table only — omit section if single-table)

| From | To | Fan-out | Distribution | Participation |
|---|---|---|---|---|
| customer | order | ~10 | poisson | 80% |
| order | order_item | ~3 | poisson | mandatory |

- `Fan-out`: typical mean (λ for poisson, ratio for fixed).
- `Distribution`: `poisson` | `geometric` | `fixed` | `zeta`. Keep it to these four — richer families belong in `Distributions` section.
- `Participation`: `%` of parents with ≥1 child, or `mandatory` (100%).

### Hard rules for this table

**One parent per derived entity.** Each derived entity must cascade from
exactly ONE parent row here. If an entity can originate from multiple parents
conceptually (e.g. facility-level vs well-level incidents), represent it via
a nullable FK on a single parent — do NOT add multiple rows pointing to the
same child entity. Two rows → ambiguous derivation → the coder cannot compute
counts.

**Distribution values are unambiguous.**
- `fixed` requires an exact integer (no `~`). Use only when the count is truly
  deterministic (e.g. 1:1 relationships).
- `poisson` / `geometric` / `zeta` take a mean value with `~` (e.g. `~10`).
- Never mix `fixed` with `~N` — contradictory and forces the coder to guess.

### Denormalized FKs

Avoid denormalized FKs (e.g. `operator_id` on `daily_production` when already
reachable via `wells`). If you include one for analytical convenience, justify
it in the Overview and add a cross-table consistency check to the Validation
Rules.

## Entities & Anchors

| Entity | Type | Derivation |
|---|---|---|
| orders | anchor | scales with `num_records` |
| customers | derived | 1:10 from orders |
| order_items | derived | 3:1 from orders |
| subscription_plans | fixed | 3 values (catalog) |

- `anchor`: row count scales with `num_records`.
- `derived`: count computed from ratios to an anchor.
- `fixed`: catalog with cardinality declared in schema.
- `shared`: appears in multiple disconnected subgraphs (multi-anchor case).

### Multi-anchor (only if the graph has disconnected subgraphs)

Declare independent anchors as a list:
```
anchors: [orders, support_tickets]
```
Mark any entity that spans both subgraphs as `shared`; its count must be set explicitly in the run config (no automatic derivation).

## Archetypes (include only if the domain has clear segments — otherwise omit)

| Entity | Archetype | Share | Behavior |
|---|---|---|---|
| customers | power_user | 5% | ~60 orders/yr |
| customers | regular | 60% | ~12 orders/yr |
| customers | one_off | 35% | 1 order |

Homogeneous fan-out is fine when segments aren't obvious; don't invent archetypes to look complete.

## Volume & Distribution Notes

- Typical scale (default `num_records` for the anchor if user doesn't specify): ~10,000
- Rationale: (e.g. "one year of activity for a small e-commerce business")
- Distributions for key numeric fields (only the 2-3 that have a well-known shape): e.g. `order_amount: lognormal(μ=3.5, σ=1.2)`. Plain "numeric with mean X" is enough for the rest.

## Validation Rules
- Required fields not null
- Enum values within allowed set
- Numeric ranges
- Distribution-level checks
- Referential integrity
- Cross-field consistency rules

## Locale

Declare a `locale` field at the top of the schema spec (ISO format: `es_AR`, `en_US`, `pt_BR`, or `null`).
Infer it from the dataset description (language, country mentions, currency, address format).
Mark each categorical/text field as `locale-sensitive: true|false`:
- true  → names, cities, addresses, companies, idioms, currency
- false → globally-uniform domains (ISO codes, product categories, timestamps)
If ambiguous, ask the user before proceeding.

Realism first. Suggest constraints and correlations beyond what is described. Validation rules are mandatory.
