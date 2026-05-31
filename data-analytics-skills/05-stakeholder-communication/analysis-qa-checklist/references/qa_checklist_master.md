# Analysis QA Checklist Master

Complete this checklist before every stakeholder delivery. Check each item explicitly — do not mark a section "done" without reviewing every item.

---

## 1. Question Framing

- [ ] The analysis answers the question that was actually asked (not a related but different question)
- [ ] Scope boundaries are respected (the analysis doesn't silently include out-of-scope data)
- [ ] The time period matches the brief
- [ ] The definition of key terms (e.g. "active user", "revenue") matches the stakeholder's definition

---

## 2. Data Sourcing

- [ ] All data sources are identified and appropriate for the question
- [ ] Data freshness is confirmed (no stale snapshots used by mistake)
- [ ] Data lineage is understood — know where each table comes from
- [ ] Access permissions were appropriate (no use of data you shouldn't have)
- [ ] Any known data quality issues in the source are documented and their effect considered

---

## 3. Transformations and Calculations

- [ ] All joins are the correct type (INNER vs LEFT vs FULL) and produce the expected row count
- [ ] Aggregation grain is correct — no accidental row duplication or double-counting
- [ ] Null handling is explicit and intentional (nulls excluded / included / imputed as intended)
- [ ] Date/timezone handling is consistent throughout
- [ ] Divisions checked for divide-by-zero
- [ ] Percentage calculations use the correct denominator
- [ ] Intermediate results spot-checked against source data for at least 3 rows

---

## 4. Statistical Validity

- [ ] Sample size is sufficient for the claim being made
- [ ] Statistical tests are appropriate for the data type and distribution
- [ ] Confidence intervals or uncertainty ranges are included where applicable
- [ ] Multiple testing correction applied if multiple hypotheses tested
- [ ] Correlation is not misrepresented as causation
- [ ] Outliers are identified and their impact on conclusions assessed

---

## 5. Findings and Conclusions

- [ ] Each conclusion is directly supported by the data shown
- [ ] No conclusions go beyond what the data can support
- [ ] Unexpected findings are flagged rather than suppressed
- [ ] Limitations and caveats are stated clearly
- [ ] The "so what" is explicit — the recommendation follows from the finding

---

## 6. Presentation and Communication

- [ ] Visualisations have accurate axes, labels, and titles
- [ ] Chart types match the data story (avoid pie charts for >5 categories, etc.)
- [ ] Numbers are formatted consistently (same decimal places, same currency)
- [ ] Technical jargon has been replaced with business language for the target audience
- [ ] The document is free of typos, broken formatting, and placeholder text

---

## Sign-off

Complete `assets/qa_signoff_template.md` after finishing this checklist.

**Pass criteria:** All items in sections 1–5 checked; section 6 checked for audience-facing docs; no unresolved FAIL items from `scripts/qa_runner.py`.
