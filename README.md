# 🗂 Socrata Toolkit

A batteries-included Python toolkit for the [Socrata Open Data API (SODA3)](https://dev.socrata.com/).  
Search any Socrata portal, pull data by **4x4 dataset ID**, and pipe it to **PostgreSQL**, **MongoDB**, or **XLSX** — with full metadata / column-dictionary support.

---

## Features

| Capability | Details |
|---|---|
| **Catalog Search** | Full-text, domain, category, tags, sort order |
| **Metadata / Dict** | Name, description, column types, row count, license |
| **JSON Fetch** | Paginated streaming with SoQL WHERE / SELECT / ORDER |
| **GeoJSON Fetch** | Paginated, auto-merged FeatureCollection |
| **XLSX Export** | Styled workbook: Data + Summary + Column Dictionary sheets |
| **Postgres Upsert** | Auto-DDL, `ON CONFLICT … DO UPDATE`, batch streaming |
| **MongoDB Upsert** | `bulk_write` with `upsert=True`, GeoJSON geometry field |
| **CLI** | `socrata search / meta / fetch / upsert-pg / upsert-mongo / pipeline` |
| **Pipeline** | Fetch once, dispatch to all outputs simultaneously |

---

## Installation

```bash
# Core (search, fetch, XLSX)
pip install .

# With PostgreSQL support
pip install ".[postgres]"

# With MongoDB support
pip install ".[mongo]"

# Everything
pip install ".[all]"
```

Set your Socrata app token (removes rate-limiting):
```bash
export SOCRATA_APP_TOKEN="your_token_here"
```

---

## CLI Quick Reference

### Search the catalog
```bash
socrata search "restaurant inspections" --domain data.cityofnewyork.us --limit 10
socrata search --category Health --order page_views_last_month
socrata search "traffic" --domain data.cityofchicago.org --json-out > results.json
```

### Get metadata / column dictionary
```bash
socrata meta data.cityofnewyork.us h9gi-nx95
socrata meta data.cityofnewyork.us h9gi-nx95 --columns-only
socrata meta data.cityofnewyork.us h9gi-nx95 --json-out > meta.json
```

### Fetch data to file
```bash
# JSON (stdout or file)
socrata fetch data.cityofnewyork.us h9gi-nx95 --format json --out crashes.json --max-rows 5000

# GeoJSON
socrata fetch data.cityofnewyork.us abc1-2def --format geojson --out parcels.geojson

# Excel (with Summary + Column Dictionary sheets)
socrata fetch data.cityofnewyork.us h9gi-nx95 \\
  --format xlsx --out crashes.xlsx \\
  --include-meta \\
  --where "crash_date >= '2023-01-01'" \\
  --max-rows 100000
```

### SoQL filtering (works on all commands)
```bash
# Date range
--where "date > '2022-01-01T00:00:00' AND date < '2023-01-01T00:00:00'"

# Select specific columns
--select "id, inspection_date, score, grade"

# Full-text search within dataset
--q "salmonella"

# Sort
--order "inspection_date DESC"
```

### Upsert to PostgreSQL
```bash
socrata upsert-pg data.cityofnewyork.us h9gi-nx95 \\
  --dsn "postgresql://user:pass@localhost:5432/mydb" \\
  --table crashes \\
  --conflict-col collision_id \\
  --save-meta

# Env-var DSN
export PG_DSN="postgresql://user:pass@localhost/mydb"
socrata upsert-pg data.cityofnewyork.us h9gi-nx95 --table crashes --conflict-col collision_id
```

### Upsert to MongoDB
```bash
socrata upsert-mongo data.cityofnewyork.us h9gi-nx95 \\
  --uri "mongodb://localhost:27017" \\
  --db socrata \\
  --collection crashes \\
  --conflict-field collision_id

# GeoJSON mode (stores geometry field — compatible with 2dsphere index)
socrata upsert-mongo data.cityofnewyork.us abc1-2def \\
  --uri $MONGO_URI --db socrata --collection parcels \\
  --geojson --conflict-field parcel_id
```

### Full pipeline (one command → all outputs)
```bash
socrata pipeline data.cityofnewyork.us h9gi-nx95 \\
  --pg-dsn $PG_DSN --pg-table crashes --pg-conflict-col collision_id \\
  --mongo-uri $MONGO_URI --mongo-db socrata --mongo-collection crashes \\
  --xlsx-out crashes.xlsx \\
  --json-out crashes.json \\
  --geojson-out crashes.geojson \\
  --where "crash_date >= '2024-01-01'"
```

---

## Python API

### Search
```python
from socrata_toolkit import SocrataClient, SocrataConfig

client = SocrataClient(SocrataConfig(app_token="MY_TOKEN"))

results = client.search(
    query="restaurant inspections",
    domain="data.cityofnewyork.us",
    limit=20,
    order="page_views_last_month",
)
for r in results:
    print(r.fourfour, r.name, r.domain)
```

### Metadata
```python
meta = client.get_metadata("data.cityofnewyork.us", "43nn-pn8j")
print(meta.summary())
print(meta.column_dict())      # list of dicts for export
print(meta.is_geo)             # True if GeoJSON-capable
```

### Paginated streaming
```python
# Yields List[dict] per page — memory-efficient for huge datasets
for batch in client.fetch_json(
    "data.cityofnewyork.us", "h9gi-nx95",
    where="crash_date >= '2023-01-01'",
    select="collision_id, crash_date, borough, number_of_persons_injured",
    order="crash_date DESC",
    max_rows=500_000,
):
    process(batch)   # your processing function
```

### DataFrame (convenience)
```python
df = client.fetch_dataframe(
    "data.cityofnewyork.us", "h9gi-nx95",
    where="crash_date >= '2024-01-01'",
    max_rows=10_000,
)
print(df.shape)
```

### GeoJSON
```python
geojson = client.fetch_geojson(
    "data.cityofnewyork.us", "abc1-2def",
    where="year = '2023'",
)
# {"type": "FeatureCollection", "features": [...]} 
```

### XLSX Export
```python
from socrata_toolkit.exporters import XLSXExporter

xl = XLSXExporter()
xl.write(
    df,                          # DataFrame or list of dicts
    path="output/inspections.xlsx",
    sheet="Inspections",
    meta=meta,                   # adds Summary + Column Dictionary sheets
    freeze_panes=True,
    auto_filter=True,
)
```

### PostgreSQL
```python
from socrata_toolkit.exporters import PostgresExporter

with PostgresExporter("postgresql://user:pass@localhost/mydb") as pg:
    # Auto-creates table, streams batches directly
    total = pg.upsert_batches(
        client.fetch_json("data.cityofnewyork.us", "h9gi-nx95",
                          where="crash_date >= '2024-01-01'"),
        table="crashes",
        conflict_column="collision_id",
    )
    pg.upsert_metadata(meta)   # saves to _socrata_metadata
    print(f"Upserted {total} rows")
```

### MongoDB
```python
from socrata_toolkit.exporters import MongoExporter

with MongoExporter("mongodb://localhost:27017", "socrata") as mongo:
    total = mongo.upsert_batches(
        client.fetch_json("data.cityofnewyork.us", "h9gi-nx95"),
        collection="crashes",
        conflict_field="collision_id",
    )
    # GeoJSON with geometry field
    gj = client.fetch_geojson("data.cityofnewyork.us", "abc1-2def")
    mongo.upsert_geojson(gj, collection="parcels", conflict_field="bbl")
```

---

## SoQL Reference

Socrata supports a SQL-like query language called SoQL. Useful clauses:

| Clause | SoQL syntax | `--where` / `where=` example |
|---|---|---|
| Date range | `$where=col >= 'YYYY-MM-DDTHH:MM:SS'` | `"crash_date >= '2023-01-01T00:00:00'"` |
| Numeric filter | `$where=score > 80` | `"score > 80"` |
| String match | `$where=grade = 'A'` | `"grade = 'A'"` |
| IS NULL | `$where=borough IS NOT NULL` | `"borough IS NOT NULL"` |
| LIKE | `$where=name LIKE '%pizza%'` | `"name LIKE '%pizza%'"` |
| Geo within box | `$within_box=...` | use `extra_params` in Python |

Full SoQL docs: https://dev.socrata.com/docs/queries/

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `SOCRATA_APP_TOKEN` | Socrata app token (removes throttling) |
| `PG_DSN` | PostgreSQL connection string |
| `MONGO_URI` | MongoDB connection URI |

---

## Project Layout

```
socrata_toolkit/
├── __init__.py        # Public API surface
├── client.py          # SocrataClient — search, metadata, fetch
├── exporters.py       # PostgresExporter, MongoExporter, XLSXExporter
└── cli.py             # Click CLI (socrata command)

requirements.txt
pyproject.toml
README.md
```

---


## Streamlit Workbench

Run the full UX/UI app for search, metadata review, fetch/export, file uploads, and automated upsert pipelines:

```bash
streamlit run socrata_toolkit/app.py
```

The app supports:
- text inputs for SoQL filters and connection settings
- JSON/GeoJSON file upload via file explorer widget
- one-click export to JSON / GeoJSON / XLSX
- automated upsertion to PostgreSQL and MongoDB

---

## License

MIT

---

## Detailed How-To Guide

### 1) Start the toolkit

```bash
pip install .
streamlit run socrata_toolkit/app.py
```

### 2) Search for datasets
1. Open **Search** workflow.
2. Enter query/domain/category/tags.
3. Click **Run Search**.
4. Download `search_results.json` for reproducibility.

### 3) Inspect metadata and columns
1. Open **Metadata** workflow.
2. Enter dataset domain + 4x4 ID.
3. Click **Load Metadata**.
4. Review summary + column dictionary and download metadata JSON.

### 4) Fetch and export data
1. Open **Fetch & Export**.
2. Add optional SoQL (`WHERE`, `SELECT`, `ORDER`, `q`) and max rows.
3. Click **Fetch Data** for preview.
4. Export as JSON / GeoJSON / XLSX in one click.

### 5) Analyze data quality
1. Open **Analysis Studio**.
2. Choose optional filter and row limit.
3. Add key columns for duplicate checks (comma-separated).
4. Click **Run Analysis** to get:
   - row/column stats,
   - missingness chart,
   - type map,
   - numeric summary,
   - duplicate quality report.

CLI equivalent:
```bash
socrata analyze data.cityofnewyork.us h9gi-nx95 --max-rows 10000 --key-column collision_id
```

### 6) Run automated upsertion pipeline
1. Open **Automated Upsert**.
2. Pick source:
   - direct Socrata fetch, or
   - uploaded JSON/GeoJSON file.
3. Select targets (PostgreSQL, MongoDB, XLSX backup).
4. Provide conflict keys and connection strings.
5. Click **Run Automated Upsert Pipeline**.

### 7) Production tips
- Always set `SOCRATA_APP_TOKEN` to reduce throttling.
- Start with narrower `WHERE` filters and lower `max_rows` for fast validation.
- Use stable business keys for upsert conflict columns/fields.
- Save XLSX + metadata JSON snapshots for auditability.


### Installation Wizard (interactive)

Run the guided setup wizard to configure root directory, app token, PostgreSQL/MongoDB credentials, and default preferences:

```bash
python -m socrata_toolkit.install_wizard
# or after install:
socrata-setup
```

The wizard writes:
- `socrata_toolkit.config.json` (preferences and defaults)
- `.env.socrata` (environment values like `SOCRATA_APP_TOKEN`, `PG_DSN`, `MONGO_URI`)



## FAQ

**Q: Do I need a Socrata app token?**  
A: No, but it is strongly recommended to avoid throttling.

**Q: Can I use this without a database?**  
A: Yes. Use JSON/GeoJSON/XLSX exports only.

**Q: What GUI is available?**  
A: Streamlit workbench (`streamlit run socrata_toolkit/app.py`) plus interactive install wizard (`socrata-setup`).

**Q: How do I troubleshoot failed upserts?**  
A: Validate your conflict key exists in the dataset, test with low `max_rows`, and verify DB credentials in `.env.socrata`.

---


## Advanced Text Query + NLP/FTS Toolkit

Capabilities now include:
- lightweight NLP tokenization and frequency extraction
- full-text style term surfacing for text columns
- regex scanning for patterns (emails, phones, URLs, IDs)
- automatic descriptive tag attachment per row
- optional geo-aware tagging (`has_geo`)

CLI:
```bash
socrata text-insights data.cityofnewyork.us h9gi-nx95 \
  --text-column borough --text-column contributing_factor_vehicle_1 \
  --geo-column location \
  --max-rows 50000 \
  --out tagged_rows.json
```

This command prints aggregate qualitative/quantitative text insights and can export rows enriched with `descriptive_tags`.


## Configuration Auto-Loading

The CLI now auto-loads `socrata_toolkit.config.json` from your current directory (or `~/.socrata_toolkit.config.json`) and uses defaults like `preferences.default_max_rows` for commands such as `analyze` and `text-insights`.


## CI / Developer Workflow

Install dev tooling:
```bash
pip install -e ".[dev]"
```

Run checks:
```bash
ruff check socrata_toolkit tests
mypy socrata_toolkit
pytest -q
```

GitHub Actions CI runs lint + type-check + tests across Python 3.10/3.11/3.12.

## Integration Test Scaffold

A `docker-compose.test.yml` is included for PostgreSQL and MongoDB.

```bash
docker compose -f docker-compose.test.yml up -d
export RUN_INTEGRATION=1
export PG_DSN="postgresql://postgres:postgres@localhost:54329/socrata"
export MONGO_URI="mongodb://localhost:27028"
pytest -q tests/test_integration_scaffold.py
```

## Pipeline Run Reports

`pipeline` now writes a JSON run report by default to:
- `outputs/pipeline_run_report.json`

Override path:
```bash
socrata pipeline ... --report-path outputs/my_run_report.json
```

## DOT Sidewalk Program Dashboards

Two dedicated dashboards are available in Streamlit:
1. **DOT Sidewalk Dashboard** — computes program KPIs from pulled tabular data:
   - Defect Density
   - Throughput Velocity
   - Burn Variance
   - First-Pass Yield
   - Rework Factor
2. **Code Export Studio** — exports reusable SQL + Python method templates aligned to planning/execution/audit responsibilities.

Run:
```bash
streamlit run socrata_toolkit/app.py
```

## DOT Analytical Method Mapping Implemented

- **Planning**: defect density and conflict-oriented templates.
- **Execution**: throughput and budget variance KPI computation.
- **Audit**: first-pass yield and rework factor quality indicators.
- **Text & qualitative**: NLP/regex tagging for correspondence or complaint-type text.


## llm_duck Integration (Local LLM + DuckDB-style Workflow)

The toolkit now includes `llm_duck`-style augmentation support:
- CLI command: `socrata llm-augment`
- Streamlit mode: **LLM Augmentation**
- Output columns: `llm_label`, `llm_confidence`, `llm_rationale`

Example:
```bash
socrata llm-augment data.cityofnewyork.us h9gi-nx95 \
  --text-column description \
  --endpoint http://localhost:1234/v1/chat/completions \
  --model local-model \
  --out llm_augmented.json
```

This is ideal for Sidewalk Program workflows such as complaint triage, conflict-risk tagging, and root-cause categorization.

## Geoinformatic Analysis Coverage

Supported geospatial methods now include:
- **Spatial intersects join** between two layers (WKT/GeoJSON geometry fields)
- **Conflict rate estimation** from intersect counts
- **DOT dashboard spatial conflict workflow** in Streamlit

CLI example:
```bash
socrata spatial-join \
  --left-json sidewalk_layer.json \
  --right-json dining_out_layer.json \
  --left-geom-col geometry \
  --right-geom-col geometry \
  --out spatial_join_output.json
```

This supports contract scope conflict analysis and geospatial planning screening.

## Advanced NLP Coverage

The toolkit now supports advanced NLP workflows through `NLP Studio` and `socrata nlp-analyze`:
- Text preprocessing: tokenization, stop-word removal, lightweight lemmatization/stemming fallback
- Information extraction: NER + POS tagging (spaCy-backed when available, rule-based fallback)
- Semantic analysis: sentiment scoring (TextBlob-backed when available, heuristic fallback)
- Output generation: summarization + optional translation (Transformers pipeline when available)

CLI:
```bash
socrata nlp-analyze --text "Sidewalk access is poor near transit hubs." --translate es
```

Library compatibility notes:
- NLTK / spaCy / Hugging Face Transformers / Gensim / TextBlob are optional integration targets.
- The system gracefully degrades to lightweight fallbacks if those libraries/models are unavailable.
