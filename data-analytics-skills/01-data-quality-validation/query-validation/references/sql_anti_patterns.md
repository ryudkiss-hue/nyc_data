# SQL Anti-Patterns Reference — NYC DOT Socrata & DuckDB

Patterns that cause correctness bugs, silent result errors, or severe performance
degradation on NYC DOT datasets. Checked automatically by `sql_lint.py`.

---

## Critical — Blocking (must fix before production)

### 1. Relative date functions in SOQL
**Pattern:** `NOW()`, `CURRENT_DATE`, `TODAY()`, `GETDATE()`, `INTERVAL '7 days'`
**Problem:** Socrata SOQL does not support relative date expressions. The query will
either error or silently return 0 rows.
**Fix:** Always use ISO 8601 absolute timestamps:
```sql
-- Wrong (SOQL)
WHERE created_date > NOW() - INTERVAL '30 days'

-- Correct (SOQL)
WHERE created_date > '2026-05-15T00:00:00'
```

### 2. Implicit CROSS JOIN
**Pattern:** `FROM table_a, table_b WHERE ...` (comma-separated tables)
**Problem:** If the WHERE join predicate is missing or incorrect, produces a Cartesian
product. On violations (~312K rows) × inspection (~398K rows) = 124 billion rows.
**Fix:** Always use explicit JOIN syntax with ON clause.

### 3. NOT IN with nullable subquery
**Pattern:** `WHERE id NOT IN (SELECT id FROM ...)`
**Problem:** If the subquery returns any NULL, `NOT IN` returns no rows — a silent,
total data loss bug.
**Fix:** Use `NOT EXISTS` instead:
```sql
-- Wrong
WHERE objectid NOT IN (SELECT objectid FROM dismissals)

-- Correct
WHERE NOT EXISTS (SELECT 1 FROM dismissals d WHERE d.objectid = v.objectid)
```

---

## Major — Fix Before Merging

### 4. SELECT * on wide Socrata datasets
**Pattern:** `SELECT *`
**Problem:** Fetches all columns. The `mappluto` dataset has > 80 columns; `inspection`
has > 40. This multiplies API response size and pandas memory usage unnecessarily.
**Fix:** Project only needed columns using `$select` (SOQL) or explicit column list (SQL):
```sql
SELECT objectid, borough, status, inspection_date FROM dntt-gqwq
```

### 5. No row limit on large datasets
**Pattern:** Query against `violations`, `inspection`, `complaints_311`, or
`street_construction_inspections` without `$limit` or `LIMIT`
**Problem:** These datasets have 312K–21M rows. A full fetch without a token will be
rate-limited; with a token, it stresses memory and slows the pipeline.
**Fix:** Always add `$limit=N` (SOQL) or `LIMIT N` (DuckDB) unless doing a full-corpus
fetch with explicit user confirmation.

### 6. Date string comparison without cast
**Pattern:** `WHERE inspection_date > '2026-01-01'` when column is stored as varchar
**Problem:** Socrata stores many dates as strings. String comparison `>` on
`'2026-01-01'` vs. `'2025-12-15'` works alphabetically but fails with formats like
`12/15/2025`.
**Fix:** Use `date_trunc` or explicit ISO format + confirm column dtype:
```sql
-- SOQL — Socrata handles ISO 8601 date strings correctly
WHERE inspection_date >= '2026-01-01T00:00:00'
```

### 7. GROUP BY without aggregate on selected columns
**Pattern:** `SELECT borough, status, COUNT(*) GROUP BY borough`
**Problem:** `status` is selected but not in GROUP BY. Returns an error or arbitrary row
in some engines; undefined behavior.
**Fix:** Include all non-aggregated columns in GROUP BY.

---

## Minor — Address in Backlog

### 8. Borough comparison without UPPER()
**Pattern:** `WHERE borough = 'Manhattan'`
**Problem:** Socrata data has inconsistent casing (MANHATTAN, Manhattan, manhattan).
**Fix:** `WHERE upper(borough) = 'MANHATTAN'` or normalize on ingest.

### 9. OR conditions in WHERE clause
**Pattern:** `WHERE status = 'OPEN' OR status = 'PENDING'`
**Problem:** Can prevent the query optimizer from using indexes effectively.
**Fix:** Use `IN` for better readability and potential optimization:
```sql
WHERE status IN ('OPEN', 'PENDING')
```

### 10. COUNT(DISTINCT col) on non-key columns
**Pattern:** `COUNT(DISTINCT street_name)` on a 300K-row table
**Problem:** Can be slow; confirm this is the intended cardinality estimate and not a
mistaken substitute for `COUNT(*)`.

---

## Engine-Specific Notes

### DuckDB (L2 cache queries)
- Use `DATE_TRUNC('month', inspection_date::DATE)` for monthly rollups
- `STRFTIME('%Y-%m', inspection_date::DATE)` works for string output
- Parquet files support column pruning — always specify column list in SELECT
- Window functions are fully supported including `QUALIFY`

### Socrata SOQL
- Function reference: https://dev.socrata.com/docs/functions/
- `$where`, `$select`, `$group`, `$order`, `$limit`, `$offset` are the main clauses
- No subqueries in SOQL — use application-side filtering instead
- Date literals must be ISO 8601: `'2026-01-01T00:00:00'`
- `count(*)` → `$select=count(*) as total`
