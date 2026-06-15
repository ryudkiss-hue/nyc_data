# Quality Thresholds Reference — EDA Skill

Default thresholds used by `null_profiler.py`, `outlier_detector.py`, and the
EDA checklist. Override on the command line or by editing this file for project-specific tolerances.

---

## Null Rate Thresholds

Applied per-column based on whether the field is required.

| Severity | Required Field Null % | Optional Field Null % |
|---|---|---|
| CRITICAL | > 5% | — |
| MAJOR | > 1% | > 25% |
| MINOR | > 0% | > 10% |
| ok | 0% | ≤ 10% |

**NYC DOT context:** The `objectid`, `borough`, `status`, and primary date column
are always treated as required. Geometry columns (`latitude`, `longitude`, `the_geom`)
are optional but flagged MINOR when > 10% null because spatial analysis breaks down.

---

## Outlier Thresholds

### IQR Method (default multiplier: 1.5)
- A value is an outlier if it falls below `Q1 - 1.5 × IQR` or above `Q3 + 1.5 × IQR`.
- Multiplier 3.0 gives "extreme outlier" detection (Tukey).

### Z-Score Method (default threshold: 3.0)
- A value is flagged if `|z| > threshold` where `z = (x - mean) / std`.
- Use threshold 2.5 for stricter detection on small samples (n < 500).

### Decision Rules
| Outlier % | Decision |
|---|---|
| > 5% | INVESTIGATE — likely data error or skewed distribution needing transformation |
| 1–5% | REVIEW — check against business rules; may be legitimate edge cases |
| < 1% | ok — document but do not act unless domain context flags them |

---

## Duplicate Thresholds

| Severity | Duplicate Rate on Primary Key |
|---|---|
| CRITICAL | > 1% |
| MAJOR | > 0.1% |
| MINOR | > 0.01% |
| ok | ≤ 0.01% |

---

## Cardinality Thresholds (for Categorical Columns)

| Category | Unique Value Count | Action |
|---|---|---|
| Low cardinality (expected) | ≤ 20 | Check for unexpected values |
| Medium cardinality | 21–500 | Spot-check top/bottom values |
| High cardinality | > 500 | Verify it is intentional (ID, freetext) |
| Near-unique | > 90% distinct | Likely an ID column — skip EDA |

**Borough column** must have exactly 5 unique values (MN, BX, BK, QN, SI) or their
full-name equivalents. More = validity violation.

---

## Correlation Thresholds

| |r| value | Flag |
|---|---|---|
| ≥ 0.95 | CRITICAL — likely redundant columns or data leak |
| 0.80 – 0.95 | MAJOR — investigate before including both in a model |
| 0.60 – 0.80 | MINOR — note for analysts; may indicate derived fields |
| < 0.60 | ok |

---

## Freshness Thresholds

Inherited from SLA config (`data/sla_config.json`). Defaults:

| SLA Tier | Max Days Since Last Update |
|---|---|
| HIGH | 14 |
| MEDIUM | 30 |
| LOW | 60 |

For EDA purposes, flag any dataset older than 30 days as STALE regardless of SLA tier
unless explicitly overridden.

---

## Overriding Defaults

Pass flags to scripts to override:

```bash
# Stricter null threshold for critical pipeline
python null_profiler.py --key violations --threshold-critical 2 --threshold-major 15

# Extreme outlier detection only
python outlier_detector.py --key inspection --method iqr --iqr-multiplier 3.0
```
