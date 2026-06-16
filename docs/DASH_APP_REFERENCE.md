# Dash Application Reference — Mission Control (PRIMARY)

This document describes the **current primary Dash/FastAPI/Mantine UI application** — the production-grade Mission Control dashboard for NYC DOT analysts.

## Current Application (PRIMARY)

**App entry point:** `app/dash_app.py` (Dash/FastAPI + Plotly)  
**Run command:** `python app/dash_app.py` → `http://localhost:8011`  
**Backend:** FastAPI (async, production-grade)  
**UI Framework:** Dash 4.2 with Mantine components  
**Charts:** Plotly interactive visualizations  
**State Management:** dcc.Store for reactive updates  
**Deployment:** See `docs/MISSION_CONTROL.md` for local, Docker, and cloud deployment  
**Configuration:** See `QUICKSTART.md` for setup and environment variables  

## Alternative Application (SECONDARY)

**App entry point:** `app/app.py` (Streamlit)  
**Run command:** `streamlit run app/app.py` → `http://localhost:8501`  
**Use case:** Simplified data exploration (non-primary, alternative option)

---

## Current Architecture (Dash/FastAPI)

```
app/
├── dash_app.py                ← Main Dash app with FastAPI backend
├── dash_layouts.py            ← Page layouts and component definitions
├── dash_layouts_analytics_integration.py  ← Advanced analytics layouts
├── dash_layouts_gis.py        ← Geospatial dashboard layouts
├── callbacks/                 ← Real-time callback handlers (reactive updates)
│   ├── analytics.py           ← KPI and metric analytics callbacks
│   ├── analytics_integration.py← Advanced analytics integrations
│   ├── gis.py                 ← Spatial analysis callbacks
│   ├── export_callbacks.py    ← PDF/Excel/PPTX export pipelines
│   ├── visualization_callbacks.py ← Chart generation callbacks
│   ├── navigation.py          ← Page routing callbacks
│   └── ...
├── components/                ← Custom Dash component definitions
│   ├── filter_system.py       ← Interactive filter UI components
│   ├── kpi_cards.py           ← KPI metric card components
│   ├── spatial_map.py         ← Map visualization components
│   └── ...
├── assets/                    ← Static assets
│   ├── custom.css             ← Mantine theming and custom styles
│   ├── favicon.ico            ← Browser tab icon
│   └── ...
├── main.py                    ← Launcher shim (auto-selects primary Dash)
└── app.py                     ← SECONDARY: Streamlit alternative
```

### Data Flow

1. **Frontend (dcc.Graph, dcc.Store)** — User interacts with Plotly chart or filter
2. **Callback Handler (app/callbacks/*.py)** — Receives Input, processes data via `socrata_toolkit` library
3. **Data Layer (src/socrata_toolkit/)** — Fetches from DuckDB L2 cache or live Socrata API
4. **Response (Output)** — Returns updated Plotly figure or dcc.Store JSON
5. **Reactive Update** — Dash auto-updates dependent components in real-time

---

## Layouts & Pages

### Dashboard (Home)
**File:** `dash_layouts.py` — home page  
**Callbacks:** `callbacks/analytics.py`, `callbacks/visualization_callbacks.py`

- KPI cards with real-time metric updates
- Dataset health status summary
- Audit trail of recent ingests and updates
- Quick-action buttons

### Construction Lists
**File:** `dash_layouts.py` — construction view  
**Callbacks:** `callbacks/analytics.py`

- Borough-filtered interactive table
- Construction project details (cost, timeline, status)
- Drill-down drill-down capability

### GIS & Spatial Analysis
**File:** `dash_layouts_gis.py`  
**Callbacks:** `callbacks/gis.py`

- Interactive Plotly Scattermapbox (permit/inspection density)
- DBSCAN spatial clustering overlay
- Conflict buffer zones (permits vs. inspections)
- TSP route optimization visualization
- Animated borough bar charts

### Advanced Analytics
**File:** `dash_layouts_analytics_integration.py`  
**Callbacks:** `callbacks/analytics_integration.py`

- Bayesian SLA forecasting with credible intervals
- CUSUM control charts for process monitoring
- KMeans clustering visualizations
- Survival curves and time-to-event analysis
- Moran's I spatial autocorrelation tests
- Heatmaps and correlation matrices

### Contract Analytics
**File:** `dash_layouts.py` — contracts view  
**Callbacks:** `callbacks/analytics.py`

- Contractor performance metrics (productivity, cost/unit, timeliness)
- Spending patterns and budget tracking
- Gantt charts for timeline visualization
- Completion rates by borough

### Reports & Export
**File:** `dash_layouts.py` — reports view  
**Callbacks:** `callbacks/export_callbacks.py`

- PDF report generation (WeasyPrint)
- Excel export with Mantine-styled tables (openpyxl)
- PPTX slide deck generation (python-pptx)
- Filtered exports by borough/date range/status

---

## Callback System

Callbacks connect UI inputs to data processing and output generation.

```python
# Example: analytics.py — KPI update on borough filter change
from dash import callback, Input, Output
import plotly.graph_objects as go

@callback(
    Output("kpi-metrics", "children"),
    Input("borough-filter", "value")
)
def update_kpis(selected_borough):
    # Fetch metrics from socrata_toolkit
    data = fetch_metrics(borough=selected_borough)
    # Return Mantine KPI card components
    return render_kpi_cards(data)
```

### Key Callback Files

| File | Purpose |
|------|---------|
| `callbacks/analytics.py` | KPI metrics, time-series, distribution charts |
| `callbacks/gis.py` | Spatial visualizations, maps, conflict detection |
| `callbacks/export_callbacks.py` | PDF/Excel/PPTX generation |
| `callbacks/visualization_callbacks.py` | Plotly figure generation and updates |
| `callbacks/navigation.py` | Page routing and sidebar navigation |

---

## Data Layer Integration

Callbacks access data via the `socrata_toolkit` library:

```python
from socrata_toolkit.core.client import SocrataClient
from socrata_toolkit.analysis.metrics import compute_quality_score

# Fetch live data from Socrata or L2 DuckDB cache
client = SocrataClient(config)
df = client.fetch_dataframe("data.cityofnewyork.us", "fourfour", max_rows=50000)

# Analyze with core toolkit
score = compute_quality_score(df, key_columns=["id"])
```

For local caching and performance:
```python
from socrata_toolkit.core.duckdb_store import query_parquet_cache

# Query L2 DuckDB cache (Parquet files)
df = query_parquet_cache("inspection", filters={"borough": ["MN"]})
```

---

## UI Components (Mantine + Dash)

Layouts use Mantine component library wrapped in Dash:

```python
from dash_mantine_components import Stack, Group, Button, Select, Card
import dash_core_components as dcc
import dash_html_components as html

layout = Stack([
    Group([
        Select(id="borough-filter", placeholder="Select borough..."),
        Button("Apply Filters", id="filter-btn")
    ]),
    Card(dcc.Graph(id="metric-chart")),
])
```

**Styling:** `app/assets/custom.css` provides Mantine-compatible color schemes and responsive layouts.

---

## Environment & Configuration

See `QUICKSTART.md` for full setup. Key variables:

```bash
# .env
SOCRATA_APP_TOKEN=your_token_here
ANTHROPIC_API_KEY=your_claude_key  (for NL-to-SoQL)
MISSION_DEMO=0                     (1 = demo mode, no API calls)
DUCKDB_PATH=data/local_db/nyc_mission_control.duckdb
```

**FastAPI Configuration:**
- Host: `127.0.0.1` (localhost)
- Port: `8011` (default; set `DASH_PORT=8012` to override)
- Debug: auto-reload enabled in dev mode

---

## Common Tasks

### Add a New Plotly Chart
1. Create callback in `callbacks/visualization_callbacks.py`
2. Define layout component in `dash_layouts.py` (dcc.Graph with id)
3. Register @callback with Input (filter) and Output (figure)
4. Return Plotly figure from socrata_toolkit.viz

### Add a New Filter / Interactive Control
1. Add dcc.Dropdown/Select/DatePickerRange to layout
2. Create callback that listens to the control's `value`
3. Update dependent charts via Output

### Integrate a New Socrata Dataset
1. Add dataset metadata to `config/datasets.yaml`
2. Extend SocrataClient to fetch it: `client.fetch_dataframe(...)`
3. Create visualization/analysis callback that uses the data
4. Test with `MISSION_DEMO=1 python app/dash_app.py`
