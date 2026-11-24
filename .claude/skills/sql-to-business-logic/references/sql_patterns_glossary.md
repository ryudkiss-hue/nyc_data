# SQL Patterns Glossary

Maps SQL constructs to plain-English business meaning. Intended for analysts documenting
queries, onboarding new team members, or explaining logic to non-technical stakeholders.
All examples use NYC DOT SOQL (Socrata Query Language) where applicable.

---

## GROUP BY

**What it does:** Collapses many rows into one summary row per unique combination of
the grouped columns. Any column not in GROUP BY must be wrapped in an aggregate function.

**Plain-English meaning:** "Give me one total/count/average per [category]."

**NYC DOT example:**

```sql
-- SOQL: violations per borough
SELECT borough, COUNT(*) AS total_violations
FROM violations
GROUP BY borough
```

Business meaning: "How many open violations does each borough have? Show one row
per borough."

**Common pitfalls:**
- Forgetting to GROUP BY all non-aggregated columns produces wrong results.
- GROUP BY a high-cardinality column (e.g., `objectid`) produces one row per record —
  effectively no aggregation.

---

## COUNT / COUNT DISTINCT

**What it does:**
- `COUNT(*)` — counts all rows, including nulls.
- `COUNT(column)` — counts non-null values in that column.
- `COUNT(DISTINCT column)` — counts unique non-null values.

**Plain-English meaning:**
- `COUNT(*)` → "How many records are there?"
- `COUNT(DISTINCT unit_id)` → "How many unique sidewalk segments were inspected?"

**NYC DOT example:**

```sql
-- SOQL: unique units inspected in May 2026
SELECT COUNT(DISTINCT unit_id) AS unique_units_inspected
FROM inspection
WHERE inspection_date >= '2026-05-01T00:00:00'
  AND inspection_date <  '2026-06-01T00:00:00'
```

Business meaning: "Count each sidewalk segment only once, even if it was inspected
multiple times in May."

---

## CASE WHEN

**What it does:** Applies conditional logic row-by-row — like an if/else statement
applied to every row in a result set.

**Plain-English meaning:** "Label each record based on rules. If [condition], call it
[label A]; otherwise call it [label B]."

**NYC DOT example:**

```sql
-- SOQL: classify inspection severity
SELECT objectid,
       defect_type,
       CASE
         WHEN defect_type IN ('CRACK_SEVERE', 'BROKEN', 'UPLIFT') THEN 'HIGH'
         WHEN defect_type IN ('CRACK_MINOR', 'WORN')              THEN 'MEDIUM'
         ELSE                                                           'LOW'
       END AS severity_tier
FROM inspection
```

Business meaning: "Tag each inspection record with a priority tier based on the
defect type. High-priority defects need urgent follow-up."

**Aggregate CASE pattern** (used to pivot data):

```sql
SELECT borough,
       COUNT(CASE WHEN status = 'OPEN'   THEN 1 END) AS open_count,
       COUNT(CASE WHEN status = 'CLOSED' THEN 1 END) AS closed_count
FROM violations
GROUP BY borough
```

Business meaning: "For each borough, show the number of open violations and the
number of closed violations side by side."

---

## WHERE vs HAVING

| Clause | Applied | Filters |
|--------|---------|---------|
| `WHERE` | Before aggregation | Individual rows |
| `HAVING` | After aggregation | Aggregated groups |

**Plain-English meaning:**
- `WHERE` → "Only look at records that match this condition."
- `HAVING` → "After summarising, only show groups that meet this threshold."

**NYC DOT example:**

```sql
-- SOQL (DuckDB equivalent): boroughs with more than 1,000 open violations
SELECT borough, COUNT(*) AS open_violations
FROM violations
WHERE status = 'OPEN'
GROUP BY borough
HAVING COUNT(*) > 1000
ORDER BY open_violations DESC
```

Business meaning: "Filter to open violations only (WHERE), then count per borough,
then only show boroughs with a large backlog (HAVING)."

---

## Window Functions (OVER / PARTITION BY)

**What it does:** Computes a value for each row using a group of related rows (the
"window"), without collapsing them into one summary row. The original row count is
preserved.

**Plain-English meaning:** "For each record, calculate [something] based on all
records in the same [group]."

**Common window functions:**

| Function | Business meaning |
|----------|-----------------|
| `ROW_NUMBER()` | "Rank records 1, 2, 3 … within each group" |
| `RANK()` | "Rank with ties (1, 1, 3 …)" |
| `SUM() OVER (...)` | "Running total within a group" |
| `LAG(col, 1)` | "Previous row's value (period-over-period change)" |
| `LEAD(col, 1)` | "Next row's value (look-ahead)" |
| `AVG() OVER (...)` | "Rolling average within a partition" |

**NYC DOT example — rolling 7-day inspection count:**

```sql
SELECT inspection_date,
       borough,
       daily_count,
       AVG(daily_count) OVER (
         PARTITION BY borough
         ORDER BY inspection_date
         ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ) AS rolling_7d_avg
FROM daily_inspection_summary
```

Business meaning: "For each day and borough, show the 7-day rolling average of
daily inspection counts. This smooths out day-of-week variation."

**NYC DOT example — most recent inspection per unit:**

```sql
SELECT *
FROM (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY unit_id
           ORDER BY inspection_date DESC
         ) AS rn
  FROM inspection
) sub
WHERE rn = 1
```

Business meaning: "Keep only the most recent inspection record for each sidewalk
segment."

---

## CTEs (Common Table Expressions) — WITH Clause

**What it does:** Names an intermediate query result so it can be referenced like a
table later in the same query. Multiple CTEs can chain together.

**Plain-English meaning:** "First, calculate [X]. Then, use that result to
calculate [Y]. Then, use both to calculate [Z]."

**NYC DOT example:**

```sql
WITH open_violations AS (
  SELECT borough, unit_id, COUNT(*) AS open_count
  FROM violations
  WHERE status = 'OPEN'
  GROUP BY borough, unit_id
),
high_severity AS (
  SELECT unit_id
  FROM inspection
  WHERE defect_type IN ('CRACK_SEVERE', 'BROKEN', 'UPLIFT')
)
SELECT ov.borough,
       ov.unit_id,
       ov.open_count
FROM open_violations ov
JOIN high_severity hs ON ov.unit_id = hs.unit_id
ORDER BY ov.open_count DESC
```

Business meaning: "Step 1: count open violations per segment. Step 2: find segments
with severe defects. Step 3: show only high-severity segments that also have open
violations — these are the highest-risk locations."

---

## JOIN Types

| Join Type | What it returns | Use when |
|-----------|----------------|----------|
| `INNER JOIN` | Only rows that match in both tables | You need complete data from both sides |
| `LEFT JOIN` | All rows from left; nulls for non-matching right | You need all records from the main table, even if no match exists |
| `RIGHT JOIN` | All rows from right; nulls for non-matching left | Rare; usually rewrite as LEFT JOIN |
| `FULL OUTER JOIN` | All rows from both; nulls on either side | Reconciliation queries |

**NYC DOT example:**

```sql
-- LEFT JOIN: all inspections, including those with no open violation on file
SELECT i.unit_id, i.inspection_date, v.open_count
FROM inspection i
LEFT JOIN (
  SELECT unit_id, COUNT(*) AS open_count
  FROM violations WHERE status = 'OPEN'
  GROUP BY unit_id
) v ON i.unit_id = v.unit_id
```

Business meaning: "Show every inspected segment. If a segment has open violations,
show how many. If it has none, show 0 (not null — remember to COALESCE)."

---

## Subqueries

**What it does:** A query nested inside another query. Can appear in SELECT, FROM,
or WHERE clauses.

**Plain-English meaning:** "Calculate [intermediate result], then use it to
answer the main question."

**NYC DOT example (correlated subquery in WHERE):**

```sql
SELECT unit_id, borough, defect_type
FROM inspection i
WHERE inspection_date = (
  SELECT MAX(inspection_date)
  FROM inspection
  WHERE unit_id = i.unit_id
)
```

Business meaning: "For each sidewalk segment, show only the most recent inspection
record." (Same logic as the ROW_NUMBER window function example above — CTEs or
window functions are usually more readable and faster.)

---

## COALESCE / NULLIF

| Function | What it does | Business meaning |
|----------|-------------|-----------------|
| `COALESCE(a, b, c)` | Returns first non-null value | "Use this value; if missing, fall back to that" |
| `NULLIF(a, b)` | Returns NULL if a equals b | "Treat this special value as missing data" |

**NYC DOT examples:**

```sql
-- Replace NULL borough with 'UNKNOWN'
COALESCE(borough, 'UNKNOWN')

-- Avoid division by zero in closure rate calculation
closed_count * 1.0 / NULLIF(total_count, 0) AS closure_rate
```

---

## SOQL-Specific Patterns (Socrata Query Language)

SOQL is a subset of SQL. Key differences from standard SQL:

| Feature | SOQL | Standard SQL |
|---------|------|-------------|
| Date literals | ISO 8601 strings: `'2026-05-01T00:00:00'` | Varies by engine |
| Limit rows | `$limit=1000` as URL parameter | `LIMIT 1000` in query |
| Filter | `$where=` parameter | `WHERE` clause |
| Select columns | `$select=` parameter | `SELECT` clause |
| Group by | `$group=` parameter | `GROUP BY` clause |
| Order | `$order=` parameter | `ORDER BY` clause |
| Text search | `$q=` full-text search | No direct equivalent |

**NYC DOT SOQL example (violations in BK, last 30 days):**

```
https://data.cityofnewyork.us/resource/6kbp-uz6m.json
  ?$where=upper(borough)='BK' AND created_date > '2026-05-15T00:00:00'
  &$select=objectid,borough,status,defect_type,created_date
  &$order=created_date DESC
  &$limit=5000
```

Business meaning: "Fetch open violations created in Brooklyn after May 15, 2026.
Return only the columns we need, newest first, capped at 5,000 rows."

---

## ORDER BY

**What it does:** Sorts the result set by one or more columns. `ASC` = smallest first
(default), `DESC` = largest first.

**Plain-English meaning:** "Sort the results so the [most important / largest /
newest] records appear first."

**NYC DOT example:**

```sql
SELECT borough, COUNT(*) AS violations
FROM violations
WHERE status = 'OPEN'
GROUP BY borough
ORDER BY violations DESC
```

Business meaning: "Show the borough with the largest open violation backlog at the top."

---

## LIMIT / TOP

**What it does:** Restricts the number of rows returned.

**Plain-English meaning:** "Only show me the top N results."

**When to use it in DOT analysis:**
- Sanity-checking a new dataset (`LIMIT 10` to see the structure).
- Preventing accidental full-corpus fetches of 21M-row datasets.
- Returning only the top contributors to a metric.

**Rule of thumb:** Always use `$limit` in SOQL requests unless you have an explicit
reason to fetch the full dataset, and confirm `SOCRATA_APP_TOKEN` is set for >2,000 rows.
