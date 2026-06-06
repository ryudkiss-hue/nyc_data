---
name: cohort-analysis
description: Time-based cohort analysis with retention and behaviour tracking. Activate when you need to measure how groups of users/customers behave over time — retention rates, revenue by cohort, or feature adoption curves.
---

# When to use
- Stakeholder asks "are new users sticking around longer than users from six months ago?"
- Investigating when in the user lifecycle churn typically occurs
- Measuring the impact of a product change on long-term retention
- Comparing retention across acquisition channels, plans, or segments
- Tracking feature adoption across different signup cohorts

# Process
1. **Define cohort parameters** — specify cohort definition (e.g. signup month), observation window (e.g. 12 months), and retention metric (e.g. any login, paid transaction)
2. **Extract and validate event data** — pull user activity data; validate completeness and check for data gaps that would distort retention curves
3. **Build cohort membership table** — assign each user to exactly one cohort based on their first qualifying event
4. **Calculate retention metrics** — for each cohort × period cell, compute retained users, retention rate, and confidence interval using `scripts/cohort_builder.py`
5. **Visualise results** — generate retention heatmap and line charts using `scripts/cohort_visualizer.py`; reference `references/cohort_interpretation_guide.md` for pattern identification
6. **Interpret patterns** — identify improving or declining cohorts, cliff drops at specific periods, and seasonality effects; use `references/retention_metrics_glossary.md` for definitions
7. **Document findings** — fill `assets/cohort_report_template.md` with retention figures, trend narrative, and recommendations

# Inputs the skill needs
- Required: event data with user ID, cohort assignment date (e.g. signup date), and activity dates
- Required: cohort granularity (daily / weekly / monthly)
- Required: retention definition — what counts as "active" or "retained"?
- Optional: segmentation dimension (channel, plan, geography)
- Optional: benchmark retention rates to compare against

# Output
- `assets/cohort_report_template.md` (filled) — full narrative with retention figures and trend interpretation
- Interactive HTML heatmap — colour-coded cohort × period retention matrix
- Retention rate CSV for downstream analysis
