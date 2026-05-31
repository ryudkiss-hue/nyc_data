# Analytical Rigour Checklist

Use during peer review to assess whether the analysis is logically sound and draws conclusions the data can support.

---

## 1. Question–Method Alignment

- [ ] The method chosen is appropriate for the question (e.g. regression for "what predicts X", not correlation)
- [ ] The unit of analysis matches the question (user-level, order-level, session-level)
- [ ] The time period is appropriate for the claim (not too short to be meaningful, not so long that it includes structurally different periods)
- [ ] The definition of key terms matches what the stakeholder means, not just what's easy to measure

---

## 2. Data Validity

- [ ] The data covers the population the question is about (no inadvertent exclusions)
- [ ] Known data quality issues are documented and their effect on conclusions assessed
- [ ] Baseline and comparison periods use the same data source and definitions
- [ ] Any joins are validated — row counts before/after are plausible

---

## 3. Statistical Validity

- [ ] Sample size is adequate for the precision of claims being made
- [ ] Uncertainty is communicated (confidence intervals, sensitivity analysis, or explicit confidence level)
- [ ] Multiple testing correction is applied if many hypotheses are tested simultaneously
- [ ] Statistical results are not over-interpreted — significance ≠ importance
- [ ] Absence of evidence is not treated as evidence of absence

---

## 4. Causal Claims

- [ ] Correlation is not misrepresented as causation in the written conclusions
- [ ] If a causal claim is made, it is supported by one of: experiment, natural experiment, causal model, or strong theoretical prior — not correlation alone
- [ ] Confounders are acknowledged when a causal claim is made

---

## 5. Robustness

- [ ] The conclusion holds under at least one alternative analytical approach
- [ ] The result was checked for sensitivity to key assumptions
- [ ] Outlier impact was assessed: does the conclusion hold when outliers are excluded?
- [ ] The result makes sense directionally given domain knowledge

---

## 6. Communication

- [ ] Each conclusion is directly linked to evidence in the analysis
- [ ] No conclusions go beyond what the data shows
- [ ] Limitations are stated clearly and prominently — not buried
- [ ] The "so what" (recommendation or decision implication) is explicit
- [ ] Numbers are formatted consistently and at appropriate precision
- [ ] Chart types are appropriate and axes are clearly labelled

---

## Severity Guide for Issues Found

| Severity | Definition | Reviewer action |
|---|---|---|
| **Must fix** | Changes the conclusion or makes the output wrong | Block delivery; author must resolve |
| **Should fix** | Weakens confidence in the conclusion | Flag clearly; author should resolve before delivery |
| **Minor** | Presentation, style, or nice-to-have improvement | Note; author's discretion |
