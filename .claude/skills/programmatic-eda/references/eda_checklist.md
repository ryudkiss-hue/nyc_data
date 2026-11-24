# EDA Checklist — NYC DOT SIM Datasets

Work through every item before declaring a dataset profiled and ready for analysis.
Check each box as you complete it. Leave a note explaining any skipped items.

---

## 1. Load & Overview

- [ ] Row count confirmed — matches expected range from dataset registry?
- [ ] Column count matches expected schema (see `DATA_DICTIONARY.md`)
- [ ] Data grain identified — what does one row represent?
  - `inspection` → one inspection event per location
  - `violations` → one violation notice
  - `ramp_progress` → one ramp repair record
  - `dismissals` → one dismissal action
  - `street_permits` → one permit application
- [ ] Sample rows inspected — no obvious encoding issues or garbage values
- [ ] Memory footprint acceptable for in-memory analysis (< 2 GB for pandas)

---

## 2. Null Profile (`null_profiler.py`)

- [ ] Null report generated for all columns
- [ ] CRITICAL findings reviewed and root cause identified
- [ ] MAJOR findings documented in findings summary
- [ ] Geometry columns (`latitude`, `longitude`) null rate noted
- [ ] Decision recorded: drop nulls / impute / flag / leave as-is per column

---

## 3. Outlier Detection (`outlier_detector.py`)

- [ ] IQR outliers computed on all numeric columns
- [ ] Z-score outliers computed on all numeric columns
- [ ] Outlier rows spot-checked — real signal vs data error?
- [ ] `house_number` outliers verified (valid range: 1–99999)
- [ ] `latitude`/`longitude` outliers verified (NYC bbox: lat 40.4–40.95, lon -74.26–-73.7)
- [ ] Outlier decision recorded per flagged column

---

## 4. Distribution Summary

- [ ] Descriptive stats (mean, median, std, min/max, P5/P95) reviewed per numeric column
- [ ] Histograms spot-checked for obvious bimodal or truncated distributions
- [ ] `borough` frequency table matches expected borough distribution (no borough > 60% or < 3%)
- [ ] `status` frequency table — unexpected status values?
- [ ] Date columns: min/max dates within valid range; no future dates

---

## 5. Cardinality & Categorical Review

- [ ] `borough` has exactly 5 expected values (MN/BX/BK/QN/SI or full names)
- [ ] `status` column values match documented valid values
- [ ] High-cardinality text columns identified (> 500 unique values = likely ID or freetext)
- [ ] Top/bottom 10 values checked for unexpected categories

---

## 6. Correlation Exploration

- [ ] Correlation matrix computed on numeric columns
- [ ] Pairs with |r| > 0.8 identified and reviewed
- [ ] No obvious data leakage (e.g. completion_rate derived from completed_count / total)
- [ ] Near-constant columns (std < 0.001) identified and considered for removal

---

## 7. Freshness Check

- [ ] `last_modified` date retrieved from Socrata metadata
- [ ] Age in days computed; compared against SLA tier
- [ ] Stale datasets flagged with note in findings summary
- [ ] If stale: fallback data source identified or stakeholder notified

---

## 8. Sign-off

| Item | Status | Notes |
|---|---|---|
| Null profile | | |
| Outlier review | | |
| Distribution review | | |
| Categorical validation | | |
| Freshness check | | |
| Findings summary written | | |

**Analyst:** ________________________________
**Date:** ____________________________________
**Dataset(s) covered:** _____________________
