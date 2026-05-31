# SQL Pattern Library — Business Logic Translations

## Aggregation patterns

| SQL pattern | Business meaning |
|---|---|
| `COUNT(*)` | Total row count (includes duplicates and NULLs) |
| `COUNT(DISTINCT id)` | Unique entities |
| `SUM(amount)` | Total value |
| `AVG(value)` | Mean — sensitive to outliers; check with PERCENTILE_CONT if skewed |
| `MAX(date)` | Most recent event |
| `MIN(date)` | First event |
| `SUM(CASE WHEN x THEN 1 ELSE 0 END)` | Conditional count — count of rows meeting a criterion |
| `SUM(amount) / NULLIF(COUNT(*), 0)` | Safe average avoiding division by zero |

---

## Date/time patterns

| SQL pattern | Business meaning |
|---|---|
| `DATE_TRUNC('month', ts)` | Collapse to first of month — used for period grouping |
| `DATE_TRUNC('week', ts)` | Week starting Monday (in most SQL dialects) |
| `ts >= '2024-01-01' AND ts < '2025-01-01'` | Inclusive start, exclusive end — the correct way to bound a year |
| `DATEDIFF(day, created_at, cancelled_at)` | Duration in days between two events |
| `ts BETWEEN '2024-01-01' AND '2024-12-31'` | Both bounds inclusive — be careful with TIMESTAMP columns |
| `EXTRACT(DOW FROM ts) IN (0, 6)` | Weekend filter (0=Sunday, 6=Saturday in most dialects) |

---

## Filter patterns

| SQL pattern | Business meaning |
|---|---|
| `status = 'completed'` | Point-in-time status filter — check if status can change retroactively |
| `deleted_at IS NULL` | Soft delete filter — excludes logically deleted records |
| `amount > 0` | Exclude zero-value records (check: are negatives refunds?) |
| `id IN (SELECT id FROM table2)` | Restrict to records that exist in another set |
| `NOT EXISTS (SELECT 1 FROM table2 WHERE ...)` | Exclude records that have a related row in another table |
| `COALESCE(col, 0)` | Replace NULL with zero — verify NULL means "zero", not "unknown" |

---

## Window function patterns

| SQL pattern | Business meaning |
|---|---|
| `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at)` | Assign sequence number per customer — use = 1 to get first order |
| `LAG(value, 1) OVER (PARTITION BY id ORDER BY date)` | Previous period value for growth rate calculation |
| `SUM(amount) OVER (PARTITION BY id ORDER BY date ROWS UNBOUNDED PRECEDING)` | Running total per entity |
| `RANK() OVER (PARTITION BY region ORDER BY revenue DESC)` | Rank within a group (ties share the same rank) |
| `PERCENT_RANK() OVER (ORDER BY value)` | Percentile rank (0 to 1) |

---

## JOIN patterns

| SQL pattern | Business meaning |
|---|---|
| `INNER JOIN` | Keep only rows with a match in both tables |
| `LEFT JOIN` | Keep all rows from the left table; NULLs for unmatched right |
| `LEFT JOIN ... WHERE b.id IS NULL` | Anti-join — rows in A with no match in B |
| `CROSS JOIN` | Every row in A paired with every row in B — rarely intentional |
| `FULL OUTER JOIN` | All rows from both; NULLs where no match |

---

## Common business logic gotchas

**Funnel denominator creep:** Each step in a funnel should use the same base population as the first step, not the previous step, unless you explicitly want step-by-step rates.

**Attribution window:** `event_date BETWEEN signup_date AND signup_date + INTERVAL '30 days'` — check whether the window is inclusive or exclusive at both ends.

**Currency conversion timing:** Is the exchange rate applied at transaction time or reporting time? The difference can be material in volatile periods.

**Fiscal vs calendar year:** `YEAR(date)` gives calendar year. If your company uses a fiscal year, verify whether a helper function or calendar table is needed.
