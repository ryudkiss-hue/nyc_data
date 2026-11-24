# A/B Test Report — NYC DOT SIM

**Experiment name:** [e.g. Streamlined Inspection Workflow v2]
**Date range:** [YYYY-MM-DD] to [YYYY-MM-DD]
**Analyst:** [name]
**Status:** [Running / Concluded / Invalidated]

---

## 1. Experiment Design

| Field | Value |
|---|---|
| Hypothesis | [Treatment X will increase inspection completion rate by 5pp vs control] |
| Randomisation unit | [inspection record / inspector / district] |
| Traffic split | [50% control / 50% treatment] |
| Primary metric | [e.g. inspection completion rate] |
| Guardrail metrics | [e.g. dismissal rate, SLA breach rate] |
| Dataset | [e.g. inspection — dntt-gqwq] |
| Pre-registered MDE | [e.g. 3 percentage points] |
| Required n per arm | [calculated] |
| Target power | [80% / 90%] |

---

## 2. Sample Ratio Mismatch Check

| Variant | Assigned n | Expected n | Deviation |
|---|---|---|---|
| Control | | | |
| Treatment | | | |

**Chi2 statistic:** [value]
**p-value:** [value]
**SRM verdict:** [PASS — no SRM detected / FAIL — SRM detected, results invalid]

> If SRM is detected, stop here. Do not interpret results until SRM is resolved.

---

## 3. Primary Metric Results

| Variant | n | Rate / Mean | 95% CI |
|---|---|---|---|
| Control | | | |
| Treatment | | | |

**Absolute difference:** [value] ([lower], [upper])
**Relative lift:** [value%]
**Test statistic:** [z or t = value]
**p-value:** [value]
**Statistical significance:** [YES (p < 0.05) / NO]
**Statistical power:** [value%]

---

## 4. Guardrail Metric Results

| Metric | Control | Treatment | Diff | Significant? | Verdict |
|---|---|---|---|---|---|
| Dismissal rate | | | | | OK / FAIL |
| SLA breach rate | | | | | OK / FAIL |
| [other] | | | | | OK / FAIL |

---

## 5. Segment Analysis

| Borough | Control Rate | Treatment Rate | Lift | Significant? |
|---|---|---|---|---|
| MN (Manhattan) | | | | |
| BX (Bronx) | | | | |
| BK (Brooklyn) | | | | |
| QN (Queens) | | | | |
| SI (Staten Island) | | | | |

**Heterogeneity note:** [Any borough where effect is notably different from average?]

---

## 6. Decision Summary

**Overall recommendation:** [SHIP / NO SHIP / EXTEND / INVALIDATED]

**Rationale:**
- Primary metric: [significant / not significant / underpowered]
- Guardrail metrics: [all clear / [metric] degraded]
- SRM: [passed / failed]
- Power: [adequate / insufficient]

**Estimated operational impact if shipped:**
- Inspections per quarter affected: ~[n]
- Projected completion rate improvement: [+X pp]
- Estimated additional completions/quarter: [n]

**Next steps:**
1. [Action item]
2. [Action item]

---

## 7. Data Notes

- Data pulled from: [dataset name + fourfour]
- Date range of experiment data: [start] to [end]
- Known data issues: [e.g. none / stale data in BX for 3 days mid-experiment]
- Analysis script: `scripts/ab_test_analyzer.py`
- Command run: `python ab_test_analyzer.py [args]`
