# ⚠️ ARCHIVED: Dash Application Reference

This document describes the legacy Dash-based application, which has been superseded by the Streamlit Mission Control dashboard.

## Current Application

**App entry point:** `app/app.py` (Streamlit)  
**Run command:** `streamlit run app/app.py` → `http://localhost:8501`  
**Deployment:** See `docs/DEPLOYMENT.md` for local, Docker, and cloud deployment  
**Configuration:** See `QUICKSTART.md` for setup and environment variables  

---

## Legacy Dash Architecture (Archived)

This section documents the previous Dash-based application for historical reference.

**Previous entry point:** `dash_app/app.py`  
**Previous data layer:** `dash_app/data/db.py`  
**Previous theme:** `dash_app/assets/theme.css` (dark / light / sepia)  
**Previous run:** `python dash_app/app.py` → `http://localhost:8050`

---

## Architecture

```
dash_app/
├── app.py              ← Dash server, sidebar layout, theme callback, router
├── data/
│   └── db.py           ← Thread-safe DuckDB singleton (threading.local)
├── pages/              ← Auto-discovered by Dash multi-page
│   ├── home.py         /
│   ├── analytics.py    /analytics
│   ├── geospatial.py   /geospatial
│   ├── governance.py   /governance
│   ├── soql.py         /soql
│   ├── pipeline.py     /pipeline
│   ├── ai.py           /ai
│   ├── tasks.py        /tasks
│   ├── quantum.py      /quantum
│   ├── engineering.py  /engineering
│   ├── export.py       /export
│   ├── reports.py      /reports
│   ├── settings.py     /settings
│   └── devtools.py     /devtools
└── assets/
    └── theme.css       ← CSS custom properties for all 3 themes
```

---

## Pages

### 🏠 Dashboard (`/`)
**File:** `pages/home.py`  
**Toolkit:** `pipeline.ingest_311_complaints`, `core.DuckDBManager`

- CSV / ZIP upload → auto-load to DuckDB
- Quick Start cards: NYC 311, Sidewalk Violations, Construction, DOT Permits
- DuckDB table browser with row counts
- Dataset preview (AG Grid)

### 📊 Analytics (`/analytics`)
**File:** `pages/analytics.py`  
**Toolkit:** `analysis.*`, `governance.compute_quality_score`

6-tab layout:

| Tab | Content |
|-----|---------|
| KPI Dashboard | `MetricsTracker` cards with trend indicators |
| Time Series | Plotly line chart by date column |
| Distribution | Histogram + box plot marginal |
| Correlation | Interactive heatmap |
| Text Analysis | Term frequency bar chart, regex hit counters |
| Anomaly Detection | Z-score flagged rows in AG Grid |

### 🗺️ Geospatial (`/geospatial`)
**File:** `pages/geospatial.py`  
**Toolkit:** `spatial.cluster_locations`, `spatial.detect_construction_conflicts`

3-tab layout:

| Tab | Content |
|-----|---------|
| Point Map | Mapbox scatter plot with borough color coding |
| Cluster Analysis | KMeans cluster map (k=5 default) |
| Density Heatmap | Plotly density_mapbox |

### ✅ Task Board (`/tasks`)
**File:** `pages/tasks.py`  
**Toolkit:** `engineering.Task`, `engineering.TaskBoard` (persisted in DuckDB)

- Kanban board: **Backlog → In Progress → Review → Done**
- Add task form (title, assignee, priority, category, borough, due date)
- Move task buttons (← →)
- DuckDB-backed persistence via `_task_board` table

### 🔄 Data Pipeline (`/pipeline`)
**File:** `pages/pipeline.py`  
**Toolkit:** `pipeline.*`, `cleaning.*`

4-tab layout:

| Tab | Content |
|-----|---------|
| Ingest | Socrata fetch with Dask parallel execution |
| CDC | Change detection between old/new DataFrame snapshots |
| Clean | Borough standardization, null removal, deduplication |
| Deduplicate | Key-column based dedupe |

### 🤖 AI Assistant (`/ai`)
**File:** `pages/ai.py`  
**Toolkit:** `ai.SocrataLLMChatbot`, `ai.SQLQueryEngine`

- Chat interface with conversation history
- NL→SQL translation with DuckDB execution
- Quick prompt dropdown
- Auto-detects LangChain availability

### ⚡ Quantum (`/quantum`)
**File:** `pages/quantum.py`  
**Toolkit:** `ai.quantum_search`, `ai.optimize_repair_route`, `ai.optimize_crew_assignment`

3-tab layout:

| Tab | Content |
|-----|---------|
| Grover Search | Dataset column search with circuit metrics |
| Route Optimizer | TSP route result + map |
| Crew Assignment | Round-robin crew assignment table |

### 🔬 Governance (`/governance`)
**File:** `pages/governance.py`  
**Toolkit:** `governance.*`, `analysis.compute_freshness_score`

- Quality scorecard (completeness, consistency, validity, freshness)
- Schema drift detection
- AG Grid table with sortable quality dimensions

### 🛠️ Engineering (`/engineering`)
**File:** `pages/engineering.py`  
**Toolkit:** `engineering.*`

4-tab layout:

| Tab | Content |
|-----|---------|
| Schema Registry | Dataset schema versioning viewer |
| Cost Estimator | Per-row cost estimation with borough multipliers |
| Contractor Scorecards | Contractor performance ranking |
| Data Profile | DuckDB `SUMMARIZE` output |

### ✨ SoQL Maestro (`/soql`)
**File:** `pages/soql.py`  
**Toolkit:** `core.SoQLBuilder`, `core.SocrataClient`

- SQL editor (CodeMirror-style textarea)
- Execute against DuckDB or Socrata directly
- Template library (GROUP BY, WHERE, aggregations)
- AG Grid results + auto-chart

### 📋 Reports (`/reports`)
**File:** `pages/reports.py`  
**Toolkit:** `analysis.generate_program_report`, `analysis.generate_contract_report`

- 5 report templates (Program KPI, Contract Status, Inquiry Response, Compliance, Data Profile)
- Markdown preview
- Download button

### 📤 Export (`/export`)
**File:** `pages/export.py`  
**Toolkit:** `pipeline.ExcelWorkbookBuilder`, `pipeline.export_for_tableau`

- Format selection: CSV, Parquet, JSON, Excel, SQL DDL, Markdown
- Table selector
- Download via `dcc.Download`

### 🔗 Dev Tools (`/devtools`)
**File:** `pages/devtools.py`  
**Toolkit:** `core.DuckDBManager` (direct)

- SQL REPL (multi-line textarea + Execute button)
- Schema browser accordion (all DuckDB tables → column names/types)
- DB Stats panel (table sizes, total rows)
- Dask cluster info

### ⚙️ Settings (`/settings`)
**File:** `pages/settings.py`  
**Toolkit:** All modules (health check)

- Dependency health check (DuckDB, Dask, LangChain, Shapely, etc.)
- Environment variable status (token presence)
- DB path and table count display

---

## `dash_app/data/db.py` — DuckDB Connection Layer

Thread-safe DuckDB singleton using `threading.local()`.

```python
from dash_app.data.db import get_conn, query_df, execute

conn = get_conn()                          # Per-thread connection
df = query_df("SELECT * FROM sidewalks LIMIT 100")
execute("INSERT INTO _task_board VALUES (?)", [task_dict])
```

**Fallback behavior:** If `nyc_dash.db` is locked by another process (common on Windows), automatically falls back to `:memory:` mode. Prevents crashes during development restarts.

### Key Functions

| Function | Description |
|----------|-------------|
| `get_conn()` | Get or create thread-local DuckDB connection |
| `query_df(sql, params)` | Execute SELECT → `pd.DataFrame` |
| `execute(sql, params)` | Execute INSERT/UPDATE/CREATE |
| `list_tables()` | List all DuckDB tables |

---

## Theme System

Themes are implemented as CSS custom properties in `dash_app/assets/theme.css`.

```python
# Switch theme via callback (in app.py)
@callback(
    Output("app-theme", "data-bs-theme"),
    Input("theme-radio", "value")
)
def switch_theme(theme):
    return theme  # "dark" | "light" | "sepia"
```

| Theme | Background | Text | Accent |
|-------|-----------|------|--------|
| `dark` | `#0f1117` | `#e8eaf6` | `#7c4dff` |
| `light` | `#f8f9fa` | `#212529` | `#0066cc` |
| `sepia` | `#f4ecd8` | `#3b2d1f` | `#8b5e3c` |
