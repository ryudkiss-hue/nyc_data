# Root Cause Analysis Report

**Metric affected:** [metric name]
**Movement:** [direction and magnitude — e.g., "Revenue down 12% WoW"]
**Detection date:** [YYYY-MM-DD]
**Investigation owner:** [name]
**Status:** Open / Root cause identified / Resolved

---

## Signal confirmation

- **Confirmed real:** Yes / No
- **Data sources checked:** [list]
- **ETL / pipeline freshness verified:** Yes / No — [notes]
- **Magnitude:** [absolute value] ([%]) vs [comparison period]
- **Onset date:** [YYYY-MM-DD (± [n] days)]

---

## Scope of impact

| Dimension | Affected | Not affected |
|---|---|---|
| Geography | [regions] | [regions] |
| Platform | [platforms] | [platforms] |
| User segment | [segments] | [segments] |
| Product area | [areas] | [areas] |

---

## Timeline

| Date | Event |
|---|---|
| [date] | [deployment / release / campaign] |
| [date] | [metric movement onset] |
| [date] | [investigation started] |

---

## Hypotheses

| # | Hypothesis | Evidence for | Evidence against | Verdict |
|---|---|---|---|---|
| 1 | [hypothesis] | [data points] | [data points] | Confirmed / Refuted / Inconclusive |
| 2 | [hypothesis] | [data points] | [data points] | Confirmed / Refuted / Inconclusive |
| 3 | [hypothesis] | [data points] | [data points] | Confirmed / Refuted / Inconclusive |

---

## Root cause

**Confirmed cause:** [one sentence]

**Explanation:**
[2–4 sentences: what happened, why it happened, how it caused the metric movement]

**Impact quantification:**
- Affected users: [n] ([%])
- Revenue impact: $[value]
- Duration: [start] to [end or ongoing]

---

## Resolution

**Corrective action:** [what is being done to fix the issue]
**Owner:** [name]
**Target resolution date:** [YYYY-MM-DD]
**Status:** [not started / in progress / resolved]

---

## Preventive measures

| Measure | Owner | Target date |
|---|---|---|
| [e.g., Add alert for >5% WoW drop] | [name] | [date] |
| [e.g., Add deployment checklist item] | [name] | [date] |

---

*Template: rca_report_template.md*
