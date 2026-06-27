# Strategy: data_driven

Use when a real CSV exists in `data/` and synthetic data must statistically match it.

## Patterns

1. Profile the real CSV first: per-column frequencies, scipy distribution fits, conditional correlations.
2. Choose algorithm:
   - **Statistical Sampling** — independent column resampling.
   - **GaussianCopula** — preserves linear correlations (SDV).
   - **CTGAN / TVAE / CopulaGAN** — non-linear correlations and complex distributions.
3. Validator uses Kolmogorov-Smirnov test per numeric column + chi-squared on categoricals.

## Important

- State the chosen algorithm and its justification directly in the plan
  (`## Selected Strategy + Justification`) — do NOT pause to ask the user.
- Persist the fitted model so generation is reproducible.

## Locale

- Locale is implicit in the source CSV — do not filter or re-locale samples unless the CSV is explicitly multi-locale.
- `generation_config.yaml` still declares the `locale` field for consistency and downstream consumers; set it to the locale of the source CSV.
- If any LLM-assisted augmentation is added later, that step must honor this locale.
