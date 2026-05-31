# Hypothesis Testing in Root Cause Investigations

## Structuring a hypothesis

A testable hypothesis has three parts:

1. **Proposed cause** — a specific, falsifiable claim ("The checkout button colour change deployed on Monday reduced mobile conversion")
2. **Predicted effect** — what you would expect to see if the hypothesis is true ("Mobile checkout conversion dropped from ~8% to ~5% starting Monday")
3. **Test** — what data or experiment would confirm or refute it ("Compare mobile checkout conversion rate by day, split pre/post Monday")

Vague hypotheses ("something broke") cannot be tested. Force specificity.

---

## Evidence quality hierarchy

When evaluating evidence for a hypothesis, rank quality:

1. **Controlled experiment (A/B test)** — highest confidence; isolates the cause
2. **Natural experiment** — a deployment or event affected only a subset of users; compare affected vs unaffected
3. **Before/after comparison with no confounders** — strong if no other changes happened simultaneously
4. **Segment analysis** — the pattern is concentrated in segments consistent with the hypothesis
5. **Correlation in time series** — weakest; requires corroborating evidence

---

## Ruling hypotheses out

Ruling a hypothesis out is as important as confirming one. A hypothesis is ruled out when:

- The predicted pattern is absent in the data
- The timing doesn't match (the metric moved before the proposed cause)
- The affected population doesn't match (the change is in desktop users only, but the hypothesis is about a mobile release)

Document ruled-out hypotheses — it prevents the team from re-investigating the same dead ends.

---

## Parallel vs sequential testing

Test multiple hypotheses in parallel when they require independent data pulls. Test sequentially when:

- One hypothesis, if confirmed, would explain everything (no need to test the rest)
- Testing hypothesis B requires knowing the outcome of hypothesis A

---

## Confounding controls

When your investigation is observational, consider whether confounders can explain the pattern:

- **Time confounders:** Is Tuesday always lower? Compare the same day of week across weeks.
- **Cohort confounders:** Are newer users behaving differently? Segment by acquisition cohort.
- **Selection confounders:** Did a different user mix start the funnel this week? Compare the denominator, not just the numerator.

---

## Documenting hypothesis outcomes

For each hypothesis tested, record:

| Field | Content |
|---|---|
| Hypothesis | One sentence description |
| Predicted signal | What data pattern would confirm it |
| Evidence found | What the data actually shows |
| Verdict | Confirmed / Refuted / Inconclusive |
| Refutation reason | (if refuted) Why the data rules it out |
| Confidence | High / Medium / Low |

The final RCA report should include all tested hypotheses, not just the confirmed one.
