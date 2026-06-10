---
name: programmatic-eda
description: Systematic exploratory data analysis. Activate when a dataset needs profiling — structure check, nulls, outliers, distributions, correlations — before deeper analysis begins.
---

# When to use
- You receive a new dataset and need to understand its shape and quality before analysis
- An analysis produces surprising numbers and you want to verify the underlying data first
- A stakeholder asks "is this data reliable?" or "what's in this table?"
- You're about to run a model or statistical test and need data-quality assurance

# Process
1. **Load and overview** — run `scripts/data_overview.py` to get row count, dtypes, memory usage, and a sample. Confirm grain (what one row represents).
2. **Null profile** — run `scripts/null_profiler.py`; compare output against thresholds in `references/quality_thresholds.md` and flag columns above limits.
3. **Outlier detection** — run `scripts/outlier_detector.py` (IQR + z-score) on numeric columns; document flagged values and decide: real signal or data error?
4. **Distribution summary** — run `scripts/distribution_summary.py` for descriptive stats and univariate histograms on each numeric column.
5. **Correlation exploration** — run `scripts/correlation_explorer.py`; flag pairs with |r| > 0.8 as potential multicollinearity or redundancy.
6. **EDA checklist sign-off** — work through `references/eda_checklist.md` and confirm each item before declaring the dataset profiled.
7. **Write findings** — fill `assets/eda_report_template.md` with full profiling output; distil top issues into `assets/findings_summary.md`.

For pattern recipes (e.g. polars vs pandas equivalents, chunked reads for large files), see `references/pandas_polars_recipes.md`.

# Inputs the skill needs
- Required: dataset path (CSV / Parquet / Excel) or a DataFrame already in scope
- Required: business context — what does one row represent?
- Optional: quality threshold overrides (defaults in `references/quality_thresholds.md`)
- Optional: columns to skip (PII, binary blobs, high-cardinality IDs)

# Output
- `assets/eda_report_template.md` (filled) — full profiling report with per-column stats
- `assets/findings_summary.md` (filled) — top 3–5 quality issues and recommended next steps
- Console output / plots from scripts for interactive inspection
