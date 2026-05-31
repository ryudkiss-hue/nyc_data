# Quality Thresholds Reference

Default thresholds used by `null_profiler.py` and the EDA checklist. Override per-project by passing `--warn-pct` / `--fail-pct` flags.

## Null / Missing Values

| Threshold | Default | Meaning |
|---|---|---|
| WARN | 5% | Column has more nulls than typical — investigate cause |
| FAIL | 30% | Column is too sparse for reliable analysis without imputation |

**Column-type exceptions:**
- Optional demographic fields (e.g. `middle_name`, `secondary_email`): set WARN to 50%
- Pipeline-populated enrichment fields (e.g. `geo_region`): set WARN to 15%, FAIL to 60%
- Behavioural event properties that only apply to a subset: document expected null rate

## Duplicates

| Threshold | Default |
|---|---|
| Full-row duplicate rate | > 0% → investigate; > 1% → FAIL |
| Key-level duplicate rate | > 0% → investigate; must justify intentional versioning |

## Outliers (Numeric Columns)

| Method | Threshold |
|---|---|
| IQR | Values beyond Q1 − 1.5×IQR or Q3 + 1.5×IQR |
| Z-score | |z| > 3 (i.e. > 3 standard deviations from the mean) |

Outliers are flagged for review, not automatically removed. Each must be classified:
- **Real signal** — genuine extreme value (e.g. a high-value enterprise deal)
- **Data error** — pipeline bug, unit mismatch, or test data leak
- **Structural** — a domain-specific sentinel value (e.g. -1 meaning "unknown")

## Value Ranges (Business-logic thresholds)

| Column type | Rule |
|---|---|
| Age | 0 ≤ age ≤ 120 |
| Revenue / price | ≥ 0 (unless refunds are expected; document negative-revenue semantics) |
| Percentage / rate | 0 ≤ x ≤ 1 (or 0–100 — confirm encoding) |
| Probability score | 0 ≤ x ≤ 1 |
| Timestamps | Within [system launch date, now + 1 day] |

## Skewness

| |skew| range | Classification | Recommendation |
|---|---|---|
| < 0.5 | Approximately normal | No action needed |
| 0.5 – 1.0 | Moderate skew | Note; consider log transform before modeling |
| > 1.0 | High skew | Investigate; log/sqrt transform likely needed |
| > 2.0 | Extreme skew | Investigate for outliers or data errors first |

## Correlation Flags

| |r| range | Action |
|---|---|
| ≥ 0.8 | Flag as strong pair — check for multicollinearity before including both in a model |
| ≥ 0.95 | Near-perfect — likely the same underlying measure; consider dropping one |
