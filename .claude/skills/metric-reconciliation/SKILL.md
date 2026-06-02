---
name: metric-reconciliation
description: Trace and resolve discrepancies when the same metric shows different values in two or more sources. Use before reporting, after pipeline changes, or when stakeholders question a number.
---

# Metric Reconciliation

# When to use
- Two dashboards or reports show different values for the same KPI
- A metric changed unexpectedly after a data pipeline update
- Stakeholders question a number and need an authoritative explanation
- Preparing to merge or deprecate a legacy reporting source
- Onboarding analysts to a new data model and validating it against the old one

# Process
1. **Define the metric and scope** — confirm the exact definition (numerator, denominator, filters, time zone) and the period under investigation. Mismatched definitions are the most common cause of discrepancy.
2. **Pull values from both sources** — extract the metric values for the same period from each source. Record absolute values, row counts, and the query or calculation path used.
3. **Compute the gap** — calculate the absolute difference and percentage gap. If the gap is within an agreed tolerance (e.g., ±0.1%), document it as accepted and close. See `references/reconciliation_patterns.md` for tolerance guidelines.
4. **Trace the computation path** — walk each source's query or pipeline step by step. Common divergence points: different join types, filter order, null handling, date truncation, or deduplication logic.
5. **Identify the root cause** — classify the cause using `references/metric_discrepancy_guide.md` (definition mismatch, data freshness, aggregation grain, calculation bug). Document the divergence point with a code snippet or query excerpt.
6. **Resolve and document** — fix the calculation or accept a canonical source, then complete `assets/reconciliation_report_template.md` and share with stakeholders.

# Inputs the skill needs
- The metric name and business definition (numerator, denominator, any known variants)
- Access to both sources (queries, dashboard SQL, or raw data)
- The time period showing the discrepancy
- Row counts or record-level data to enable line-by-line comparison if needed
- Any known recent changes to pipelines, schema, or business rules

# Output
- `assets/reconciliation_report_template.md` — completed report showing source A vs. source B, the gap, root cause, and resolution status
- A corrected query or pipeline change (if a bug was found)
- A documented tolerance agreement (if the gap is acceptable)
