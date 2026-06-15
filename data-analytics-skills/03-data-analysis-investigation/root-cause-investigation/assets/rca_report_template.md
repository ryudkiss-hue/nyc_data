# Root Cause Analysis Report

> Fill one section at a time. Do not skip Section 1 (change validation) — many
> reported metric changes turn out to be data artifacts, not real operational shifts.

---

## Report Header

| Field | Value |
|-------|-------|
| **Analysis title** | [e.g., Violation closure rate drop — Brooklyn, May 2026] |
| **Metric investigated** | [e.g., violation_closure_rate] |
| **Analyst** | [name] |
| **Date completed** | [YYYY-MM-DD] |
| **Status** | Draft / Under Review / Final |
| **Priority** | High / Medium / Low |

---

## Section 1: Change Validation

*Goal: Confirm the metric movement is real and not a data artifact.*

### 1.1 Reported change

| Item | Value |
|------|-------|
| **Metric** | [e.g., violation closure rate] |
| **Baseline period** | [e.g., April 2026] |
| **Comparison period** | [e.g., May 2026] |
| **Baseline value** | [e.g., 68.4%] |
| **Comparison value** | [e.g., 56.2%] |
| **Absolute change** | [e.g., -12.2 percentage points] |
| **Relative change** | [e.g., -17.8%] |
| **Borough scope** | [e.g., BK only / all boroughs] |

### 1.2 Statistical significance check

- Rolling 4-week average ± 2σ baseline: [e.g., 66% ± 4.1%]
- Does the comparison value fall outside the normal range? [Yes / No]
- If No: stop here — this is normal variance, not a real change.
- Sample sizes: baseline n = [X], comparison n = [Y]
- Method used: [e.g., two-proportion z-test, Wilson Score CI]

### 1.3 Data quality checks

- [ ] Verified no ETL pipeline failures during the comparison period
- [ ] Checked for duplicate records that could inflate the denominator
- [ ] Confirmed `status` field encoding has not changed (schema drift check)
- [ ] Verified `completion_date` null handling is consistent across periods
- [ ] Confirmed dataset was refreshed on schedule (SLA check)

**Verdict:** [Real change / Data artifact / Inconclusive — requires further investigation]

---

## Section 2: Timing and Pattern

*Goal: Pinpoint when the change began and whether it is sudden or gradual.*

### 2.1 Time series summary

| Week | Closure Rate | Notes |
|------|-------------|-------|
| [Week -4] | [%] | |
| [Week -3] | [%] | |
| [Week -2] | [%] | |
| [Week -1] | [%] | [Last normal week] |
| [Week 0] | [%] | [First anomalous week] |
| [Week +1] | [%] | |
| [Week +2] | [%] | |

### 2.2 Pattern classification

- [ ] Sudden step-change (single-week shift)
- [ ] Gradual decline (multi-week trend)
- [ ] Spike and recovery (transient event)
- [ ] Seasonal (expected from prior-year pattern)

**Change began:** [date or week]
**Pattern type:** [sudden / gradual / transient / seasonal]

---

## Section 3: Metric Decomposition

*Goal: Identify which sub-component(s) drove the top-level metric change.*

The closure rate = `closed_violations / total_open_violations`.

A drop can be caused by:
1. Fewer closures (numerator fell)
2. More new violations opened (denominator grew)
3. Both simultaneously

### 3.1 Component analysis

| Component | Baseline | Comparison | Change | % of Total Change |
|-----------|---------|------------|--------|-------------------|
| Closed violations (n) | | | | |
| Total open violations (n) | | | | |
| New violations opened | | | | |
| Violations carried over | | | | |

### 3.2 Primary driver

The change is primarily driven by: [numerator / denominator / both]

Interpretation: [e.g., "The number of closures fell by 340 while new violations
held steady — the backlog is not growing, but clearance pace slowed."]

---

## Section 4: Dimensional Drilldown

*Goal: Identify which borough, defect type, material type, or crew explains most of the change.*

### 4.1 Borough contribution

| Borough | Baseline Rate | Comparison Rate | Change (pp) | Contribution to Total Change |
|---------|--------------|----------------|-------------|------------------------------|
| MN | | | | |
| BX | | | | |
| BK | | | | |
| QN | | | | |
| SI | | | | |
| **Total** | | | | **100%** |

### 4.2 Defect type breakdown

| Defect Type | Baseline Closure Rate | Comparison Closure Rate | Change (pp) |
|-------------|----------------------|-----------------------|-------------|
| CRACK_SEVERE | | | |
| BROKEN | | | |
| UPLIFT | | | |
| CRACK_MINOR | | | |
| WORN | | | |
| Other | | | |

### 4.3 Material type breakdown (if applicable)

| Material Type | Baseline Rate | Comparison Rate | Change (pp) |
|--------------|--------------|----------------|-------------|
| CONCRETE | | | |
| ASPHALT | | | |
| BRICK | | | |
| Other | | | |

### 4.4 Dimensional summary

The change is concentrated in: [e.g., "Brooklyn (BK) accounts for 71% of the total
drop. Within BK, CRACK_SEVERE defects show the largest rate decline (-18pp)."]

---

## Section 5: Hypothesis Testing

*Goal: Identify the most likely cause by correlating the change with known events.*

### 5.1 Known events log

List events that occurred before or around the change onset date:

| Date | Event | Source | Plausible cause? |
|------|-------|--------|-----------------|
| [date] | [e.g., BK crew reassigned to emergency pothole response after storm] | [Operations log] | High |
| [date] | [e.g., New violation category added: UPLIFT_MAJOR] | [Schema changelog] | Medium |
| [date] | [e.g., Socrata API migration — dataset briefly unavailable] | [IT incident log] | Low |

### 5.2 Hypothesis ranking

| Hypothesis | Evidence For | Evidence Against | Confidence |
|-----------|-------------|-----------------|------------|
| [H1: Crew capacity diverted] | [BK crew count down 30% in May per dispatch log] | [Other boroughs unaffected] | High |
| [H2: New defect category inflating denominator] | [UPLIFT_MAJOR rows appeared in May] | [Count is small; <2% of total] | Low |
| [H3: Data pipeline lag] | [Known ETL delay on May 14] | [Delay resolved by May 16; trend persists through month] | Low |

### 5.3 Validated hypothesis

**Primary cause:** [e.g., "Crew capacity diversion to emergency pothole response
reduced BK violation closure throughput by approximately 340 closures in May."]

**Evidence summary:** [2–3 sentences citing specific numbers and sources]

**Confidence level:** High / Medium / Low

---

## Section 6: Recommendations

*Tier recommendations by urgency and impact.*

### Tier 1 — Immediate actions (within 1 week)

- [ ] [e.g., Restore BK crew allocation to normal levels — target: 2026-06-07]
- [ ] [e.g., Prioritise CRACK_SEVERE closures in BK backlog — estimated 340 units]

### Tier 2 — Short-term actions (within 30 days)

- [ ] [e.g., Set automated alert if borough closure rate drops >10pp vs 4-week average]
- [ ] [e.g., Review crew diversion policy to require data team notification when borough
  capacity falls >20%]

### Tier 3 — Long-term / monitoring

- [ ] [e.g., Build monthly closure rate dashboard with borough-level trend lines]
- [ ] [e.g., Document crew diversion events in event log for future RCA correlation]

---

## Section 7: Appendix

### 7.1 Data sources used

| Dataset | Key | Rows fetched | Date range | Freshness at time of analysis |
|---------|-----|-------------|------------|-------------------------------|
| violations | 6kbp-uz6m | | | |
| inspection | dntt-gqwq | | | |
| dismissals | p4u2-3jgx | | | |

### 7.2 Queries / scripts run

```python
# Example: fetch violation closure rate by borough for April–May 2026
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe(
    "data.cityofnewyork.us",
    "6kbp-uz6m",
    where="created_date >= '2026-04-01T00:00:00' AND created_date < '2026-06-01T00:00:00'",
    select="objectid,borough,status,completion_date,created_date",
    max_rows=50000
)
```

### 7.3 Assumptions and limitations

| Assumption | Impact if wrong |
|------------|----------------|
| `completion_date IS NOT NULL` = closed | Medium — if status field also captures closures, rate is understated |
| April = valid baseline (no known anomalies) | High — if April was also anomalous, the comparison is invalid |
| Crew assignment data from operations log is accurate | Medium — if log is incomplete, H1 confidence drops |

### 7.4 Reviewer sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Lead Analyst | | | |
| Peer Reviewer | | | |
| Program Manager | | | |
