# Pandas / DuckDB Recipes — NYC DOT EDA Patterns

Practical code snippets for common EDA operations on SIM datasets.
Prefer DuckDB for large files (> 500K rows); use pandas for
interactive analysis and plotting.

---

## Loading Data

### From Socrata API (pandas)
```python
import sys; sys.path.insert(0, "src")
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe("data.cityofnewyork.us", "dntt-gqwq", max_rows=50000)
```

### From Parquet cache (DuckDB)
```python
import duckdb

conn = duckdb.connect()
df = conn.execute("""
    SELECT objectid, borough, status, inspection_date
    FROM read_parquet('data/cache/inspection.parquet')
    WHERE inspection_date >= '2026-01-01'
    LIMIT 50000
""").df()
```

### From Parquet cache (pandas)
```python
import pandas as pd
df = pd.read_parquet("data/cache/inspection.parquet",
                     columns=["objectid", "borough", "status", "inspection_date"])
```

---

## Overview Profiling

### Row count, dtypes, memory
```python
print(f"Rows: {len(df):,}  Cols: {len(df.columns)}")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")
print(df.dtypes)
print(df.head(3))
```

### DuckDB equivalent (fast on large files)
```python
conn.execute("SUMMARIZE SELECT * FROM read_parquet('data/cache/violations.parquet')").df()
```

---

## Null Profiling

### pandas
```python
null_report = (
    df.isna()
    .sum()
    .rename("null_count")
    .to_frame()
    .assign(null_pct=lambda x: x["null_count"] / len(df) * 100)
    .sort_values("null_pct", ascending=False)
)
```

### DuckDB (counts nulls per column without loading into memory)
```python
select_nulls = ", ".join(
    f"COUNT(*) FILTER (WHERE {col} IS NULL) AS {col}_nulls"
    for col in ["objectid", "borough", "status", "inspection_date"]
)
conn.execute(f"SELECT {select_nulls} FROM read_parquet('data/cache/inspection.parquet')").df()
```

---

## Borough Distribution

```python
# pandas
boro_dist = df["borough"].str.upper().value_counts(dropna=False).rename("count")
boro_dist_pct = (boro_dist / len(df) * 100).rename("pct")
print(pd.concat([boro_dist, boro_dist_pct], axis=1))

# DuckDB
conn.execute("""
    SELECT upper(borough) AS borough, COUNT(*) AS cnt,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM read_parquet('data/cache/inspection.parquet')
    GROUP BY ALL ORDER BY cnt DESC
""").df()
```

---

## Date Range Validation

```python
import pandas as pd
from datetime import date

df["inspection_date"] = pd.to_datetime(df["inspection_date"], errors="coerce")

future_dates = df[df["inspection_date"] > pd.Timestamp.now()]
pre_2000 = df[df["inspection_date"] < pd.Timestamp("2000-01-01")]

print(f"Future dates: {len(future_dates):,}  |  Pre-2000: {len(pre_2000):,}")
```

---

## IQR Outlier Detection

```python
import numpy as np

def iqr_outliers(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (series < q1 - multiplier * iqr) | (series > q3 + multiplier * iqr)

numeric_cols = df.select_dtypes(include=np.number).columns
for col in numeric_cols:
    flags = iqr_outliers(df[col].dropna())
    pct = flags.sum() / len(flags) * 100
    if pct > 1:
        print(f"{col}: {flags.sum():,} outliers ({pct:.1f}%)")
```

---

## Correlation Matrix

```python
import numpy as np

corr = df.select_dtypes(include=np.number).corr()

# Find high-correlation pairs
pairs = (
    corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    .stack()
    .abs()
    .sort_values(ascending=False)
)
print(pairs[pairs > 0.6].rename("abs_correlation"))
```

---

## Borough-Level Groupby (Standard Pattern)

```python
# Always use this pattern for borough aggregations
BOROUGHS = ["MN", "BX", "BK", "QN", "SI"]

summary = (
    df.assign(borough_code=df["borough"].str.upper()
              .map({"MANHATTAN": "MN", "BRONX": "BX", "BROOKLYN": "BK",
                    "QUEENS": "QN", "STATEN ISLAND": "SI"})
              .fillna(df["borough"].str.upper()))
    .query("borough_code in @BOROUGHS")
    .groupby("borough_code")
    .agg(
        total=("objectid", "count"),
        open_count=("status", lambda s: (s.str.upper() == "OPEN").sum()),
    )
    .assign(open_rate=lambda df: df["open_count"] / df["total"] * 100)
    .reindex(BOROUGHS)
)
```

---

## Chunked Read for Large Files

```python
# Use when inspection.parquet > 1 GB and RAM is constrained
import pyarrow.parquet as pq

pf = pq.ParquetFile("data/cache/inspection.parquet")
results = []
for batch in pf.iter_batches(batch_size=50000, columns=["objectid", "borough", "status"]):
    chunk = batch.to_pandas()
    results.append(chunk.groupby("borough")["objectid"].count())

borough_totals = pd.concat(results).groupby(level=0).sum()
```
