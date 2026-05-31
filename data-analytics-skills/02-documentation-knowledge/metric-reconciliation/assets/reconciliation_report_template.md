# Metric Reconciliation Report

**Metric:** [metric name]
**Period:** [date or date range]
**Analyst:** [name]
**Date:** [YYYY-MM-DD]

---

## Values compared

| Source | Value | Query / Pipeline |
|---|---|---|
| Source A | [value] | [link or description] |
| Source B | [value] | [link or description] |

**Absolute difference:** [Source A − Source B]
**Percentage difference:** [(A − B) / A × 100]%
**Within tolerance:** Yes / No (tolerance: [threshold])

---

## Root cause

**Status:** Confirmed / Under investigation / No issue

**Cause category:** Filter difference / Join type / Grain mismatch / Definition drift / Refresh lag / Other

**Description:**
[One paragraph: what specific difference in the queries or pipelines explains the gap]

---

## Evidence

**Steps taken to identify the cause:**
1. [Step 1 — e.g., compared WHERE clauses]
2. [Step 2 — e.g., checked JOIN types]
3. [Step 3 — e.g., pulled row-level sample]

**Key finding:**
[The specific line of query or pipeline behaviour that explains the discrepancy]

---

## Resolution

**Designated source of truth:** [Source A / Source B / Neither — needs alignment]

**Action required:**
- [ ] Pipeline fix needed (owner: [name], by: [date])
- [ ] Query correction needed (owner: [name], by: [date])
- [ ] Definition clarification needed (owner: [name], by: [date])
- [ ] Downstream consumers need recalculation (list: [])
- [ ] No action — gap is within tolerance

---

## Preventive measure

[How will we catch this earlier in future? e.g., automated reconciliation check, CI test, data quality alert]

---

*Template: reconciliation_report_template.md*
