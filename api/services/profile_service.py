"""Deterministic statistical profiler for the data_driven flow.

When a user uploads a source CSV, we profile it with pandas/scipy over the FULL
file (not an LLM reading a truncated sample) and emit `data_profile.md`. The
schema, plan, and implement agents read that profile so the generated generator
matches the real distributions/correlations — the core of data_driven fidelity.

Best-effort: any failure degrades gracefully (the CSV is still usable), it just
means no precomputed profile.
"""

from pathlib import Path

from api.services import file_service

PROFILE_FILENAME = "data_profile.md"

# Numeric distributions we try to fit (scored by KS statistic, lower = better).
_CANDIDATE_DISTS = ("norm", "lognorm", "expon", "gamma", "uniform")
_TOP_K_CATEGORIES = 12
_MAX_CORR_PAIRS = 25
_CORR_MIN = 0.3


def profile_project_file(project_id: str, rel_path: str) -> str | None:
    """Profile a project's source file and write data_profile.md.
    Returns the profile's relative path, or None if profiling wasn't possible."""
    import pandas as pd  # imported lazily so the API boots even without pandas

    csv_path = file_service.project_dir(project_id) / rel_path
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path, low_memory=False)
    if df.empty:
        return None

    md = _render_markdown(df, Path(rel_path).name)
    file_service.write_artifact(project_id, PROFILE_FILENAME, md)
    return PROFILE_FILENAME


def _coerce_datetime(series):
    """Return a parsed datetime Series if the column looks like dates, else None."""
    import pandas as pd

    if series.dropna().empty:
        return None
    sample = series.dropna().head(50)
    parsed = pd.to_datetime(sample, errors="coerce", utc=False)
    if parsed.notna().mean() >= 0.9:
        return pd.to_datetime(series, errors="coerce", utc=False)
    return None


def _best_fit(series) -> dict | None:
    """Fit candidate distributions to a numeric column; return the best by KS."""
    import numpy as np
    from scipy import stats

    x = series.dropna().to_numpy(dtype="float64")
    if x.size < 20 or np.unique(x).size < 5:
        return None

    best = None
    for name in _CANDIDATE_DISTS:
        dist = getattr(stats, name)
        try:
            params = dist.fit(x)
            ks = float(stats.kstest(x, name, args=params).statistic)
        except Exception:
            continue
        if best is None or ks < best["ks"]:
            best = {"dist": name, "params": [round(float(p), 4) for p in params], "ks": round(ks, 4)}
    return best


def _render_markdown(df, filename: str) -> str:
    import numpy as np
    import pandas as pd

    n_rows, n_cols = df.shape
    lines: list[str] = [
        f"# Data Profile: {filename}",
        "",
        f"**Rows:** {n_rows:,} | **Columns:** {n_cols}",
        "",
        "Precomputed from the full source file (pandas/scipy). Use these real",
        "statistics to design the schema, choose the data_driven algorithm, set",
        "distribution parameters, and define KS / chi-squared validation targets.",
        "",
        "## Columns",
        "",
    ]

    numeric_cols: list[str] = []
    for col in df.columns:
        s = df[col]
        n_null = int(s.isna().sum())
        pct_null = round(100 * n_null / n_rows, 1) if n_rows else 0.0
        n_unique = int(s.nunique(dropna=True))

        dt = _coerce_datetime(s) if s.dtype == object else None
        is_numeric = pd.api.types.is_numeric_dtype(s) and dt is None

        if is_numeric:
            numeric_cols.append(col)
            desc = s.describe()
            kind = "numeric"
            detail = (
                f"min={_fmt(desc.get('min'))} max={_fmt(desc.get('max'))} "
                f"mean={_fmt(desc.get('mean'))} std={_fmt(desc.get('std'))} "
                f"p25={_fmt(desc.get('25%'))} p50={_fmt(desc.get('50%'))} p75={_fmt(desc.get('75%'))}"
            )
            fit = _best_fit(s)
            fit_line = (
                f"\n  - best-fit: `{fit['dist']}{tuple(fit['params'])}` (KS={fit['ks']})"
                if fit else ""
            )
            body = f"\n  - {detail}{fit_line}"
        elif dt is not None:
            kind = "datetime"
            body = f"\n  - range: {dt.min()} → {dt.max()}"
        else:
            kind = "categorical"
            vc = s.value_counts(dropna=True).head(_TOP_K_CATEGORIES)
            tops = ", ".join(f"{_short(str(k))} ({round(100*v/n_rows,1)}%)" for k, v in vc.items())
            body = f"\n  - top values: {tops}"

        lines.append(f"### `{col}` — {kind}, {pct_null}% null, {n_unique:,} unique{body}")
        lines.append("")

    # Numeric correlations (Pearson), strongest pairs only.
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr(numeric_only=True).abs()
        pairs = []
        cols = list(corr.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = corr.iloc[i, j]
                if pd.notna(r) and r >= _CORR_MIN:
                    pairs.append((cols[i], cols[j], float(r)))
        pairs.sort(key=lambda p: p[2], reverse=True)
        if pairs:
            lines += ["## Numeric correlations (|r| ≥ 0.3)", ""]
            for a, b, r in pairs[:_MAX_CORR_PAIRS]:
                lines.append(f"- `{a}` ~ `{b}`: r={round(r, 2)}")
            lines.append("")
            lines += [
                "Strong correlations → prefer a correlation-preserving model "
                "(GaussianCopula / CopulaGAN / CTGAN) over independent column sampling.",
                "",
            ]

    return "\n".join(lines)


def _fmt(v) -> str:
    import pandas as pd
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.4g}"


def _short(s: str, n: int = 30) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"
