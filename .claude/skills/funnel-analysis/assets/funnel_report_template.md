# Funnel Analysis Report — NYC DOT SIM

**Funnel:** [e.g. Inspection Lifecycle: Created → Assigned → Inspected → Violation → Resolved]
**Completion window:** [e.g. 90 days from created_date]
**Period analyzed:** [YYYY-MM-DD to YYYY-MM-DD]
**Dataset:** [e.g. inspection (dntt-gqwq) + violations (6kbp-uz6m), as of YYYY-MM-DD]
**Analyst:** [name]
**Date:** [YYYY-MM-DD]

---

## Summary Finding

[1–2 sentences: overall conversion rate and the single biggest drop-off point]

Example: "End-to-end conversion from inspection creation to resolution is 31.4%, with the largest single drop occurring between Inspection Conducted and Violation Issued (–42 percentage points), representing 1,847 inspections that did not result in a violation within 90 days."

---

## Funnel Table

| Step | Count | vs. Prior Step | vs. Top | Drop-Off |
|---|---|---|---|---|
| [1] Inspection Record Created | | 100% | 100% | — |
| [2] Assigned to Inspector | | | | –X (Y%) |
| [3] Inspection Conducted | | | | –X (Y%) |
| [4] Violation Issued | | | | –X (Y%) |
| [5] Resolved / Completed | | | | –X (Y%) |

**Completion window:** [N] days
**Total records in scope:** [n]

---

## Time Between Steps

| Transition | n | Median | P75 | P90 |
|---|---|---|---|---|
| Created → Assigned | | | | |
| Assigned → Inspected | | | | |
| Inspected → Violation | | | | |
| Violation → Resolved | | | | |
| **Created → Resolved (end-to-end)** | | | | |

**SLA alignment:** [e.g. Median end-to-end of 34 days exceeds HIGH tier SLA of 14 days]

---

## Borough Segment Comparison

| Borough | Top of Funnel | Completed | Conversion | Biggest Drop Step |
|---|---|---|---|---|
| Manhattan (MN) | | | | |
| Bronx (BX) | | | | |
| Brooklyn (BK) | | | | |
| Queens (QN) | | | | |
| Staten Island (SI) | | | | |
| **City Total** | | | | |

**Largest gap between boroughs:** [Borough A] vs [Borough B] — [X pp] difference at [step]

---

## Drop-Off Priority

Ranked by records lost (higher = bigger opportunity):

| Rank | Step | Records Lost | Drop Rate | Est. Impact |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |

---

## Root Causes (Hypotheses)

**Biggest drop: [Step X → Step Y]**

| Hypothesis | Evidence | Confidence |
|---|---|---|
| [e.g. Insufficient inspector capacity in BX] | [BX drop rate 12pp above average] | Medium |
| [e.g. Data entry lag — inspections done but not recorded] | [10% of nulls have downstream completion] | Low |
| [e.g. Seasonal winter slowdown] | [Drop concentrated in Dec–Feb cohorts] | High |

---

## Recommendations

| Priority | Recommendation | Expected Impact | Owner | Timeline |
|---|---|---|---|---|
| P1 | [Address biggest drop-off] | [+X pp conversion] | | |
| P2 | [Borough-specific action] | [+X records/month] | | |
| P3 | [Data quality improvement] | [Better measurement] | | |

---

## Data Notes

- Script: `scripts/funnel_analyzer.py`
- Exclusions: [e.g. Cancelled records (n=X); records with missing created_date (n=Y)]
- Right-censoring: [e.g. Records created after 2026-03-14 excluded from step-3+ analysis]
- Definition choices: [e.g. Used MIN(inspection_date) for records with multiple inspection events]
- Known data issues: [e.g. assigned_date missing for BX pre-2024 records — step 2 understated]
