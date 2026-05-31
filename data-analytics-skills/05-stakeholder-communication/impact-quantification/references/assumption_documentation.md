# Assumption Documentation Guide

Every impact estimate rests on assumptions. This guide explains how to document them so that reviewers can assess risk and stakeholders understand confidence.

---

## Why Document Assumptions

- Enables others to reproduce and update the estimate when conditions change
- Forces the analyst to be explicit about what is known vs. guessed
- Provides a clear audit trail if the estimate is later shown to be wrong
- Allows sensitivity analysis: which assumption matters most?

---

## Assumption Log Template

For each assumption in an impact estimate:

| Field | What to record |
|---|---|
| **Name** | Short label (e.g. "baseline conversion rate") |
| **Value used** | The number plugged into the formula |
| **Source** | Where this value came from (see source types below) |
| **Confidence** | High / Medium / Low |
| **Sensitivity** | What is the impact on the final estimate if this value is 50% off? |
| **Notes** | Any context that affects interpretation |

---

## Source Types (in order of reliability)

| Source type | Description | Example |
|---|---|---|
| **Measured — current** | Pulled directly from production data | Conversion rate from last 90 days in the DW |
| **Measured — experiment** | From a controlled A/B test | Lift from a holdout test run last quarter |
| **Measured — analogous** | From a similar prior change in the same system | Lift from a similar feature launched 18 months ago |
| **Industry benchmark** | Published external data for comparable businesses | SaaS churn benchmark from annual report |
| **Expert estimate** | Informed judgment from a domain expert | Product manager's estimate of take rate |
| **Analyst estimate** | Best-effort estimate from the analyst | Assumed cost-per-error from process knowledge |

---

## Sensitivity Analysis

For each high-sensitivity assumption, test two scenarios:

| Scenario | Description |
|---|---|
| **Bear case** | The assumption is 50% worse than the base |
| **Bull case** | The assumption is 50% better than the base |

Report as: "If [assumption] is half as good as expected, the impact falls from $X to $Y."

Prioritise documenting sensitivity for:
1. The single largest input (usually volume or rate)
2. Any input sourced from expert estimate or analyst estimate
3. Any input with no direct historical parallel

---

## Red Flags in Assumption Logs

- Every input is sourced from "analyst estimate" → escalate confidence to Low; get measured data
- No sensitivity analysis on a $1M+ estimate → must add before delivery
- Lift assumption is higher than any analogous historical lift → add a note explaining why
- Time horizon > 2 years with no discount rate → apply a discount rate for LTV calculations
