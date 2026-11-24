# Cohort Retention Report — NYC DOT SIM

**Analysis type:** [Inspection resolution / Ramp completion / Violation closure]
**Cohort definition:** [e.g. Month of created_date]
**Retention event:** [e.g. completion_date populated]
**Granularity:** [Monthly / Weekly / Quarterly]
**Periods tracked:** [e.g. 12 months]
**Dataset:** [e.g. inspection — dntt-gqwq, as of YYYY-MM-DD]
**Analyst:** [name]
**Date:** [YYYY-MM-DD]

---

## Key Findings

1. **Overall retention:** [e.g. Median 30-day completion rate is 52%, improving to 78% by 6 months]
2. **Trend:** [Improving / Stable / Declining — compare oldest vs. newest mature cohorts]
3. **Cliff drops:** [e.g. No significant cliff detected / Drop at period 2 (68%→51%) warrants investigation]
4. **Borough spread:** [e.g. MN cohorts resolve 8pp faster than SI cohorts at period 3]

---

## Cohort Size Summary

| Cohort | n | Quick-Resolve (P0) | 30-day (P1) | 90-day (P3) | 6-month (P6) |
|---|---|---|---|---|---|
| [Month-YY] | | | | | |
| [Month-YY] | | | | | |
| [Month-YY] | | | | | |
| **Median** | | | | | |
| **Benchmark** | | 30–40% | 45–55% | 65–75% | 75–82% |

_Right-censored cells (cohort too recent) marked as `--`_

---

## Retention Heatmap

[Insert heatmap image or ASCII representation]

Color scale: Dark green = high retention (>80%), Yellow = medium (50–79%), Red = low (<50%)

---

## Cohort Trend Analysis

**Are recent cohorts better or worse than historical cohorts?**

| Cohort Group | Avg P1 Retention | vs. Prior Group | Trend |
|---|---|---|---|
| [Jan–Mar 2025] | | | Baseline |
| [Apr–Jun 2025] | | | |
| [Jul–Sep 2025] | | | |
| [Oct–Dec 2025] | | | |
| [Jan–Mar 2026] | | | |

**Interpretation:** [e.g. Recent cohorts show 4pp improvement in P1 retention, consistent with workflow changes implemented in Q3 2025]

---

## Borough Segment Analysis

| Borough | n (cohorts) | Avg P1 | Avg P3 | Avg P6 | vs. City Avg |
|---|---|---|---|---|---|
| Manhattan (MN) | | | | | |
| Bronx (BX) | | | | | |
| Brooklyn (BK) | | | | | |
| Queens (QN) | | | | | |
| Staten Island (SI) | | | | | |

---

## Notable Patterns

**Cliff drops identified:**
- [Period X→Y: median drop of Z pp — likely cause: ]
- [None detected]

**Seasonal effects:**
- [e.g. December/January cohorts show 6pp lower P1 retention consistent with winter inspection slowdown]

**Outlier cohorts:**
- **Best:** [Month-YY] — [reason if known]
- **Worst:** [Month-YY] — [reason if known]

---

## SLA Alignment

Based on cohort data, **[X%]** of inspections complete within **[SLA tier]** threshold of **[N] days**.

| SLA Tier | Threshold | Achieved By Period | % Within SLA |
|---|---|---|---|
| HIGH | 14 days | Period 0–1 | [value] |
| MEDIUM | 30 days | Period 1 | [value] |
| LOW | 60 days | Period 2 | [value] |

---

## Recommendations

1. **[Priority action]** — [e.g. Investigate cliff at period 2: review what distinguishes records that close within 60d vs. those that remain open >90d]
2. **[Borough action]** — [e.g. SI's P3 rate (55%) is 12pp below city average — flag for capacity review]
3. **[Process action]** — [e.g. P0 quick-resolve rate of 38% suggests potential for same-period closure with faster data entry workflows]

---

## Data Notes

- Script: `scripts/cohort_builder.py`
- Exclusions: [e.g. Cancelled records excluded; records missing created_date excluded (n=X)]
- Right-censored cohorts: [e.g. Apr–Jun 2026 cohorts excluded from P3+ comparisons]
- Known data issues: [e.g. none / ramp_locations not used — stale since 2021]
