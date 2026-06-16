# MotherDuck + DuckDB Compatibility Matrix

This document outlines SQL and feature compatibility between local DuckDB and MotherDuck cloud backend for the NYC DOT Analytics Toolkit.

## Key Principles

1. **Default: Local DuckDB** — All queries work with local DuckDB (no external dependencies)
2. **Optional: MotherDuck** — Set `MOTHERDUCK_TOKEN` environment variable to enable cloud backend
3. **Conservative Approach** — Only use features available in both engines
4. **Automatic Validation** — All queries automatically validated for compatibility

## Compatibility Status

| Feature | DuckDB Local | MotherDuck Cloud | Notes |
|---------|--------------|------------------|-------|
| **Data Types** |
| INTEGER, FLOAT, VARCHAR | ✅ | ✅ | Core types, fully supported |
| TIMESTAMP | ✅ | ✅ | Always use ISO 8601 format |
| STRUCT, LIST, MAP | ✅ | ✅ | Complex types work both ways |
| VARIANT | ✅ | ❌ | **ERROR**: Use VARCHAR or STRUCT instead |
| GEOMETRY (native) | ✅ | ❌ | **ERROR**: Use WKT/WKB strings or spatial extension |
| **Functions** |
| COUNT, SUM, AVG, MIN, MAX | ✅ | ✅ | Standard aggregates |
| MEDIAN, STDDEV, QUANTILE_CONT | ✅ | ✅ | Statistical functions |
| GROUP BY ALL, EXCLUDE, REPLACE | ✅ | ✅ | DuckDB syntax extensions |
| UNION BY NAME | ✅ | ✅ | Column-name-based union |
| ROW_NUMBER, DENSE_RANK, LAG | ✅ | ✅ | Window functions |
| GENERATE_SERIES, UNNEST | ✅ | ✅ | Array/series functions |
| date_trunc (all units) | ✅ | ⚠️ | **WARNING**: `'decade'` added recently; use explicit math |
| DATE_TRUNC with 'week' | ✅ | ✅ | Week truncation works |
| **SQL Statements** |
| SELECT, WHERE, GROUP BY, ORDER BY | ✅ | ✅ | Core SQL |
| CASE WHEN THEN | ✅ | ✅ | Conditional logic |
| UNION, UNION ALL | ✅ | ✅ | Set operations |
| JOIN (all types) | ✅ | ✅ | Joins work identically |
| CREATE TABLE AS SELECT | ✅ | ✅ | CTAS for materialization |
| INSERT, UPDATE, DELETE | ✅ | ✅ | DML statements |
| MERGE INTO | ✅ | ❌ | **ERROR**: Use INSERT/UPDATE separately |
| ALTER TABLE | ✅ | ✅ | Schema modification |
| **Temporary Tables** |
| TEMPORARY TABLE | ✅ | ⚠️ | **WARNING**: Different lifetime; exists for session |
| Explicit drop on close | ✅ | ✅ | Recommended pattern |
| **Extensions** |
| httpfs (S3, GCS, HTTP) | ✅ | ✅ | Pre-loaded in MotherDuck |
| parquet | ✅ | ✅ | Pre-loaded |
| delta | ✅ | ✅ | Pre-loaded |
| json | ✅ | ✅ | Pre-loaded |
| icu (date/time) | ✅ | ✅ | Pre-loaded |
| spatial | ✅ | ⚠️ | **WARNING**: May have version lag |
| fts (full-text search) | ✅ | ⚠️ | **WARNING**: May have version lag |
| LOAD extension | ✅ | ❌ | **WARNING**: Client-only; omit in MotherDuck mode |
| **File Access** |
| Local filesystem paths | ✅ | ❌ | MotherDuck cannot access local files |
| S3 paths (httpfs) | ✅ | ✅ | Use `s3://bucket/key` format |
| GCS paths (httpfs) | ✅ | ✅ | Use `gs://bucket/key` format |
| HTTP(S) URLs | ✅ | ✅ | Direct HTTP(S) read supported |
| DuckDB paths | ✅ | ✅ | Shared catalog paths work |
| **Special Features** |
| Parquet caching | ✅ | ✅ | L2 cache via Parquet |
| Schema inference | ✅ | ✅ | Auto-detect column types |
| Snapshots (operational) | ❌ | ✅ | MotherDuck-specific backup |
| Shares (data sharing) | ❌ | ✅ | MotherDuck-specific collaboration |
| Postgres endpoint | N/A | ✅ | Connect via psql (different behavior) |

## Implementation Rules

### Errors (Won't Run)

These will raise `ValueError` during validation:

```python
# ❌ VARIANT type
SELECT CAST(col AS VARIANT) FROM table
# Fix: SELECT CAST(col AS VARCHAR) FROM table

# ❌ GEOMETRY type
SELECT ST_Point(1, 2)::GEOMETRY FROM table
# Fix: SELECT ST_AsText(ST_Point(1, 2)) as geom FROM table

# ❌ MERGE INTO
MERGE INTO target t USING source s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET val = s.val
# Fix: Use INSERT/UPDATE separately

# ❌ LOAD statement (server mode)
LOAD httpfs;
SELECT * FROM read_parquet('s3://bucket/file.parquet')
# Fix: Remove LOAD; extensions pre-loaded in MotherDuck
SELECT * FROM read_parquet('s3://bucket/file.parquet')
```

### Warnings (Will Run, but May Behave Differently)

These log warnings but continue:

```python
# ⚠️ date_trunc('decade', ...)
SELECT date_trunc('decade', created_date) FROM table
# Fix: SELECT date_trunc('year', created_date) - INTERVAL '5 years' FROM table

# ⚠️ Local filesystem access
SELECT * FROM read_csv_auto('/local/file.csv')
# Fix: SELECT * FROM read_csv_auto('s3://bucket/file.csv')

# ⚠️ TEMPORARY TABLE
CREATE TEMPORARY TABLE staging AS SELECT * FROM source
# Fix: Consider using persistent tables or explicit drop on close
DROP TABLE IF EXISTS staging
```

### All Clear (No Issues)

These queries are fully compatible:

```python
# ✅ Cross-tabulation with window functions
SELECT
  material,
  borough,
  COUNT(*) as cnt,
  ROW_NUMBER() OVER (PARTITION BY material ORDER BY cnt DESC) as rank
FROM staging.inspection
GROUP BY material, borough

# ✅ Statistical summary
SELECT
  COUNT(*) as n,
  AVG(value) as mean,
  MEDIAN(value) as median,
  STDDEV(value) as stddev,
  QUANTILE_CONT(value, 0.25) as q1,
  QUANTILE_CONT(value, 0.75) as q3
FROM analytics.metrics
WHERE value IS NOT NULL

# ✅ Multi-dataset union
SELECT * FROM table1 WHERE date > '2026-01-01'
UNION BY NAME
SELECT * FROM table2 WHERE date > '2026-01-01'
```

## Configuration

### Using Local DuckDB (Default)

No setup required. All queries execute locally.

```python
from socrata_toolkit.core.motherduck_integration import get_connection

conn = get_connection(use_motherduck=False)
result = conn.execute("SELECT * FROM staging.inspection")
```

### Using MotherDuck Cloud

1. Set environment variable:
   ```bash
   export MOTHERDUCK_TOKEN="<your-token>"
   ```

2. Use in code:
   ```python
   from socrata_toolkit.core.motherduck_integration import get_connection

   conn = get_connection(use_motherduck=True)
   result = conn.execute("SELECT * FROM staging.inspection")
   ```

3. Fallback: If `MOTHERDUCK_TOKEN` not set, automatically falls back to local DuckDB

### Validation Modes

```python
# Enable validation (default): catch compatibility issues before execution
conn.execute(sql, validate=True)

# Skip validation: for internal SQL known to be compatible
conn.execute(sql, validate=False)
```

## Migration Guide

### From Local-Only to MotherDuck-Ready

1. **Audit existing SQL:**
   ```python
   from socrata_toolkit.core.motherduck_integration import MotherDuckValidator
   
   validator = MotherDuckValidator()
   issues = validator.validate(sql)
   for issue in issues:
       print(f"{issue.severity}: {issue.reason}")
   ```

2. **Fix incompatibilities:**
   - Replace VARIANT → VARCHAR or STRUCT
   - Replace GEOMETRY → WKT/WKB strings
   - Replace MERGE INTO → INSERT/UPDATE
   - Remove LOAD statements

3. **Update file paths:**
   - Local CSV → S3/GCS via httpfs
   - Local Parquet → S3/GCS via httpfs

4. **Test both backends:**
   ```python
   # Test local
   conn_local = get_connection(use_motherduck=False)
   result_local = conn_local.execute(sql)
   
   # Test cloud
   conn_cloud = get_connection(use_motherduck=True)
   result_cloud = conn_cloud.execute(sql)
   
   # Compare results
   assert result_local.fetchall() == result_cloud.fetchall()
   ```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `VARIANT type not supported` | Using VARIANT type | Use VARCHAR or STRUCT |
| `GEOMETRY type not supported` | Using native GEOMETRY | Use WKT/WKB strings |
| `MERGE INTO not supported` | Using MERGE statement | Use INSERT/UPDATE separately |
| `Table not found` | File not accessible on MotherDuck | Move to S3/GCS with httpfs |
| `Connection failed` | MOTHERDUCK_TOKEN invalid or expired | Check token, refresh if needed |
| `Slow performance` | Large local dataset not indexed | Materialize to MotherDuck share first |

## Future Compatibility

This matrix is updated quarterly. Key versioning:
- **DuckDB**: Track latest stable release
- **MotherDuck**: Typically lags DuckDB by 1-2 releases

Check `motherduck.com/docs` for latest feature announcements.
