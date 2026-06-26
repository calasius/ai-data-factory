You are creating a complete synthetic data generator from scratch.

The user has a `dataset_description.md` in the current working directory.

## Guiding principles

- Realism first.
- Suggest beyond the described constraints and correlations.
- Validation is mandatory.

## Pipeline

1. `/generate-schema` → `data_schema_spec.md` (pause for user review)
2. `/generate-plan`   → `implementation_dataset.md` (pause for user review)
3. `/implement`       → full generator code, runs, validates

After each step, summarize what was produced and ask the user if they want changes before continuing.
