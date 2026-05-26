# 🔍 SOQL Guide

**SOQL** (Socrata Query Language) is SQL-like syntax for querying NYC Open Data datasets directly in your browser. Use it in the **SOQL Studio** tab of Manhattan Mission Control.

---

## 📚 Table of Contents

1. [What is SOQL?](#what-is-soql)
2. [Basic Syntax](#basic-syntax)
3. [SELECT — Choose Columns](#select)
4. [WHERE — Filter Rows](#where)
5. [GROUP BY — Aggregate](#group-by)
6. [ORDER BY — Sort Results](#order-by)
7. [LIMIT / OFFSET — Pagination](#limit--offset)
8. [Date & Time Queries](#date--time-queries)
9. [Text Queries](#text-queries)
10. [Geospatial Queries](#geospatial-queries)
11. [Numeric & Math Functions](#numeric--math-functions)
12. [Aggregate Functions](#aggregate-functions)
13. [Common Patterns](#common-patterns)
14. [SOQL vs SQL Differences](#soql-vs-sql-differences)
15. [Full Examples](#full-examples)

---

## What is SOQL?

SOQL is a query language that works against the **Socrata REST API**. When you write a SOQL query in the Mission Control SOQL Studio, it gets translated into a URL like:

```
https://data.cityofnewyork.us/resource/{dataset-id}.json?$query=SELECT...
```

SOQL supports most common SQL operations but has some important differences (see [SOQL vs SQL Differences](#soql-vs-sql-differences)).

---

## Basic Syntax

```sql
SELECT column1, column2, ...
WHERE condition
GROUP BY column
ORDER BY column ASC|DESC
LIMIT number
OFFSET number
```

All clauses are optional. The minimum valid query is just `SELECT *` (returns first 1,000 rows).

---

## SELECT

### Select all columns (default)
```sql
SELECT *
```

### Select specific columns
```sql
SELECT inspection_id, street_name, borough, status
```

### Rename columns with aliases
```sql
SELECT borough AS neighborhood, COUNT(*) AS total_inspections
```

### Computed columns
```sql
SELECT inspection_id,
       date_extract_y(inspection_date) AS year,
       upper(street_name) AS street_upper
```

---

## WHERE

### Equals
```sql
WHERE borough = 'MANHATTAN'
WHERE status = 'Open'
WHERE year = 2024
```

> 🔤 **String values must use single quotes**, not double quotes.

### Comparison operators
```sql
WHERE row_count > 100
WHERE created_date >= '2024-01-01T00:00:00.000'
WHERE rating != 'Poor'
```

### Multiple conditions
```sql
WHERE borough = 'MANHATTAN'
  AND status = 'Open'
  AND year = 2024
```

```sql
WHERE borough = 'BROOKLYN'
  OR borough = 'QUEENS'
```

### IN — match any of a list
```sql
WHERE borough IN ('MANHATTAN', 'BRONX', 'BROOKLYN')
```

### IS NULL / IS NOT NULL
```sql
WHERE closing_date IS NULL          -- still open
WHERE closing_date IS NOT NULL      -- has been closed
```

### BETWEEN — range filter
```sql
WHERE year BETWEEN 2020 AND 2024
```

---

## GROUP BY

### Basic count
```sql
SELECT borough, COUNT(*) AS total
GROUP BY borough
```

### Multiple grouping columns
```sql
SELECT borough, status, COUNT(*) AS total
GROUP BY borough, status
ORDER BY borough, total DESC
```

### HAVING — filter after grouping
```sql
SELECT borough, COUNT(*) AS total
GROUP BY borough
HAVING COUNT(*) > 100
ORDER BY total DESC
```

---

## ORDER BY

```sql
-- Ascending (A→Z, 0→9)
ORDER BY borough ASC

-- Descending (Z→A, 9→0)
ORDER BY total DESC

-- Multiple columns
ORDER BY borough ASC, total DESC
```

---

## LIMIT / OFFSET

```sql
-- First 100 rows
LIMIT 100

-- Rows 201-300 (pagination)
LIMIT 100 OFFSET 200
```

> ⚠️ The default limit is **1,000 rows**. Maximum is **50,000** per request. For larger datasets, use pagination.

---

## Date & Time Queries

### Filter by date
```sql
WHERE inspection_date >= '2024-01-01T00:00:00.000'
WHERE inspection_date BETWEEN '2024-01-01T00:00:00.000' AND '2024-12-31T23:59:59.000'
```

> 📅 Dates must be in **ISO 8601 format**: `YYYY-MM-DDTHH:MM:SS.000`

### Extract date parts
```sql
SELECT date_extract_y(inspection_date) AS year,
       date_extract_m(inspection_date) AS month,
       date_extract_d(inspection_date) AS day
```

| Function | Returns |
|----------|---------|
| `date_extract_y(col)` | Year (e.g., 2024) |
| `date_extract_m(col)` | Month (1–12) |
| `date_extract_d(col)` | Day of month (1–31) |
| `date_extract_dow(col)` | Day of week (0=Sunday) |
| `date_extract_hh(col)` | Hour (0–23) |
| `date_extract_mm(col)` | Minute (0–59) |
| `date_trunc_y(col)` | Truncate to year |
| `date_trunc_ym(col)` | Truncate to month |

---

## Text Queries

### Exact match (case-sensitive)
```sql
WHERE borough = 'MANHATTAN'
```

### Case-insensitive
```sql
WHERE upper(borough) = 'MANHATTAN'
WHERE lower(status) = 'open'
```

### Contains (LIKE)
```sql
WHERE street_name LIKE '%BROADWAY%'
```

> `%` matches any sequence of characters. `_` matches exactly one character.

### Starts with
```sql
WHERE street_name LIKE 'PARK%'
```

### Full-text search
```sql
WHERE street_name = 'BROADWAY'         -- exact
WHERE street_name LIKE '%BROAD%'       -- contains
```

---

## Geospatial Queries

### Within a circle (radius search)
```sql
-- Within 500 meters of Times Square
WHERE within_circle(location, 40.7580, -73.9855, 500)
```

Parameters: `within_circle(geo_column, latitude, longitude, radius_in_meters)`

### Within a bounding box
```sql
WHERE within_box(location, 40.700, -74.020, 40.800, -73.900)
```

Parameters: `within_box(geo_column, min_lat, min_lon, max_lat, max_lon)`

### Within a polygon (advanced)
```sql
WHERE within_polygon(location, 'MULTIPOLYGON (((-74.01 40.70, -73.97 40.70, ...)))')
```

---

## Numeric & Math Functions

```sql
SELECT abs(value)           -- absolute value
SELECT round(value, 2)      -- round to 2 decimal places
SELECT floor(value)         -- round down
SELECT ceiling(value)       -- round up
SELECT sqrt(value)          -- square root
SELECT log(value)           -- natural log
SELECT pow(value, 2)        -- power (value²)
```

---

## Aggregate Functions

| Function | Description |
|----------|-------------|
| `COUNT(*)` | Count all rows |
| `COUNT(column)` | Count non-null values |
| `SUM(column)` | Sum of values |
| `AVG(column)` | Average value |
| `MIN(column)` | Minimum value |
| `MAX(column)` | Maximum value |
| `MEDIAN(column)` | Median value |
| `STDDEV_POP(column)` | Population standard deviation |
| `STDDEV_SAMP(column)` | Sample standard deviation |

---

## Common Patterns

### Top 10 by count
```sql
SELECT borough, COUNT(*) AS total
GROUP BY borough
ORDER BY total DESC
LIMIT 10
```

### Monthly trend
```sql
SELECT date_trunc_ym(created_date) AS month,
       COUNT(*) AS total
GROUP BY month
ORDER BY month ASC
```

### Null check — find incomplete records
```sql
SELECT COUNT(*) AS total,
       COUNT(street_name) AS has_street,
       COUNT(*) - COUNT(street_name) AS missing_street
```

### Find duplicates
```sql
SELECT inspection_id, COUNT(*) AS duplicates
GROUP BY inspection_id
HAVING COUNT(*) > 1
ORDER BY duplicates DESC
```

### Year-over-year comparison
```sql
SELECT date_extract_y(created_date) AS year,
       COUNT(*) AS total
WHERE date_extract_y(created_date) >= 2020
GROUP BY year
ORDER BY year ASC
```

### Average by borough
```sql
SELECT borough,
       AVG(days_to_close) AS avg_days,
       MIN(days_to_close) AS fastest,
       MAX(days_to_close) AS slowest
GROUP BY borough
ORDER BY avg_days ASC
```

---

## SOQL vs SQL Differences

| Feature | SQL | SOQL |
|---------|-----|------|
| **JOINs** | ✅ Supported | ❌ Not supported |
| **Subqueries** | ✅ Supported | ❌ Not supported |
| **UPDATE/INSERT/DELETE** | ✅ Supported | ❌ Read-only |
| **NULL handling** | `IS NULL` | `IS NULL` ✅ same |
| **String quotes** | `'single'` or `"double"` | `'single'` only |
| **Date literals** | Various formats | Must use ISO 8601 |
| **Geospatial** | Extension-dependent | `within_circle()`, `within_box()` built-in |
| **Full-text search** | `LIKE '%term%'` | `LIKE '%term%'` ✅ same |
| **Window functions** | ✅ Supported | ❌ Not supported |
| **CTEs (WITH clause)** | ✅ Supported | ❌ Not supported |

---

## Full Examples

### Example 1: 311 Complaint Summary
```sql
SELECT complaint_type,
       borough,
       COUNT(*) AS total
WHERE created_date >= '2024-01-01T00:00:00.000'
GROUP BY complaint_type, borough
ORDER BY total DESC
LIMIT 20
```

### Example 2: Recent Sidewalk Inspections in Manhattan
```sql
SELECT inspection_id,
       street_name,
       address_number,
       status,
       inspection_date
WHERE borough = 'MANHATTAN'
  AND inspection_date >= '2024-01-01T00:00:00.000'
  AND status != 'Closed'
ORDER BY inspection_date DESC
LIMIT 50
```

### Example 3: Monthly Activity Trend
```sql
SELECT date_trunc_ym(created_date) AS month,
       COUNT(*) AS new_cases,
       COUNT(closed_date) AS closed_cases
WHERE date_extract_y(created_date) = 2024
GROUP BY month
ORDER BY month ASC
```

### Example 4: Geographic Cluster (within Times Square)
```sql
SELECT *
WHERE within_circle(location, 40.7580, -73.9855, 1000)
  AND status = 'Open'
ORDER BY created_date DESC
LIMIT 100
```

### Example 5: Data Quality Check
```sql
SELECT COUNT(*) AS total_rows,
       COUNT(street_name) AS has_name,
       COUNT(borough) AS has_borough,
       COUNT(location) AS has_coords
```

---

## API URL Structure

Every SOQL query becomes an API call:

```
https://data.cityofnewyork.us/resource/{DATASET_ID}.json
  ?$query=SELECT borough, COUNT(*) GROUP BY borough
  &$limit=1000
  &$app_token=YOUR_TOKEN
```

The SOQL Studio constructs this URL automatically from your query.

---

*[[Home]] · [[Feature-Reference]] · [[Code-Generation]] · [[API-Keys-Setup]]*
