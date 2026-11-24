# NYC DOT SIM Operations Metrics Report

**Period:** [Month YYYY] / [Quarter YYYY] / [FY YYYY]
**Analyst:** [name]
**Dataset vintage:** [e.g. inspection data as of 2026-06-14]
**Prepared:** [YYYY-MM-DD]

---

## Executive Summary

[2–3 sentences: top-line performance vs. prior period and vs. target. Lead with the most operationally important finding.]

---

## 1. Throughput Metrics

| Metric | Current Period | Prior Period | MoM Change | YTD | Target | Status |
|---|---|---|---|---|---|---|
| Inspections completed | | | | | | ✓ / ✗ |
| Violations resolved | | | | | | ✓ / ✗ |
| Ramps completed | | | | | | ✓ / ✗ |
| Dismissals | | | | | | ✓ / ✗ |

**Rolling 3M average (inspections):** [value]
**Trend:** [Improving / Stable / Declining]

---

## 2. SLA Compliance

| SLA Tier | Threshold | Compliant | Total | Compliance Rate | Benchmark | Grade |
|---|---|---|---|---|---|---|
| HIGH | 14 days | | | | ≥ 85% | G/A/P |
| MEDIUM | 30 days | | | | ≥ 85% | G/A/P |
| LOW | 60 days | | | | ≥ 85% | G/A/P |

**Median days to close:** [value]
**P90 days to close:** [value]

---

## 3. Borough Scorecard

| Borough | Inspections | Completion Rate | vs. Avg | SLA Compliance | Grade |
|---|---|---|---|---|---|
| Manhattan (MN) | | | | | |
| Bronx (BX) | | | | | |
| Brooklyn (BK) | | | | | |
| Queens (QN) | | | | | |
| Staten Island (SI) | | | | | |
| **City Total** | | | | | |

---

## 4. Ramp Program

| Borough | Total Ramps | Completed | Rate | 95% CI | vs. Prior Qtr |
|---|---|---|---|---|---|
| MN | | | | | |
| BX | | | | | |
| BK | | | | | |
| QN | | | | | |
| SI | | | | | |

_CI method: Wilson Score (used when n < 1000 per borough)_

---

## 5. Unit Economics

| Metric | Value | Prior Period | Change |
|---|---|---|---|
| Cost per inspection (CPI) | $ | $ | |
| Inspections per inspector/month | | | |
| Cost per resolved violation | $ | $ | |

---

## 6. Benchmark Comparison

| Metric | Actual | Good | Average | Poor | Grade |
|---|---|---|---|---|---|
| Completion rate | | ≥ 75% | 60–74% | < 60% | |
| Resolution rate (30d) | | ≥ 70% | 55–69% | < 55% | |
| SLA compliance (HIGH) | | ≥ 85% | 75–84% | < 75% | |
| Dismissal rate | | < 20% | 20–30% | > 30% | |
| Ramp completion | | ≥ 70% | 50–69% | < 50% | |

---

## 7. Key Insights

1. **[Insight 1]** — [1 sentence finding + operational implication]
2. **[Insight 2]** — [1 sentence finding + operational implication]
3. **[Insight 3]** — [1 sentence finding + operational implication]

---

## 8. Recommendations

| Priority | Recommendation | Owner | Timeline |
|---|---|---|---|
| P1 | | | |
| P2 | | | |
| P3 | | | |

---

## 9. Data Notes

- Datasets used: inspection (dntt-gqwq), violations (6kbp-uz6m), ramp_progress (e7gc-ub6z), dismissals (p4u2-3jgx)
- Data as of: [date]
- Known issues: [e.g. ramp_locations stale since 2021 — not used in this report]
- Definition choices: [any deviations from standard definitions in metric_definitions.md]
- Script: `scripts/saas_metrics.py`
