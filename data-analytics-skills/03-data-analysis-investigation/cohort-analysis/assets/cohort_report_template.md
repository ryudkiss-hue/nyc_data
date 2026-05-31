# Cohort Analysis Report: [Product / Feature Name]

**Analyst:** [Name]  
**Date:** [YYYY-MM-DD]  
**Cohort definition:** Users who [e.g. signed up] between [start date] and [end date]  
**Retention event:** [e.g. logged in at least once in the period]  
**Granularity:** [Monthly / Weekly / Daily]  
**Minimum cohort size:** [e.g. 100 users — smaller cohorts excluded]

---

## Summary

In [one sentence, state the headline finding — e.g. "Month-1 retention has improved from 28% in Q1 to 39% in Q3, driven by the onboarding redesign shipped in April."]

| Metric | Value |
|---|---|
| Cohorts analysed | [N cohorts from X to Y] |
| Total users in scope | [N] |
| Average Period-1 retention | [X%] |
| Average Period-3 retention | [X%] |
| Stable retention (Period 6+) | [X%] |

---

## Retention Matrix

*(Paste or embed retention matrix from `scripts/retention_matrix.py` output)*

| Cohort | Size | P0 | P1 | P2 | P3 | P6 | P12 |
|---|---|---|---|---|---|---|---|
| [date] | | 100% | | | | | |

Full heatmap: see `assets/retention_matrix.html`

---

## Key Findings

### Finding 1: [Title]
[Cohort X shows notably higher/lower retention at period N than peers.]

- **What:** [Specific numbers]
- **Why (hypothesis):** [Reason this might be happening]
- **Recommended action:** [Investigate / Intervene / Monitor]

### Finding 2: [Title]
[Describe a second finding]

### Finding 3: [Title]
[Describe a third finding]

---

## Trend Analysis

**Cohort comparison (Period-1 retention over time):**

| Quarter | Average P1 Retention | Trend |
|---|---|---|
| Q1 [year] | | |
| Q2 [year] | | ↑ / ↓ / → |
| Q3 [year] | | |

**Interpretation:** [Are cohorts improving, declining, or flat? What might explain the trend?]

---

## Segment Breakdown (if applicable)

| Segment | Cohorts | Avg P1 | Avg P3 | Notes |
|---|---|---|---|---|
| [e.g. Organic] | | | | |
| [e.g. Paid] | | | | |

---

## Caveats & Limitations

- [e.g. Cohorts from November and December 2023 are immature — P12 data not available]
- [e.g. Test accounts excluded — N = X accounts filtered]
- [e.g. Retention event definition changed in March 2024 — pre/post comparison should be treated with caution]

---

## Recommended Next Steps

1. [ ] [Action — e.g. Investigate why Cohort X has 15% higher P1 retention than peers]
2. [ ] [Action — e.g. Share findings with Product team — retention improvement in Q3 correlates with onboarding redesign]
3. [ ] [Action — e.g. Set up automated retention tracking — alert if P1 drops below 30%]
