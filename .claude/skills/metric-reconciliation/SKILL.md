---
name: metric-reconciliation
description: Investigate and resolve metric discrepancies across data sources, systems, or time periods. Activate when metrics from different sources don't match, after a data migration, or when a dashboard figure doesn't match a report.
---

# When to use
- Two systems report different revenue, user counts, or other KPIs for the same period
- A dashboard metric doesn't match the figure in an emailed report
- Validating data accuracy after a pipeline or system migration
- Month-end close requires reconciliation between finance and analytics systems
- A stakeholder challenges a reported number and you need to trace the discrepancy

# Process
1. **Load data from each source** — connect to or import all relevant datasets (DB queries, CSVs, API exports)
2. **Standardise formats** — align date formats, numeric types, null handling, and categorical labels across sources
3. **Aggregate at comparison level** — roll up to the grain where comparison makes sense (e.g. daily totals, monthly cohort)
4. **Join and diff** — merge sources on the comparison key; calculate absolute difference, percentage difference, and direction
5. **Categorise discrepancies** — classify gaps by severity (within tolerance / investigate / critical) using defined thresholds
6. **Investigate root causes** — analyse patterns: timing lags, filter differences, definition mismatches, currency/unit issues, deduplication logic
7. **Drill down** — isolate specific dates, transaction IDs, or segments where discrepancies are largest
8. **Report findings** — document root cause, magnitude, and remediation steps

# Inputs the skill needs
- Required: two or more data sources or exports to compare
- Required: the metric(s) to reconcile and how each source defines them
- Required: acceptable variance threshold (e.g. ±0.5%)
- Required: time period and comparison granularity (daily, weekly, monthly)
- Required: the join key that links records across sources (date, transaction ID, customer ID)

# Output
- Reconciliation report documenting sources, methodology, discrepancy magnitude, root cause, and remediation
- Discrepancy detail file — row-level diffs for the records that don't match
