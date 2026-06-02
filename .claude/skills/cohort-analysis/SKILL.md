---
name: cohort-analysis
description: Time-based cohort analysis with retention and behaviour tracking. Activate when you need to measure how groups of users/customers behave over time — retention rates, revenue by cohort, or feature adoption curves.
---

# When to use
- A stakeholder asks "are we retaining users better than last quarter?"
- You need to measure N-day, weekly, or monthly retention for a product or feature
- You want to compare how different acquisition cohorts (by channel, plan, or signup date) perform over their lifetime
- You're investigating churn and need to identify at which period users typically leave

# Process
1. **Define the cohort and activity** — clarify: cohort grouping (signup month, first purchase date, etc.) and retention event (login, purchase, feature use). Document in the report header.
2. **Pull or build the data** — if starting from a database, use `scripts/cohort_query.sql` as the starting point. Adapt the `cohort_date` and `activity_date` columns to your schema.
3. **Build the cohort table** — run `scripts/cohort_builder.py` to produce a cohort × period membership table from event data. Output is a CSV with `user_id`, `cohort_period`, `activity_period`.
4. **Compute the retention matrix** — run `scripts/retention_matrix.py` on the cohort table to generate the period-over-period retention rates. Output is an N×M matrix (cohort × period).
5. **Visualise** — run `scripts/cohort_visualizer.py` to render a heatmap of the retention matrix and a time-series of retention curves per cohort.
6. **Interpret findings** — consult `references/retention_metrics_glossary.md` for metric definitions and `references/cohort_definition_patterns.md` for pattern recognition.
7. **Write the report** — fill `assets/cohort_report_template.md`. For a visual deliverable, fill in the `assets/retention_matrix.html` heatmap template.

# Inputs the skill needs
- Required: event data with `user_id`, `cohort_date` (e.g. `signup_date`), `activity_date`
- Required: cohort grouping granularity (daily / weekly / monthly)
- Required: retention event definition — what counts as "active" or "retained"?
- Optional: minimum cohort size (recommend ≥ 100 users; smaller cohorts have noisy rates)
- Optional: number of periods to track (e.g. 12 months)
- Optional: cohort attributes to segment by (acquisition channel, plan tier, geography)

# Output
- `assets/cohort_report_template.md` (filled) — narrative interpretation and retention figures
- `assets/retention_matrix.html` (filled) — colour-coded retention heatmap
- `scripts/retention_matrix.py` output CSV — raw retention rates for downstream use
