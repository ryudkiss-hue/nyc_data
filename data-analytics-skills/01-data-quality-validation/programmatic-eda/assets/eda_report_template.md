# EDA Report: [Dataset Name]

**Analyst:** [Name]  
**Date:** [YYYY-MM-DD]  
**Dataset:** [file path or table reference]  
**Business context:** [What does one row represent? What decision does this data inform?]

---

## 1. Dataset Overview

| Property | Value |
|---|---|
| Row count | |
| Column count | |
| Memory (MB) | |
| Date range | [earliest] → [latest] |
| Grain | [e.g. one row per user per day] |
| Primary key | [column name] — unique? [Yes / No — N duplicates] |

### Schema Summary

| Column | Dtype | Non-null % | Notes |
|---|---|---|---|
| | | | |

---

## 2. Null / Completeness Profile

*(Copy output from `null_profiler.py`)*

| Column | Null % | Status | Action |
|---|---|---|---|
| | | FAIL / WARN / OK | |

**Key findings:**
- [Column X is 45% null — expected? Needs business explanation.]
- [Column Y has 0 nulls — pipeline enforcing NOT NULL.]

---

## 3. Duplicate Analysis

| Check | Result |
|---|---|
| Full-row duplicates | [N rows, N% of total] |
| Key duplicates (`[key_col]`) | [N entities appear more than once] |

**Notes:** [Are duplicates intentional versioning? Data pipeline bug?]

---

## 4. Validity Checks

| Column | Check | Result | Notes |
|---|---|---|---|
| | [Age ≥ 0] | PASS / FAIL | |
| | [Revenue ≥ 0] | PASS / FAIL | |
| | [Date in range] | PASS / FAIL | |

---

## 5. Distributions

*(Copy descriptive stats from `distribution_summary.py`)*

| Column | Mean | Median | Std | p5 | p95 | Skew | Flag |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

**Histogram findings:**
- [Column X is right-skewed (skew = 2.4) — likely needs log transform before modeling.]
- [Column Y is bimodal — suggests two distinct user populations.]

---

## 6. Outliers

*(Copy from `outlier_detector.py`)*

| Column | Outlier Count | Outlier % | Classification | Decision |
|---|---|---|---|---|
| | | | Real / Error / Sentinel | Keep / Remove / Investigate |

---

## 7. Correlations

*(Copy from `correlation_explorer.py`)*

**Strong pairs (|r| ≥ 0.8):**

| Col A | Col B | r | Explanation |
|---|---|---|---|
| | | | |

---

## 8. Business Logic Checks

| Check | Result | Notes |
|---|---|---|
| [Revenue correlates with order count] | PASS / FAIL | |
| [Segment totals reconcile with aggregate] | PASS / FAIL | |
| [Derived columns match source calculation] | PASS / FAIL | |

---

## 9. EDA Checklist Sign-off

- [ ] All 40 checklist items reviewed (`references/eda_checklist.md`)
- [ ] All FAIL items resolved or risk-accepted
- [ ] Findings summary written (`assets/findings_summary.md`)

**EDA status:** [Ready to proceed / Needs data fix / Escalated to data engineering]
