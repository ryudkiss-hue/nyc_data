---
name: query-validation
description: SQL query review for correctness, performance, and best practices. Activate when a query needs review before production use, shows unexpected results, or runs too slowly.
---

# When to use
- A SQL query is about to be promoted to a production dashboard or report
- A query is returning surprising or incorrect results
- A query is running slowly and needs performance review
- You want to catch anti-patterns (implicit conversions, SELECT *, unbounded CTEs) before they cause incidents

# Process
1. **Lint the query** — run `scripts/sql_lint.py` (sqlglot-based) to catch syntax errors, unsupported functions for the target engine, and style violations. Fix hard errors before continuing.
2. **Review anti-patterns** — compare the query structure against `references/sql_anti_patterns.md`. Flag any present anti-patterns with a severity rating.
3. **Parse the explain plan** — if an EXPLAIN or query profile output is available, run `scripts/explain_plan_parser.py` to extract slow steps (full table scans, missing indexes, high row estimates).
4. **Estimate cardinality** — run `scripts/cardinality_estimator.py` if schema stats are available to flag joins that might fan-out unexpectedly.
5. **Check engine-specific behaviour** — consult `references/engine_specific_guide.md` for the target engine (Snowflake / BigQuery / Postgres / Redshift) to verify date functions, window behaviour, and clustering assumptions.
6. **Produce review output** — fill in `assets/query_review_template.md` with findings; for any performance issues found, complete `assets/optimization_recommendations.md`.

# Inputs the skill needs
- Required: the SQL query text
- Required: target database engine (Snowflake / BigQuery / Postgres / Redshift / other)
- Optional: relevant table schemas (column names, types, approximate row counts)
- Optional: EXPLAIN / query profile output
- Optional: expected business logic — what should the query calculate?

# Output
- `assets/query_review_template.md` (filled) — categorised findings: correctness, performance, style
- `assets/optimization_recommendations.md` (filled, if issues found) — ranked rewrite suggestions with expected impact
