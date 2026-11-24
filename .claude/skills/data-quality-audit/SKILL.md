---
name: data-quality-audit
description: Comprehensive data quality assessment against business rules, schema constraints, and freshness expectations. Activate when validating production pipelines, onboarding new data sources, or when stakeholders report data quality concerns.
---

# When to use
- A production pipeline needs validation before a business-critical report runs
- Stakeholders report suspicious numbers or missing values
- Onboarding a new data source that needs a baseline quality profile
- A scheduled data quality SLA check is due

# Process
1. **Completeness analysis** — detect nulls across all columns; calculate per-column and overall completeness scores
2. **Duplicate identification** — find exact and near-duplicate rows; distinguish intentional versioning from pipeline errors
3. **Referential integrity validation** — measure orphan rates for foreign key relationships documented in the schema
4. **Range validation** — test numeric and date fields against documented business rules (e.g. age 0–120, dates not in the future)
5. **Freshness assessment** — compare data currency against pipeline SLAs; flag stale tables
6. **Severity classification** — map findings to quality dimensions (completeness, validity, consistency, timeliness) and assign severity (critical / major / minor)

# Inputs the skill needs
- Required: target dataset (path, DataFrame, or DB connection + table name)
- Required: schema documentation identifying key fields and relationships
- Required: business rules defining valid ranges, required fields, and acceptable values
- Optional: error rate thresholds (defaults: >5% nulls on required field = critical; >1% duplicates = major)
- Optional: pipeline schedule and SLA for freshness check

# Output
- HTML audit report with per-dimension scores and finding details
- Markdown quality scorecard summarising dimensional performance
