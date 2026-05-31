# Query Review: [Query Name / Purpose]

**Reviewer:** [Name]  
**Date:** [YYYY-MM-DD]  
**Engine:** [Snowflake / BigQuery / Postgres / Redshift]  
**Query location:** [path, dashboard link, or paste below]

---

## Query (or reference)

```sql
-- paste query here or reference file path
```

---

## Correctness

| # | Finding | Severity | Location | Recommendation |
|---|---|---|---|---|
| 1 | | HIGH / MED / LOW | [line or CTE name] | |

**Overall correctness verdict:** PASS / FAIL / NEEDS INVESTIGATION

Notes:
- [e.g. Business logic matches the spec for MRR — verified against definition doc.]
- [e.g. NULL handling in the CASE expression on line 14 may produce incorrect totals — recommend COALESCE.]

---

## Performance

| # | Finding | Severity | Estimated impact | Recommendation |
|---|---|---|---|---|
| 1 | | HIGH / MED / LOW | | |

**EXPLAIN / profile reviewed?** Yes / No  
**Estimated scan size:** [rows / GB if known]

Notes:
- [e.g. Full table scan on `events` (180M rows) — add WHERE clause to filter by partition column.]

---

## Style & Maintainability

| # | Finding | Severity | Recommendation |
|---|---|---|---|
| 1 | SELECT * on line 3 | LOW | Enumerate columns |

---

## Anti-Patterns Found

*(Cross-reference `references/sql_anti_patterns.md`)*

- [ ] Implicit type conversion
- [ ] NULL comparison error
- [ ] Fan-out join
- [ ] NOT IN with nullable subquery
- [ ] Function on indexed column in WHERE
- [ ] Correlated subquery in SELECT
- [ ] DISTINCT masking a join problem
- [x] ~~None found~~

---

## Summary

**Approved for production?** Yes / No / Yes with conditions

Conditions (if any):
1. [Fix before deploying]
2. [Monitor after deploying]

**Estimated performance after fixes:** [e.g. ~5 s → ~0.3 s based on removing full table scan]
