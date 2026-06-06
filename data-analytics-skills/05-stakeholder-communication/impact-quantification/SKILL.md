---
name: impact-quantification
description: Estimate and communicate the business impact of analytical findings. Activate after an analysis surfaces an opportunity, risk, or inefficiency that needs a dollar, user, or time value attached before stakeholders can prioritise it.
---

# When to use
- An analysis has surfaced an opportunity and you need to size it for prioritisation
- A stakeholder asks "how much does this actually matter?"
- Building a business case for an initiative based on analytical findings
- Ranking a backlog where quantified impact is the primary signal

# Process
1. **Classify the impact type** — determine whether the impact is revenue growth, cost reduction, risk reduction, or efficiency gain; each requires a different estimation approach
2. **Gather baseline inputs** — collect: current metric values, population size, expected change magnitude, and confidence level
3. **Build the estimate** — use `scripts/revenue_impact.py` for growth scenarios or `scripts/cost_savings.py` for efficiency/cost scenarios; model uncertainty as low/base/high range rather than a single point
4. **Document assumptions** — list every input that is estimated rather than directly measured; run sensitivity analysis to identify which assumptions most influence the output
5. **Validate with stakeholders** — share the assumption list before finalising the estimate; stakeholders often have better inputs for business parameters
6. **Produce deliverables** — fill `assets/impact_estimate_template.md` for opportunity sizing or `assets/business_case_template.md` for larger investment decisions

# Inputs the skill needs
- Required: the finding or opportunity to quantify
- Required: baseline metrics (current performance, population size)
- Required: estimated change magnitude (from the analysis or a comparable benchmark)
- Optional: confidence level and acceptable uncertainty range
- Optional: time horizon for impact realisation

# Output
- `scripts/revenue_impact.py` / `scripts/cost_savings.py` — impact calculation with low/base/high ranges
- `assets/impact_estimate_template.md` (filled) — impact range, assumptions, sensitivity analysis
- `assets/business_case_template.md` (filled) — for larger decisions requiring full business case
