# A/B Test Report

**Test name:** [descriptive name]
**Owner:** [name / team]
**Dates:** [start date] to [end date]
**Status:** Running / Analysis complete / Decision made

---

## Hypothesis

**Change tested:** [What was changed in treatment vs control]
**Expected effect:** [What metric should move and in which direction]
**Rationale:** [Why we expected this effect]

---

## Design

| Parameter | Value |
|---|---|
| Traffic split | [50/50 / 80/20 / other] |
| Randomisation unit | [user / session / device] |
| Primary metric | [metric name and definition] |
| Guardrail metrics | [list] |
| Minimum detectable effect | [absolute value and % relative] |
| Required sample size (per group) | [n] |
| Pre-specified alpha | [0.05 / 0.01] |
| Pre-specified power | [80% / 90%] |

---

## Results

### Sample Ratio Mismatch (SRM) check

| Group | Expected | Actual | Difference |
|---|---|---|---|
| Control | [n] | [n] | [%] |
| Treatment | [n] | [n] | [%] |

**SRM detected:** Yes / No (chi2=[value], p=[value])

> If SRM detected: **Stop. Do not interpret results. Investigate assignment mechanism.**

---

### Primary metric

| Group | N | Metric value | 95% CI |
|---|---|---|---|
| Control | [n] | [value] | — |
| Treatment | [n] | [value] | [lower, upper] |

**Absolute difference:** [value] ([%])
**Relative lift:** [+/-]%
**p-value:** [value]
**Significant at alpha=[value]:** Yes / No

---

### Guardrail metrics

| Metric | Control | Treatment | Change | Pass |
|---|---|---|---|---|
| [metric] | [value] | [value] | [+/-%] | Yes / No |

---

### Segment breakdowns

| Segment | Control rate | Treatment rate | Lift | Significant |
|---|---|---|---|---|
| [segment] | [value] | [value] | [%] | Yes / No |

---

## Decision

**Verdict:** Ship / Do not ship / Extend test / Inconclusive

**Reasoning:**
[2–4 sentences explaining the decision in light of primary metric, guardrails, and segment results]

**Next steps:**
1. [action — owner — date]
2. [action — owner — date]

---

*Template: ab_test_report_template.md*
