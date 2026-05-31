# Pandas / Polars Recipes for EDA

Side-by-side patterns for common EDA operations. Use pandas when the data fits in memory (~< 1 GB) and you want ecosystem breadth; use polars for larger files or when you need faster runtimes.

## Loading Data

| Task | pandas | polars |
|---|---|---|
| CSV | `pd.read_csv("f.csv")` | `pl.read_csv("f.csv")` |
| Parquet | `pd.read_parquet("f.parquet")` | `pl.read_parquet("f.parquet")` |
| Large CSV (chunked) | `pd.read_csv("f.csv", chunksize=100_000)` | `pl.scan_csv("f.csv").collect()` (lazy) |

## Shape & Schema

```python
# pandas
df.shape          # (rows, cols)
df.dtypes         # per-column dtype
df.info()         # non-null counts + dtypes together

# polars
df.shape
df.schema         # {col: dtype}
df.describe()
```

## Null Profiling

```python
# pandas
df.isna().sum()
df.isna().mean() * 100          # null %

# polars
df.null_count()
df.select(pl.all().is_null().mean() * 100)
```

## Deduplication

```python
# pandas
df.duplicated().sum()            # full-row duplicates
df.duplicated(subset=["id"]).sum()  # key duplicates
df.drop_duplicates(subset=["id"], keep="first")

# polars
df.is_duplicated().sum()
df.unique(subset=["id"])
```

## Descriptive Stats

```python
# pandas
df.describe(percentiles=[.05, .25, .5, .75, .95])
df["col"].skew()
df["col"].kurt()

# polars
df.describe()
df.select(pl.col("col").skew(), pl.col("col").kurtosis())
```

## Value Counts / Frequency Tables

```python
# pandas
df["col"].value_counts(dropna=False, normalize=True)

# polars
df["col"].value_counts(sort=True)
```

## Filter & Inspect Outliers

```python
# pandas
q1, q3 = df["col"].quantile([0.25, 0.75])
iqr = q3 - q1
outliers = df[(df["col"] < q1 - 1.5*iqr) | (df["col"] > q3 + 1.5*iqr)]

# polars
q1 = df["col"].quantile(0.25)
q3 = df["col"].quantile(0.75)
iqr = q3 - q1
outliers = df.filter((pl.col("col") < q1 - 1.5*iqr) | (pl.col("col") > q3 + 1.5*iqr))
```

## Correlation

```python
# pandas
df.corr(method="pearson")        # or "spearman", "kendall"

# polars (pearson only natively)
df.select(pl.pearson_corr("col_a", "col_b"))
# For full matrix, convert to pandas: df.to_pandas().corr()
```

## Date/Time Operations

```python
# pandas
df["date"] = pd.to_datetime(df["date"])
df["date"].dt.year
df["date"].dt.floor("D")         # truncate to day
df.set_index("date").resample("M").size()  # monthly counts

# polars
df.with_columns(pl.col("date").str.to_datetime())
df["date"].dt.year()
df.group_by(pl.col("date").dt.truncate("1mo")).agg(pl.count())
```

## Memory Reduction Tips (pandas)

```python
# Downcast numerics
df["int_col"] = pd.to_numeric(df["int_col"], downcast="integer")
df["float_col"] = pd.to_numeric(df["float_col"], downcast="float")
# Convert low-cardinality strings to category
df["country"] = df["country"].astype("category")
```

## Reading Large Files Without Loading All at Once

```python
# pandas chunked read
total_rows = 0
for chunk in pd.read_csv("big.csv", chunksize=500_000):
    total_rows += len(chunk)

# polars lazy (reads only what's needed)
result = (
    pl.scan_csv("big.csv")
    .filter(pl.col("revenue") > 0)
    .group_by("country")
    .agg(pl.col("revenue").sum())
    .collect()
)
```
