# Assumption Types Reference Guide

A structured classification of analytical assumptions for NYC DOT inspection data analysis.
Use this reference when logging assumptions in `assets/assumptions_log_template.md` to ensure
every assumption is categorised, scoped, and impact-rated before finalising conclusions.

---

## Category 1: Data Assumptions

Assumptions about the dataset itself — what is included, excluded, or inferred from the raw records.

### 1.1 Coverage Assumptions
Assumptions about which records are present and which are missing.

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| Dataset is complete for the analysis period | "All inspections from Jan–May 2026 are in `dntt-gqwq`" | Undercounting violations in a borough |
| No systematic missing rows by borough | "BX records are as complete as MN records" | Borough-level comparisons become misleading |
| Deletions indicate closures, not data errors | "Rows absent this week but present last week were closed" | Inflated closure rates |

### 1.2 Population Scope Assumptions
Assumptions about which rows constitute the target population.

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| Status filter correctly isolates active violations | `WHERE status = 'OPEN'` captures all unresolved violations | Missed open violations, understated backlog |
| Borough codes are standardised | `BK` always means Brooklyn; no mixed-case or alias values | Cross-borough comparisons break |
| Unit IDs uniquely identify a sidewalk segment | `unit_id` is the correct join key between inspections and violations | Double-counting or missing joins |

### 1.3 Null-Handling Assumptions
Assumptions about how missing values are treated.

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| NULL `completion_date` = not yet completed | Ramp records with NULL `completion_date` excluded from completion rate | Rate denominator is wrong |
| NULL `defect_type` = unknown, not no defect | Nulls dropped rather than treated as "No Defect" category | Defect distribution is distorted |
| NULL `borough` excluded from borough analysis | Rows with no borough code removed rather than assigned | Borough totals don't reconcile to dataset total |

### 1.4 Deduplication Assumptions
Assumptions about uniqueness of records.

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| `objectid` is unique within a dataset | Used as primary key without checking for duplicates | Inflated counts, double-weighted metrics |
| One inspection per `unit_id` per day | Grouping by `unit_id` + date doesn't create duplicates | Metric values per unit are inflated |

---

## Category 2: Statistical Assumptions

Assumptions embedded in the statistical methods applied.

### 2.1 Distribution Assumptions

| Assumption | Context | When It Breaks |
|---|---|---|
| Rates are approximately normal | Using z-score CI for borough completion rates | n < 30 per borough; use Wilson Score CI instead |
| Residuals are normally distributed | Linear regression on inspection volume over time | Heavy-tailed seasonal spikes violate normality |
| Observations are independent | Comparing inspections across days | Same crew re-inspecting same block creates autocorrelation |

**NYC DOT rule of thumb:** For any rate or proportion with n < 1,000, always use Wilson Score binomial CI rather than normal approximation.

### 2.2 Stationarity Assumptions

| Assumption | Context | When It Breaks |
|---|---|---|
| Time series is stationary (mean-reverting) | Applying ARIMA to weekly inspection counts | Spring surge creates non-stationarity; difference first |
| Seasonal period is 7 days | Weekly cycle in field operations Mon–Fri | Holiday weeks break the pattern |
| Trend is linear | Fitting a linear regression slope to ramp completion progress | Backlog-clearing often follows an S-curve, not a line |

### 2.3 Sampling Assumptions

| Assumption | Context | When It Breaks |
|---|---|---|
| `max_rows=10000` random sample is representative | Quality scoring with limited fetch | If inspections cluster in one borough, the sample is biased |
| Stratified sample needed for borough comparisons | Comparing defect rates by borough | SI has far fewer rows; unstratified sample underrepresents SI |

### 2.4 Comparison Validity Assumptions

| Assumption | Context | When It Breaks |
|---|---|---|
| Comparison period has identical data collection methods | YoY comparison of violation rates | Program scope changes (e.g., new defect types added in 2024) invalidate YoY |
| Control and treatment groups are comparable | A/B-style borough comparison | MN has denser sidewalk network than SI; raw rates aren't comparable |

---

## Category 3: Business Logic Assumptions

Assumptions about what business rules, definitions, and thresholds are correct.

### 3.1 Definition Assumptions

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| "Closure" means completion_date is non-null | Rate = closed / total | If some records closed via other status flags, rate is understated |
| "High priority" = defect_type in ('CRACK_SEVERE', 'BROKEN', 'UPLIFT') | Flagging critical segments | Definition differs from field inspector handbook |
| SLA tier mapping is correct | HIGH=14d means 14 calendar days, not business days | SLA breach count is wrong |

### 3.2 Threshold Assumptions

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| Staleness threshold for ramp data is 30 days (MED SLA) | Alert fires at >30 days since `ramp_progress` last update | Program uses different SLA; over- or under-alerting |
| Quality score weights (35/25/25/15) reflect DOT priorities | Composite score comparisons across datasets | Freshness may be more critical for daily-updated violation datasets |
| 50m buffer radius is correct for conflict detection | `socrata conflict-detect --buffer 50` | Engineering standard may require 25m or 100m depending on street type |

### 3.3 Workflow Assumptions

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| Inspections trigger violations, not the reverse | Analysis reads inspection → violation flow as causal | Complaint-driven inspections (from `ramp_complaints`) reverse the flow |
| Field crew borough assignment is consistent | BX crew only generates BX inspection records | Cross-borough assignments corrupt geographic analysis |

---

## Category 4: Temporal Assumptions

Assumptions about time periods, freshness, and change over time.

### 4.1 Date Field Assumptions

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| `created_date` reflects actual event date, not data entry date | Used as event timestamp for trend analysis | Entry lag (inspections entered days after they occur) creates a recency bias |
| `inspection_date` is in UTC | Filtered with ISO 8601 UTC timestamps | Edge cases near midnight differ by timezone |
| Records with future dates are data errors | `WHERE created_date <= CURRENT_DATE` filter applied | Planned inspections may intentionally have future dates |

### 4.2 Freshness Assumptions

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| Dataset updated daily means updated as of yesterday | Treating today's data as reflecting yesterday's state | ETL pipelines may lag 24–48 hours beyond nominal refresh |
| `ramp_locations` (stale since 2021) not used for current analysis | Using `ramp_progress` instead | Analyst unfamiliar with known issue uses stale data |
| Seasonal pattern observed in 2024 repeats in 2025–2026 | Applying prior-year seasonality to forecast | Policy changes or weather anomalies break the pattern |

### 4.3 Period Comparability Assumptions

| Assumption | Example (NYC DOT) | Risk if Wrong |
|---|---|---|
| Same calendar months are comparable YoY | May 2025 vs May 2026 comparison | Holiday calendar differences shift inspection day counts |
| Pre/post policy change periods are clearly delineated | Comparing inspection volumes before and after a process change | Transition period contains mixed records from both regimes |

---

## Impact Rating Guide

Rate each logged assumption before finalising conclusions:

| Impact Level | Definition | Action Required |
|---|---|---|
| **HIGH** | If this assumption is wrong, the headline finding reverses or becomes unactionable | Validate with data or stakeholder before sharing results |
| **MEDIUM** | If wrong, the magnitude changes but direction holds | Document clearly; note range of outcomes in the output |
| **LOW** | If wrong, the effect on conclusions is negligible | Log it; no validation step needed |

---

## Quick-Reference Checklist

Before marking an analysis complete, verify each category has been logged:

- [ ] Data coverage: which records are included and why
- [ ] Null handling: how missing values are treated
- [ ] Deduplication: whether `objectid` uniqueness was verified
- [ ] Statistical method: which distribution / test assumptions apply
- [ ] Business definitions: how key terms (closure, priority, SLA tier) are defined
- [ ] Temporal scope: date fields used, timezone, freshness caveats
- [ ] High-impact assumptions validated or flagged for review
