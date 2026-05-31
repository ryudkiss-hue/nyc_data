---
name: impact-quantification
description: Estimate and communicate business impact of insights. Use when sizing opportunities discovered in analysis, calculating ROI of recommended actions, or prioritizing initiatives by potential impact.
---

# When to use

After an analytical finding surfaces a potential action, change, or opportunity. Use to produce a defensible numeric estimate that stakeholders can act on. Also use when prioritizing a backlog of initiatives — quantified impact is the primary ranking signal.

# Process

1. **Classify the impact type** — revenue growth, cost reduction, risk reduction, or efficiency gain. Each type has a different formula family (see `references/impact_quantification_framework.md`).
2. **Gather inputs** — collect baseline metrics, affected population size, expected lift/reduction, time horizon, and confidence level.
3. **Build the point estimate** — use `scripts/revenue_impact.py` for revenue/growth scenarios or `scripts/cost_savings.py` for cost/efficiency scenarios.
4. **Add uncertainty bounds** — use `scripts/confidence_interval.py` to produce low/base/high estimates. Never deliver a single number without a range.
5. **Document assumptions** — fill in `references/assumption_documentation.md` for every input that is estimated rather than directly measured; note the sensitivity of the output to each.
6. **Package the estimate** — complete `assets/impact_estimate_template.md` with the range, assumptions, confidence, and recommended action; optionally build the full `assets/business_case_template.md` for larger decisions.

# Inputs the skill needs

- Baseline metric value (current state)
- Affected population or volume
- Expected change (lift %, absolute, or rate change)
- Time horizon (monthly / annual)
- Confidence level in inputs (high / medium / low)

# Output

- Impact estimate with low/base/high range
- Assumption log (source and sensitivity for each input)
- Completed `impact_estimate_template.md` or `business_case_template.md`
