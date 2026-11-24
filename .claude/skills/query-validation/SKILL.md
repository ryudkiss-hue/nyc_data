---
name: query-validation
description: Review SQL queries for correctness, performance, and best practices before they reach production. Activate when promoting queries to dashboards, investigating unexpected results, or when a query is slow and needs optimisation.
---

# When to use
- Promoting a query to a production dashboard or scheduled report
- Results look wrong or unexpected — validating logic before escalating
- A query is slow and needs performance investigation
- Preventing anti-patterns from causing production incidents
- Code review for an analyst's or engineer's SQL

# Process
1. **Syntax & style check** — run `scripts/sql_lint.py` (uses sqlglot) to catch syntax errors, unsupported functions for the target DB, and style violations
2. **Anti-pattern detection** — compare against `references/sql_anti_patterns.md`; rate each finding by severity (blocking / major / minor)
3. **Execution plan analysis** — parse EXPLAIN or query profile output via `scripts/explain_plan_parser.py`; identify full table scans, missing indexes, and sort spills
4. **Cardinality estimation** — run `scripts/cardinality_estimator.py` when schema statistics exist; flag joins with unexpected row multiplication
5. **Engine-specific validation** — cross-reference `references/engine_specific_guide.md` for Snowflake, BigQuery, Postgres, or Redshift-specific behaviour (date functions, window frame defaults, QUALIFY support)
6. **Produce deliverables** — populate `assets/query_review_template.md` with categorised findings; generate `assets/optimization_recommendations.md` for performance issues

# Inputs the skill needs
- Required: SQL text
- Required: target database engine (Snowflake / BigQuery / Postgres / Redshift / other)
- Should provide: table schemas and approximate row counts
- Should provide: EXPLAIN or query profile output if the query has already run
- Optional: business logic the query is meant to implement
- Optional: performance target (e.g. must run under 30 s on prod)

# Output
- `assets/query_review_template.md` (filled) — correctness, performance, style findings categorised by severity
- `assets/optimization_recommendations.md` (filled) — prioritised optimisation suggestions with projected impact
