# Engine-Specific SQL Guide

Key behavioural differences across the four most common data warehouse engines. Check this when a query will be run on a specific engine, or when porting a query between engines.

---

## Snowflake

### Date/Time
- `CURRENT_TIMESTAMP` returns a `TIMESTAMP_LTZ` by default — use `CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP)` for consistency.
- `DATE_TRUNC('month', col)` returns a DATE; truncation granularity strings must be lowercase or uppercase (not mixed).
- `DATEADD(day, -7, CURRENT_DATE)` — Snowflake supports DATEADD natively.
- String-to-date: prefer explicit `TO_DATE(col, 'YYYY-MM-DD')` over implicit casting.

### Performance
- **Micro-partition pruning**: filter on columns that are naturally ordered (e.g. `created_at`) to leverage micro-partition metadata.
- **Clustering keys**: for very large tables (> 500M rows), check if a clustering key exists on the filter column — use `SYSTEM$CLUSTERING_INFORMATION('<table>')`.
- **RESULT_CACHE**: Snowflake caches identical query results for 24 hours. Use `ALTER SESSION SET USE_CACHED_RESULT = FALSE` for benchmarking.
- **VARIANT / SEMI-STRUCTURED**: accessing nested JSON with `col:field::string` is efficient; avoid parsing entire VARIANT columns unnecessarily.

### Gotchas
- `ILIKE` is case-insensitive LIKE — useful for string matching on user input.
- `QUALIFY` can replace outer subqueries for window function filtering.
- CTEs are materialised by default when referenced more than once in some query plans — no need to force materialisation with a temp table.

---

## BigQuery

### Date/Time
- `CURRENT_DATE()` / `CURRENT_TIMESTAMP()` — note the parentheses (function call syntax).
- `DATE_TRUNC(date_col, MONTH)` — second argument is a keyword, not a string.
- `TIMESTAMP_DIFF(ts1, ts2, DAY)` — argument order matters.
- BigQuery stores timestamps in UTC; use `DATETIME` type for local-timezone-aware data.

### Performance
- **Partitioning**: always filter on the partition column (`_PARTITIONTIME` or a declared partition field). Unfiltered partition scans process the full table.
- **Clustering**: cluster on columns used in GROUP BY and WHERE after the partition column. Use `INFORMATION_SCHEMA.TABLE_STORAGE` to verify clustering is in effect.
- **Wildcard tables**: `FROM project.dataset.events_*` with `WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'` — always restrict with `_TABLE_SUFFIX`.
- **Flattening arrays**: `UNNEST()` is needed to expand ARRAY columns — each unnested element creates a new row.

### Gotchas
- `ARRAY_AGG` without `IGNORE NULLS` includes NULLs in the array.
- `COUNTIF(condition)` is BigQuery-specific shorthand for `SUM(CASE WHEN condition THEN 1 ELSE 0 END)`.
- Standard SQL dialect vs. legacy SQL: always use Standard SQL (`#standardSQL` or project-default setting).

---

## PostgreSQL

### Date/Time
- `NOW()` returns `TIMESTAMP WITH TIME ZONE` in the server timezone.
- `DATE_TRUNC('month', col)` returns `TIMESTAMP`, not `DATE` — cast with `::DATE` if needed.
- `INTERVAL`: use `col + INTERVAL '7 days'` (quoted, with unit).
- `EXTRACT(epoch FROM ts)` for Unix timestamp conversion.

### Performance
- **Index use**: `WHERE LOWER(email) = 'x@y.com'` prevents index use — create a functional index `ON users(LOWER(email))` or store email pre-lowercased.
- **EXPLAIN ANALYZE**: always use both keywords — `EXPLAIN` alone shows estimated plan; `ANALYZE` executes and shows actual times.
- **Vacuum/Analyze**: stale statistics cause bad query plans. Run `ANALYZE <table>` after large data loads.
- **CTE fence**: in Postgres < 12, CTEs are optimisation fences (always materialised). In Postgres ≥ 12, the planner may inline them. Use `WITH MATERIALIZED` / `WITH NOT MATERIALIZED` to be explicit.

### Gotchas
- `SERIAL` / `BIGSERIAL` are not true types — they're shorthand for sequences. Use `GENERATED ALWAYS AS IDENTITY` for new tables.
- `||` for string concatenation (not `+`).
- `ILIKE` for case-insensitive pattern matching.

---

## Redshift

### Date/Time
- `GETDATE()` returns current time in UTC (not server TZ).
- `DATEADD(day, -7, GETDATE())` — similar to Snowflake; supported natively.
- `DATEDIFF(day, start, end)` — argument order is unit, start, end (not start, end, unit like some other engines).

### Performance
- **Distribution key (DISTKEY)**: used for join colocation. JOIN on a non-DISTKEY causes data redistribution. Use `SVV_TABLE_INFO` to check.
- **Sort key (SORTKEY)**: filter on the leading sort key column to enable zone map pruning. Check with `SVL_QUERY_SUMMARY`.
- **VACUUM / ANALYZE**: Redshift needs periodic VACUUM to reclaim space from deletes and re-sort data. Monitor with `SVV_TABLE_INFO.unsorted_pct`.
- **Result caching**: enabled by default; disable with `SET enable_result_cache_for_session = off` for benchmarking.

### Gotchas
- Maximum VARCHAR is 65535 bytes — large JSON stored as text hits this.
- `LISTAGG` is Redshift's equivalent of `STRING_AGG` / `GROUP_CONCAT`.
- Redshift does not enforce primary key / unique constraints — duplicates can exist silently.
- Window functions cannot be nested; use a subquery to apply a window function to another window function's output.
