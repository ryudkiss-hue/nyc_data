---
name: business-metrics-calculator
description: Standard business metric calculation with industry benchmarks. Use when calculating SaaS metrics (MRR, churn, LTV, CAC), e-commerce KPIs, or product analytics metrics with proper definitions.
---

# Business Metrics Calculator

# When to use
- Preparing a board or investor deck and need accurately defined metrics
- The team disagrees on how a key metric (e.g., churn) should be calculated
- Benchmarking performance against industry standards
- Building a metrics report for a new business or new metric set
- Validating that existing metric calculations match the standard definition

# Process
1. **Identify the business model and period** — confirm the model type (SaaS subscription, e-commerce, marketplace, product/app) and the calculation period (month, quarter, trailing 12M). Model type determines which metrics apply. See `references/metric_definitions.md`.
2. **Load and validate the underlying data** — check for expected row counts, missing values, and plausible date ranges. A metrics report is only as good as the data feeding it.
3. **Calculate primary metrics** — for SaaS: MRR, ARR, new MRR, churned MRR, expansion MRR, customer churn rate, revenue churn rate. For e-commerce: GMV, AOV, conversion rate, ROAS. Use `scripts/saas_metrics.py` or adapt for other models.
4. **Calculate unit economics** — LTV (simple average and cohort-based), CAC, LTV:CAC ratio, payback period, and quick ratio. Document which assumptions were used for LTV lifetime.
5. **Compare to benchmarks** — grade each metric against the industry benchmark thresholds in `references/metric_definitions.md` (good / average / poor). Flag anything outside the acceptable range.
6. **Produce the metrics report** — assemble results into `assets/metrics_report_template.md` with trend charts, benchmark comparison, and 3–5 key insights. Document any definition choices that differ from industry standard.

# Inputs the skill needs
- Subscription or transaction data with at minimum: customer ID, date, value, status
- Marketing spend data (for CAC calculation)
- Monthly targets or goals (for vs-target comparisons)
- The agreed-upon metric definitions (or default to industry standard)
- Time period and any segmentation required (by plan, region, cohort)

# Output
- `scripts/saas_metrics.py` — calculates standard SaaS metrics from a subscriptions CSV; includes MRR waterfall, churn, LTV/CAC
- `references/metric_definitions.md` — canonical definitions and benchmark thresholds by model type
- `assets/metrics_report_template.md` — structured report: revenue metrics, customer metrics, unit economics, benchmark comparison, insights
