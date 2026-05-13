# `socrata_toolkit.core` — Core Client & Infrastructure

**File:** `socrata_toolkit/core.py` | **Pillar:** Core  
**Dependencies:** `duckdb`, `pandas`, `requests`, `tenacity`

---

## Key Constants

| Constant | Value |
|----------|-------|
| `CATALOG_URL` | `https://api.us.socrata.com/api/catalog/v1` |
| `DEFAULT_DOMAIN` | `data.cityofnewyork.us` |
| `COL_LAT/LON` | `latitude` / `longitude` |
| `COL_BORO` | `borough` |

---

## Data Classes

### `SearchResult`
One result from the Socrata Discovery API.
```python
@dataclass
class SearchResult:
    name: str; description: str; domain: str; fourfour: str
    page_views_last_month: int|None; category: str|None; tags: list[str]
```

### `DatasetMetadata`
Full dataset metadata from `/api/views/{id}`.
```python
@dataclass
class DatasetMetadata:
    domain: str; fourfour: str; name: str; description: str
    row_count: int|None; license: str|None; columns: list[dict]

    @property
    def is_geo(self) -> bool: ...       # True if geo columns present
    def summary(self) -> dict: ...      # Condensed metadata
    def column_dict(self) -> list: ...  # Clean column defs
```

### `SocrataConfig`
```python
@dataclass
class SocrataConfig:
    app_token: str|None = None  # defaults to SOCRATA_APP_TOKEN env var
    timeout: int = 30
    page_size: int = 1000
```

---

## `SocrataClient`

Main HTTP client for the Socrata SODA API. Handles auth, retries, and pagination.

```python
client = SocrataClient()
# or
client = SocrataClient(SocrataConfig(app_token="TOKEN", page_size=2000))
```

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `search(query, domain, category, tags, order, limit)` | `list[SearchResult]` | Discovery catalog search |
| `get_metadata(domain, fourfour)` | `DatasetMetadata` | Full dataset metadata |
| `fetch_json(domain, fourfour, *, where, select, order, q, max_rows)` | `Generator` | Streaming paginated JSON |
| `fetch_dataframe(domain, fourfour, **kwargs)` | `pd.DataFrame` | Collect all pages into DataFrame |
| `parallel_fetch(domain, fourfour, limit, max_workers=8)` | `pd.DataFrame` | Multi-threaded parallel fetch |
| `fetch_geojson(domain, fourfour, *, where, max_rows)` | `dict` | GeoJSON FeatureCollection |
| `fetch_since(domain, fourfour, updated_col, since)` | `Generator` | Incremental fetch since timestamp |
| `fetch_odata(domain, fourfour, top=100)` | `pd.DataFrame` | OData v4 protocol |
| `search_datasets(query, limit, offset)` | `pd.DataFrame` | Catalog search as DataFrame |
| `catalog_query(soql)` | `pd.DataFrame` | Raw `$query` against catalog |

**Example — parallel fetch 50k rows:**
```python
df = client.parallel_fetch("data.cityofnewyork.us", "erm2-nwe9", limit=50000)
```

**Example — incremental sync:**
```python
for batch in client.fetch_since("data.cityofnewyork.us", "erm2-nwe9",
                                  updated_col=":updated_at",
                                  since="2024-06-01T00:00:00"):
    process(batch)
```

---

## `SoQLBuilder`

Fluent builder for Socrata Query Language.

```python
from socrata_toolkit import SoQLBuilder

params = (
    SoQLBuilder()
    .select("borough", "complaint_type", "count(*) AS cnt")
    .where("created_date > '2024-01-01'", "borough IS NOT NULL")
    .group("borough", "complaint_type")
    .order("cnt", desc=True)
    .limit(100)
    .build()
)
```

### Builder Methods

| Method | SoQL param | Notes |
|--------|-----------|-------|
| `.select(*cols)` | `$select` | Column list |
| `.where(*clauses)` | `$where` | ANDed filter clauses |
| `.order(col, desc)` | `$order` | |
| `.group(*cols)` | `$group` | |
| `.having(*clauses)` | `$having` | Post-aggregation filter |
| `.limit(n)` | `$limit` | |
| `.offset(n)` | `$offset` | |
| `.search(q)` | `$q` | Full-text search |
| `.aggregate(func, col, alias)` | `$select` | `COUNT(*)`, `SUM(col)` |
| `.date_trunc(col, precision, alias)` | `$select` | `date_trunc_month(col)` |
| `.build()` | — | Returns `dict[str,str]` for `requests` |
| `.build_query_string()` | — | Returns raw SoQL string |

### Static Geo Helpers
```python
SoQLBuilder.within_circle("location", 40.7128, -74.006, 500)
# → "within_circle(location, 40.7128, -74.006, 500)"

SoQLBuilder.within_box("location", 40.91, -74.26, 40.48, -73.70)
# → "within_box(location, 40.91, -74.26, 40.48, -73.7)"

SoQLBuilder.between("created_date", "2024-01-01", "2024-12-31")
# → "created_date between '2024-01-01' and '2024-12-31'"
```

---

## Schema Registry

### `SchemaRegistry`
Persists versioned dataset schemas as JSON files in `schema_registry/`.
```python
registry = SchemaRegistry(storage_dir="schema_registry/")
registry.register_schema(schema)  # Saves as {id}_v{version}.json
```

### `SchemaValidator`
Validates a DataFrame against an expected schema.
```python
validator = SchemaValidator({"borough": "object", "latitude": "float64"})
errors = validator.validate(df)  # → ["Missing: latitude"]
```

---

## DuckDB Layer

### `DuckDBManager`
Single-connection DuckDB manager with spatial extension auto-load.
```python
mgr = DuckDBManager("nyc_mission_control.db")
mgr.query("SELECT COUNT(*) FROM sidewalks").fetchone()
mgr.close()
```

### `DuckDBRepository`
Batch upserts with `ON CONFLICT` support.
```python
repo = DuckDBRepository(mgr, "sidewalks")
repo.upsert_dataframe(df, conflict_column="id")
repo.fetch_all(limit=1000)
repo.count()
```

### `DuckDBExporter`
Context-manager for streaming batch upserts.
```python
with DuckDBExporter("nyc.db") as exp:
    exp.upsert_batches([batch1, batch2], table="sidewalks", conflict_column="id")
```

---

## Exporters

### `XLSXExporter`
```python
XLSXExporter().write(df, "output.xlsx", sheet="Data", meta=metadata)
```
Writes frozen-header Excel with optional Summary + Column Dictionary sheets.

### `ParquetExporter`
```python
ParquetExporter().write(df, "output.parquet", compression="snappy")
```

---

## Utility Functions

| Function | Description |
|----------|-------------|
| `search_nyc_datasets(query, domain, limit)` | Convenience NYC catalog search |
| `generate_data_dictionary(df)` | Column name/dtype/null% list |
| `with_retries(fn, retries=3)` | Exponential-backoff HTTP retry |
| `ensure_fts_index(dsn, table, columns)` | Create Postgres GIN FTS index |
| `get_bundle_dir()` | PyInstaller bundle path detection |

---

## Exceptions

### `SocrataToolkitError`
Base exception for all toolkit errors. Raised on HTTP failures, API errors, and connection issues.
```python
try:
    client.get_metadata("data.cityofnewyork.us", "bad-id")
except SocrataToolkitError as e:
    print(f"API error: {e}")
```
