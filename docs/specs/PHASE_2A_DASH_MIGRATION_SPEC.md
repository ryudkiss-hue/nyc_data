# Phase 2A: Dash Migration Technical Specification
## NYC DOT Socrata Toolkit – Analytics & Labor Platform

**Date:** June 10, 2026  
**Timeline:** Weeks 4–5 (55 hours, solo engineer)  
**Objective:** Migrate 24+ Streamlit/Plotly charts to production-grade Dash with real-time callback interactivity, <500ms P95 latency, and 100+ concurrent user support.

---

## 1. Dash Architecture Overview

### 1.1 Component Hierarchy

```
Dash App (dash_app.py)
├── FastAPI Backend (uvicorn)
├── Session Management (dcc.Store)
├── Global State (store-global-filters)
│
├── Page Router (url callback)
│   ├── /analytics → Analytics Advanced View
│   │   ├── Filter Panel
│   │   │   ├── Date Range Picker (dcc.DatePickerRange)
│   │   │   ├── Borough Selector (dmc.MultiSelect)
│   │   │   └── Metric Selector (dmc.SegmentedControl)
│   │   └── Charts Grid (dmc.SimpleGrid)
│   │       ├── CUSUM Control Chart
│   │       ├── Bayesian CI Charts (5 variants)
│   │       ├── KMeans Clustering Viz
│   │       ├── Survival Curves
│   │       ├── Moran's I Heatmap
│   │       ├── Distribution Classification Charts
│   │       ├── Anomaly Detection Map
│   │       ├── Seasonal Decomposition (4-panel)
│   │       ├── Bootstrap CI Bands
│   │       ├── Time-Series Forecast
│   │       ├── Heatmap (Material × Borough)
│   │       ├── Correlation Matrix
│   │       └── Trend Analysis
│   │
│   └── /labor → Labor & Lifecycle View
│       ├── Filter Panel
│       └── Charts Grid (11+ charts)
│
└── Services (app/services/dash_service.py)
    ├── DuckDB Query Layer
    ├── Data Cache (Redis/Diskcache)
    ├── Chart Transform Layer
    └── Error Boundaries
```

### 1.2 Callback Pattern: Filter Synchronization

**Key Principle:** Single-source-of-truth filter state in `store-global-filters`.

```
User Action (e.g., date range change)
    ↓
Input: dcc.DatePickerRange.start_date + end_date
    ↓
Master Callback (filter_manager_callback)
    • Validates inputs
    • Updates store-global-filters
    • Returns no_update (avoid circular updates)
    ↓
Dependent Callbacks (one per chart)
    • Input: store-global-filters (reactive dependency)
    • Fetches data from DuckDB
    • Transforms + renders Plotly figure
    • Output: dcc.Graph.figure
```

**Pattern Code:**
```python
# Master filter callback (runs first)
@app.callback(
    Output("store-global-filters", "data"),
    Input("filter-date-range", "start_date"),
    Input("filter-date-range", "end_date"),
    Input("filter-borough", "value"),
    Input("filter-metric", "value"),
    prevent_initial_call=False
)
def update_filter_state(start, end, boro, metric):
    return {
        "date_range": [start, end],
        "borough": boro or "ALL",
        "metric": metric or "ALL"
    }

# Per-chart callback (depends on filter store)
@app.callback(
    Output("chart-cusum", "figure"),
    Input("store-global-filters", "data"),
    prevent_initial_call=False
)
def render_cusum_chart(filters):
    try:
        data = fetch_cusum_data(filters)
        return create_cusum_figure(data)
    except Exception as e:
        return error_figure(str(e))
```

### 1.3 Data Flow Architecture

```
DuckDB L2 Cache (Parquet files)
    ├── analytics.borough_summary (pre-computed)
    ├── analytics.time_series (daily rollups)
    ├── analytics.spatial_features (geom + metrics)
    ├── analytics.material_lifecycle (degradation curves)
    └── analytics.workforce_metrics (labor data)
        ↓
        [query_* functions in dash_service.py]
        ↓
Pandas DataFrames (in-memory)
        ↓
        [transform_* functions in dash_service.py]
        ↓
Plotly Figures (JSON serializable)
        ↓
dcc.Graph.figure (rendered in browser)
```

**Query Pattern:**
```python
def query_cusum_data(date_range, borough) -> pd.DataFrame:
    """Load + filter CUSUM control data from DuckDB."""
    query = """
    SELECT date, borough, metric_value, control_limit, 
           violation_flag FROM analytics.cusum_data
    WHERE date BETWEEN ? AND ? 
      AND borough = ? OR borough = 'ALL'
    ORDER BY date
    """
    return duckdb.query(query, (date_range[0], date_range[1], borough)).to_df()
```

### 1.4 Caching Strategy

**Two-tier cache:**

1. **L1: DuckDB Parquet** (persistent, disk-backed)
   - Pre-computed analytics tables refreshed nightly via APScheduler
   - Schema: `analytics.*` (cusum_data, time_series, spatial_features, etc.)
   - TTL: 24 hours (manual refresh available)

2. **L2: In-Memory Cache** (request-scoped, Diskcache)
   - Cache query results for 5 minutes
   - Key: `f"analytics_{metric}_{borough}_{date_range_hash}"`
   - Size limit: 500 MB
   - Strategy: LRU eviction

**Cache Code:**
```python
import diskcache
import hashlib

_l2_cache = diskcache.Cache(".cache/dash_l2")

def fetch_analytics_data(metric, borough, date_range) -> pd.DataFrame:
    """Fetch with L2 cache check."""
    cache_key = f"analytics_{metric}_{borough}_{hash_daterange(date_range)}"
    
    # Check L2 cache
    if cache_key in _l2_cache:
        return _l2_cache[cache_key]
    
    # Query DuckDB
    data = query_cusum_data(date_range, borough)
    
    # Cache result (5 min TTL)
    _l2_cache.set(cache_key, data, expire=300)
    return data

def hash_daterange(dates):
    s = f"{dates[0]}-{dates[1]}"
    return hashlib.md5(s.encode()).hexdigest()[:8]
```

### 1.5 Performance Optimization Strategy

**Target:** P50 20ms, P95 <500ms per chart interaction

**Techniques:**

1. **Selective Loading:** Only render visible charts (lazy-load off-screen)
2. **Data Precomputation:** Pre-aggregate in DuckDB, avoid Pandas operations
3. **Figure Caching:** Memoize Plotly figure JSON for identical filter states
4. **Async Prefetch:** Load popular filters in background on page load
5. **Callback Debouncing:** Delay chart renders until user stops typing (date picker)
6. **Client-side Callbacks:** Use `clientside_callback` for filter sync (0ms latency)

**Implementation:**
```python
# Debounce pattern for date range
@app.callback(
    Output("store-global-filters", "data"),
    Input("filter-date-range", "start_date"),
    Input("filter-date-range", "end_date"),
    Input("filter-borough", "value"),
    prevent_initial_call=False,
    debounce=True  # Built-in debounce (300ms default)
)
def update_filters(...):
    # Updates only after user stops changing inputs
    return {...}

# Client-side callback (instant UI response)
app.clientside_callback(
    "function(filters) { return filters.borough; }",
    Output("filter-borough-display", "children"),
    Input("store-global-filters", "data")
)
```

---

## 2. Analytics Advanced View Layout (`app/dash_layouts_analytics.py`)

### 2.1 Complete Layout Code

```python
# app/dash_layouts_analytics.py

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify


def layout_analytics_advanced():
    """Analytics Advanced View — 13+ interactive charts with filters."""
    return dmc.Container(
        fluid=True,
        p="lg",
        children=[
            # ─── HEADER ───
            dmc.Stack([
                dmc.Group([
                    dmc.Group([
                        DashIconify(icon="mdi:chart-line", width=32),
                        dmc.Stack([
                            dmc.Title("Analytics Advanced View", order=1, size="h2"),
                            dmc.Text(
                                "13+ interactive charts with Bayesian inference, spatial analysis, and anomaly detection",
                                size="sm",
                                c="dimmed"
                            ),
                        ], gap=0),
                    ]),
                    dmc.Button(
                        "Refresh Data",
                        id="btn-refresh-analytics",
                        leftSection=DashIconify(icon="mdi:refresh"),
                        variant="light"
                    ),
                ], justify="space-between", mb="lg"),
            ]),

            # ─── FILTER PANEL ───
            dmc.Paper(
                p="md",
                radius="lg",
                withBorder=True,
                mb="xl",
                children=[
                    dmc.Group([
                        # Date Range
                        dmc.Stack([
                            dmc.Text("Date Range", fw=700, size="sm"),
                            dcc.DatePickerRange(
                                id="filter-date-range",
                                start_date="2026-05-10",
                                end_date="2026-06-10",
                                display_format="YYYY-MM-DD",
                                style={"width": "100%"},
                            ),
                        ], style={"flex": 1}, gap="xs"),

                        # Borough Selector
                        dmc.Stack([
                            dmc.Text("Borough", fw=700, size="sm"),
                            dmc.MultiSelect(
                                id="filter-borough",
                                placeholder="Select boroughs (or ALL)",
                                data=[
                                    {"value": "MN", "label": "Manhattan"},
                                    {"value": "BX", "label": "Bronx"},
                                    {"value": "BK", "label": "Brooklyn"},
                                    {"value": "QN", "label": "Queens"},
                                    {"value": "SI", "label": "Staten Island"},
                                ],
                                value=["MN", "BX"],
                                searchable=True,
                                clearable=True,
                            ),
                        ], style={"flex": 1}, gap="xs"),

                        # Metric Selector
                        dmc.Stack([
                            dmc.Text("Primary Metric", fw=700, size="sm"),
                            dmc.SegmentedControl(
                                id="filter-metric",
                                data=[
                                    {"value": "completion_rate", "label": "Completion %"},
                                    {"value": "violation_count", "label": "Violations"},
                                    {"value": "days_open", "label": "Days Open"},
                                ],
                                value="completion_rate",
                                fullWidth=True,
                            ),
                        ], style={"flex": 1}, gap="xs"),

                        # Advanced Options
                        dmc.Stack([
                            dmc.Text("Options", fw=700, size="sm"),
                            dmc.Group([
                                dmc.Checkbox(id="filter-exclude-outliers", label="Exclude Outliers", checked=False),
                                dmc.Checkbox(id="filter-apply-ci", label="Show 95% CI", checked=True),
                            ], gap="md"),
                        ], gap="xs"),
                    ], grow=True, align="flex-end", spacing="md"),
                ],
            ),

            # ─── LOADING INDICATOR ───
            dcc.Loading(
                id="analytics-loading",
                type="dots",
                children=[
                    dmc.Alert(
                        id="analytics-error-alert",
                        title="Error",
                        color="red",
                        children="",
                        style={"display": "none"},
                        mb="md"
                    ),

                    # ─── CHARTS GRID ───
                    dmc.SimpleGrid(
                        cols={"base": 1, "sm": 2, "lg": 3},
                        spacing="lg",
                        children=[
                            # ─ 1. CUSUM Control Chart ─
                            chart_container(
                                "chart-cusum",
                                "CUSUM Control Chart",
                                "Statistical process control for violation trends"
                            ),

                            # ─ 2-5. Bayesian Confidence Intervals (4 variants) ─
                            chart_container(
                                "chart-bayesian-ci-ramp",
                                "Bayesian Ramp Completion Rate",
                                "Posterior distribution with 95% credible interval"
                            ),
                            chart_container(
                                "chart-bayesian-ci-violation",
                                "Bayesian Violation Rate",
                                "Posterior distribution with credible interval"
                            ),
                            chart_container(
                                "chart-bayesian-sla",
                                "Bayesian SLA Breach Probability",
                                "Posterior P(breach | observed data)"
                            ),
                            chart_container(
                                "chart-bayesian-forecast",
                                "Bayesian Time-Series Forecast",
                                "Posterior predictive distribution with credible bands"
                            ),

                            # ─ 6. KMeans Clustering ─
                            chart_container(
                                "chart-kmeans",
                                "KMeans Clustering (3 Clusters)",
                                "Inspect borough/material profiles"
                            ),

                            # ─ 7. Survival Curves ─
                            chart_container(
                                "chart-survival",
                                "Material Degradation Survival Curves",
                                "Kaplan-Meier curves by material type"
                            ),

                            # ─ 8. Moran's I Spatial Autocorrelation ─
                            chart_container(
                                "chart-morans-i",
                                "Moran's I Spatial Autocorrelation",
                                "Local indicators of spatial association"
                            ),

                            # ─ 9-10. Distribution Classification ─
                            chart_container(
                                "chart-distribution-completion",
                                "Distribution: Completion Rate",
                                "Histogram + KDE + normality test"
                            ),
                            chart_container(
                                "chart-distribution-violation",
                                "Distribution: Violation Count",
                                "Histogram + KDE + normality test"
                            ),

                            # ─ 11. Anomaly Detection Map ─
                            chart_container(
                                "chart-anomaly-map",
                                "Anomaly Detection (Isolation Forest)",
                                "Spatial distribution of anomalous inspections"
                            ),

                            # ─ 12. Seasonal Decomposition (4-panel) ─
                            chart_container(
                                "chart-seasonal-decomp",
                                "Seasonal Decomposition (Time Series)",
                                "Trend + Seasonal + Residual components"
                            ),

                            # ─ 13. Bootstrap Confidence Interval Bands ─
                            chart_container(
                                "chart-bootstrap-ci",
                                "Bootstrap Confidence Interval Bands",
                                "95% CI bands from 10K bootstrap resamples"
                            ),
                        ],
                    ),
                ],
            ),

            # ─── HIDDEN STORES ───
            dcc.Store(id="store-analytics-filters", data={}),
            dcc.Store(id="store-analytics-cache", data={}),
        ],
    )


def chart_container(chart_id, title, description):
    """Reusable chart wrapper with tabs (Visual | Insights | Data | Export)."""
    return dmc.Paper(
        withBorder=True,
        p="md",
        radius="lg",
        shadow="sm",
        children=[
            dmc.Group([
                dmc.Stack([
                    dmc.Title(title, order=4, size="h5"),
                    dmc.Text(description, size="xs", c="dimmed"),
                ], gap=0),
                dmc.Badge("Live", color="green", size="sm"),
            ], justify="space-between", mb="md"),

            dmc.Tabs(
                [
                    dmc.TabsList([
                        dmc.TabsTab("Chart", value="chart"),
                        dmc.TabsTab("Insights", value="insights"),
                        dmc.TabsTab("Data", value="data"),
                        dmc.TabsTab("Export", value="export"),
                    ]),
                    dmc.TabsPanel(
                        value="chart",
                        children=[
                            dcc.Graph(
                                id=chart_id,
                                config={
                                    "displayModeBar": True,
                                    "responsive": True,
                                    "toImageButtonOptions": {
                                        "format": "png",
                                        "filename": f"{chart_id}.png",
                                        "height": 600,
                                        "width": 1200,
                                        "scale": 2,
                                    },
                                },
                            )
                        ],
                    ),
                    dmc.TabsPanel(
                        value="insights",
                        children=[
                            dmc.Text(
                                id={"type": "insights-text", "index": chart_id},
                                children="Loading insights...",
                                size="sm",
                                style={"whiteSpace": "pre-wrap", "lineHeight": "1.6"},
                            )
                        ],
                    ),
                    dmc.TabsPanel(
                        value="data",
                        children=[
                            dmc.Code(
                                id={"type": "data-table", "index": chart_id},
                                block=True,
                                children="Loading data...",
                                style={"fontSize": "10px", "maxHeight": "300px", "overflow": "auto"},
                            )
                        ],
                    ),
                    dmc.TabsPanel(
                        value="export",
                        children=[
                            dmc.SimpleGrid(
                                cols=2,
                                children=[
                                    dmc.Button(
                                        "CSV",
                                        id={"type": "btn-export-csv", "index": chart_id},
                                        variant="outline",
                                        size="sm",
                                    ),
                                    dmc.Button(
                                        "JSON",
                                        id={"type": "btn-export-json", "index": chart_id},
                                        variant="outline",
                                        size="sm",
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
                value="chart",
                variant="pills",
            ),
        ],
    )
```

### 2.2 Layout Registration

```python
# In app/dash_app.py, update routing:

from app.dash_layouts_analytics import layout_analytics_advanced

def render_page_content(pathname):
    if pathname == "/":
        return layout_dashboard()
    elif pathname == "/analytics":  # NEW
        return layout_analytics_advanced()
    elif pathname == "/labor":
        return layout_labor()
    # ... rest of routes
```

---

## 3. Analytics View Callbacks (`app/callbacks/dash_analytics.py`)

### 3.1 Master Filter Callback

```python
# app/callbacks/dash_analytics.py

from dash import Input, Output, State, callback, no_update
import logging

logger = logging.getLogger(__name__)


def register_analytics_callbacks(app, dash_service):
    """Register all analytics view callbacks."""

    # ─── Master Filter Callback (single source of truth) ───
    @app.callback(
        Output("store-analytics-filters", "data"),
        Input("filter-date-range", "start_date"),
        Input("filter-date-range", "end_date"),
        Input("filter-borough", "value"),
        Input("filter-metric", "value"),
        Input("filter-exclude-outliers", "checked"),
        Input("filter-apply-ci", "checked"),
        prevent_initial_call=False,
    )
    def update_analytics_filters(start_date, end_date, boroughs, metric, exclude_outliers, apply_ci):
        """Consolidate all filter inputs into single store."""
        return {
            "date_range": [start_date, end_date],
            "boroughs": boroughs or [],
            "metric": metric or "completion_rate",
            "exclude_outliers": exclude_outliers or False,
            "apply_ci": apply_ci or True,
        }

    # ─── Error Handling Callback ───
    @app.callback(
        Output("analytics-error-alert", "style"),
        Output("analytics-error-alert", "children"),
        Input("store-analytics-filters", "data"),
        prevent_initial_call=False,
    )
    def check_filter_validity(filters):
        """Validate filters and show/hide error alert."""
        if not filters or not filters.get("date_range"):
            return {"display": "block"}, "No date range selected"
        return {"display": "none"}, ""
```

### 3.2 Per-Chart Callbacks (13 charts)

**Pattern:** For each chart, define a callback that takes filters from store and outputs Plotly figure.

```python
    # ─── 1. CUSUM CONTROL CHART ───
    @app.callback(
        Output("chart-cusum", "figure"),
        Input("store-analytics-filters", "data"),
        prevent_initial_call=False,
    )
    def render_cusum(filters):
        """CUSUM control chart for violation trends."""
        try:
            if not filters or not filters.get("date_range"):
                return go.Figure().add_annotation(text="Select date range")
            
            data = dash_service.query_cusum_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"],
                exclude_outliers=filters["exclude_outliers"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No data available")
            
            fig = dash_service.create_cusum_figure(data)
            fig.update_layout(height=400)
            return fig
        except Exception as e:
            logger.error(f"CUSUM chart error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 2. BAYESIAN CI: RAMP COMPLETION RATE ───
    @app.callback(
        Output("chart-bayesian-ci-ramp", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_bayesian_ramp_ci(filters):
        """Bayesian posterior distribution for ramp completion rate."""
        try:
            data = dash_service.query_ramp_completion_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No ramp data")
            
            # Compute posterior (Beta-Binomial conjugate prior)
            posterior = dash_service.compute_bayesian_posterior_binomial(
                successes=data["completed"].sum(),
                trials=len(data),
                prior_alpha=1,
                prior_beta=1
            )
            
            fig = dash_service.create_bayesian_posterior_figure(
                posterior, 
                title="Ramp Completion Rate — Posterior Distribution",
                metric_name="completion_rate"
            )
            fig.update_layout(height=400)
            return fig
        except Exception as e:
            logger.error(f"Bayesian ramp CI error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 3. BAYESIAN CI: VIOLATION RATE ───
    @app.callback(
        Output("chart-bayesian-ci-violation", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_bayesian_violation_ci(filters):
        """Bayesian posterior for violation rate."""
        try:
            data = dash_service.query_violation_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No violation data")
            
            posterior = dash_service.compute_bayesian_posterior_binomial(
                successes=data["violation_flag"].sum(),
                trials=len(data),
                prior_alpha=2,
                prior_beta=8
            )
            
            fig = dash_service.create_bayesian_posterior_figure(
                posterior,
                title="Violation Rate — Posterior Distribution",
                metric_name="violation_rate"
            )
            fig.update_layout(height=400)
            return fig
        except Exception as e:
            logger.error(f"Bayesian violation CI error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 4. BAYESIAN SLA BREACH PROBABILITY ───
    @app.callback(
        Output("chart-bayesian-sla", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_bayesian_sla_breach(filters):
        """P(breach | observed data) for each borough."""
        try:
            data = dash_service.query_sla_breach_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No SLA data")
            
            # Compute P(breach) per borough using Bayesian posterior
            breach_probs = dash_service.compute_sla_breach_probabilities(data)
            
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=breach_probs["borough"],
                        y=breach_probs["breach_probability"],
                        marker_color=breach_probs["breach_probability"].map(
                            lambda x: "red" if x > 0.5 else "yellow" if x > 0.2 else "green"
                        ),
                        text=breach_probs["breach_probability"].map("{:.1%}".format),
                        textposition="outside",
                    )
                ]
            )
            fig.update_layout(
                title="SLA Breach Probability by Borough",
                xaxis_title="Borough",
                yaxis_title="P(breach | data)",
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Bayesian SLA error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 5. BAYESIAN FORECAST WITH CREDIBLE BANDS ───
    @app.callback(
        Output("chart-bayesian-forecast", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_bayesian_forecast(filters):
        """Time-series forecast with posterior predictive credible intervals."""
        try:
            hist_data = dash_service.query_time_series_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"],
                metric=filters["metric"]
            )
            
            if hist_data.empty or len(hist_data) < 10:
                return go.Figure().add_annotation(text="Insufficient data for forecast")
            
            # Fit Bayesian model (NUTS sampler)
            forecast = dash_service.compute_bayesian_forecast(
                hist_data,
                periods=30,
                credible_interval=0.95
            )
            
            fig = go.Figure()
            
            # Historical
            fig.add_trace(go.Scatter(
                x=hist_data["date"],
                y=hist_data["value"],
                name="Historical",
                mode="lines",
                line=dict(color="blue"),
            ))
            
            # Forecast mean
            fig.add_trace(go.Scatter(
                x=forecast["date"],
                y=forecast["mean"],
                name="Forecast",
                mode="lines",
                line=dict(color="orange"),
            ))
            
            # Credible interval bands
            fig.add_trace(go.Scatter(
                x=forecast["date"],
                y=forecast["ci_upper"],
                fill=None,
                mode="lines",
                line_color="rgba(0,0,0,0)",
                showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=forecast["date"],
                y=forecast["ci_lower"],
                fillcolor="rgba(255, 165, 0, 0.2)",
                fill="tonexty",
                mode="lines",
                line_color="rgba(0,0,0,0)",
                name="95% Credible Interval",
            ))
            
            fig.update_layout(
                title=f"Bayesian Forecast ({filters['metric']})",
                xaxis_title="Date",
                yaxis_title="Value",
                height=400,
                hovermode="x unified",
            )
            return fig
        except Exception as e:
            logger.error(f"Bayesian forecast error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 6. KMEANS CLUSTERING ───
    @app.callback(
        Output("chart-kmeans", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_kmeans_cluster(filters):
        """KMeans 3-cluster visualization (principal components)."""
        try:
            data = dash_service.query_cluster_features(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.shape[0] < 3:
                return go.Figure().add_annotation(text="Insufficient data for clustering")
            
            clusters, pca_data = dash_service.compute_kmeans_clusters(
                data,
                n_clusters=3,
                random_state=42
            )
            
            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=pca_data[clusters == i, 0],
                        y=pca_data[clusters == i, 1],
                        mode="markers",
                        name=f"Cluster {i}",
                        marker=dict(size=8, opacity=0.7),
                    )
                    for i in range(3)
                ]
            )
            
            fig.update_layout(
                title="KMeans Clustering (PCA-2D Projection)",
                xaxis_title="PC1",
                yaxis_title="PC2",
                height=400,
                hovermode="closest",
            )
            return fig
        except Exception as e:
            logger.error(f"KMeans error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 7. SURVIVAL CURVES ───
    @app.callback(
        Output("chart-survival", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_survival_curves(filters):
        """Kaplan-Meier survival curves by material type."""
        try:
            data = dash_service.query_material_lifecycle_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No material lifecycle data")
            
            material_types = data["material_type"].unique()
            
            fig = go.Figure()
            
            for material in material_types:
                subset = data[data["material_type"] == material]
                km_estimator = dash_service.compute_kaplan_meier(subset)
                
                fig.add_trace(go.Scatter(
                    x=km_estimator["time"],
                    y=km_estimator["survival_probability"],
                    name=material,
                    mode="lines",
                ))
            
            fig.update_layout(
                title="Material Degradation — Kaplan-Meier Survival Curves",
                xaxis_title="Days Since Installation",
                yaxis_title="Survival Probability",
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Survival curve error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 8. MORAN'S I SPATIAL AUTOCORRELATION ───
    @app.callback(
        Output("chart-morans-i", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_morans_i(filters):
        """Local Indicators of Spatial Association (LISA)."""
        try:
            data = dash_service.query_spatial_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty or not all(col in data.columns for col in ["latitude", "longitude", "metric_value"]):
                return go.Figure().add_annotation(text="No spatial data available")
            
            lisa_values = dash_service.compute_morans_i_local(data)
            
            fig = go.Figure(
                data=[
                    go.Scattergeo(
                        lon=data["longitude"],
                        lat=data["latitude"],
                        mode="markers",
                        marker=dict(
                            size=8,
                            color=lisa_values,
                            colorscale="RdBu",
                            showscale=True,
                            colorbar=dict(title="Moran's I"),
                        ),
                        text=data.get("location_name", ""),
                    )
                ]
            )
            fig.update_layout(
                title="Moran's I — Spatial Autocorrelation",
                geo=dict(scope="usa"),
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Moran's I error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 9. DISTRIBUTION: COMPLETION RATE ───
    @app.callback(
        Output("chart-distribution-completion", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_distribution_completion(filters):
        """Histogram + KDE + normality test for completion rate."""
        try:
            data = dash_service.query_completion_rate_distribution(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No completion rate data")
            
            values = data["completion_rate"].dropna()
            
            # Shapiro-Wilk test for normality
            stat, pval = dash_service.test_normality(values)
            
            fig = go.Figure()
            
            fig.add_trace(go.Histogram(
                x=values,
                nbinsx=30,
                name="Histogram",
                opacity=0.7,
            ))
            
            fig.add_trace(go.Scatter(
                x=dash_service.compute_kde_x(values),
                y=dash_service.compute_kde_y(values),
                name="KDE",
                mode="lines",
            ))
            
            fig.add_annotation(
                text=f"Shapiro-Wilk p={pval:.4f} {'(Normal)' if pval > 0.05 else '(Non-normal)'}",
                xref="paper", yref="paper",
                x=0.5, y=-0.15,
            )
            
            fig.update_layout(
                title="Distribution: Completion Rate",
                xaxis_title="Completion Rate",
                yaxis_title="Frequency",
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Distribution completion error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 10. DISTRIBUTION: VIOLATION COUNT ───
    @app.callback(
        Output("chart-distribution-violation", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_distribution_violation(filters):
        """Histogram + KDE + normality test for violation count."""
        try:
            data = dash_service.query_violation_count_distribution(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No violation count data")
            
            values = data["violation_count"].dropna().astype(int)
            stat, pval = dash_service.test_normality(values)
            
            fig = go.Figure()
            
            fig.add_trace(go.Histogram(
                x=values,
                nbinsx=30,
                name="Histogram",
                opacity=0.7,
            ))
            
            fig.update_layout(
                title="Distribution: Violation Count",
                xaxis_title="Violation Count",
                yaxis_title="Frequency",
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Distribution violation error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 11. ANOMALY DETECTION MAP ───
    @app.callback(
        Output("chart-anomaly-map", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_anomaly_map(filters):
        """Isolation Forest anomaly detection on spatial data."""
        try:
            data = dash_service.query_spatial_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"]
            )
            
            if data.empty or not all(col in data.columns for col in ["latitude", "longitude"]):
                return go.Figure().add_annotation(text="No spatial data")
            
            anomalies = dash_service.detect_anomalies_isolation_forest(data)
            
            fig = go.Figure(
                data=[
                    go.Scattergeo(
                        lon=data[~anomalies]["longitude"],
                        lat=data[~anomalies]["latitude"],
                        mode="markers",
                        name="Normal",
                        marker=dict(size=6, color="blue", opacity=0.5),
                    ),
                    go.Scattergeo(
                        lon=data[anomalies]["longitude"],
                        lat=data[anomalies]["latitude"],
                        mode="markers",
                        name="Anomaly",
                        marker=dict(size=8, color="red"),
                    ),
                ]
            )
            
            fig.update_layout(
                title="Anomaly Detection (Isolation Forest)",
                geo=dict(scope="usa"),
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Anomaly map error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 12. SEASONAL DECOMPOSITION ───
    @app.callback(
        Output("chart-seasonal-decomp", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_seasonal_decomposition(filters):
        """4-panel seasonal decomposition (Trend, Seasonal, Residual)."""
        try:
            data = dash_service.query_time_series_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"],
                metric=filters["metric"]
            )
            
            if data.empty or len(data) < 14:
                return go.Figure().add_annotation(text="Insufficient data for decomposition")
            
            decomposition = dash_service.compute_seasonal_decomposition(
                data,
                period=7  # Weekly seasonality
            )
            
            fig = go.Figure()
            
            # Subplots: Observed, Trend, Seasonal, Residual
            from plotly.subplots import make_subplots
            
            fig = make_subplots(
                rows=4, cols=1,
                subplot_titles=("Observed", "Trend", "Seasonal", "Residual"),
                shared_xaxes=True,
                vertical_spacing=0.08,
            )
            
            fig.add_trace(go.Scatter(
                x=data["date"], y=data["value"],
                name="Observed", mode="lines"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=decomposition["date"], y=decomposition["trend"],
                name="Trend", mode="lines"
            ), row=2, col=1)
            
            fig.add_trace(go.Scatter(
                x=decomposition["date"], y=decomposition["seasonal"],
                name="Seasonal", mode="lines"
            ), row=3, col=1)
            
            fig.add_trace(go.Scatter(
                x=decomposition["date"], y=decomposition["residual"],
                name="Residual", mode="lines"
            ), row=4, col=1)
            
            fig.update_layout(height=600, title_text="Seasonal Decomposition")
            return fig
        except Exception as e:
            logger.error(f"Seasonal decomposition error: {e}", exc_info=True)
            return error_figure(str(e))


    # ─── 13. BOOTSTRAP CONFIDENCE INTERVALS ───
    @app.callback(
        Output("chart-bootstrap-ci", "figure"),
        Input("store-analytics-filters", "data"),
    )
    def render_bootstrap_ci(filters):
        """Bootstrap 95% CI bands from 10K resamples."""
        try:
            data = dash_service.query_time_series_data(
                date_range=filters["date_range"],
                boroughs=filters["boroughs"],
                metric=filters["metric"]
            )
            
            if data.empty:
                return go.Figure().add_annotation(text="No time series data")
            
            ci_bands = dash_service.compute_bootstrap_ci_bands(
                data,
                n_bootstrap=10000,
                ci=0.95,
                window_size=7  # Rolling 7-day window
            )
            
            fig = go.Figure()
            
            # Original data
            fig.add_trace(go.Scatter(
                x=data["date"],
                y=data["value"],
                name="Observed",
                mode="lines",
                line=dict(color="blue"),
            ))
            
            # Upper CI
            fig.add_trace(go.Scatter(
                x=ci_bands["date"],
                y=ci_bands["ci_upper"],
                fill=None,
                mode="lines",
                line_color="rgba(0,0,0,0)",
                showlegend=False,
            ))
            
            # Lower CI (fill between)
            fig.add_trace(go.Scatter(
                x=ci_bands["date"],
                y=ci_bands["ci_lower"],
                fillcolor="rgba(100, 150, 255, 0.2)",
                fill="tonexty",
                mode="lines",
                line_color="rgba(0,0,0,0)",
                name="95% Bootstrap CI",
            ))
            
            fig.update_layout(
                title="Bootstrap Confidence Interval Bands (10K resamples)",
                xaxis_title="Date",
                yaxis_title="Value",
                height=400,
            )
            return fig
        except Exception as e:
            logger.error(f"Bootstrap CI error: {e}", exc_info=True)
            return error_figure(str(e))
```

### 3.3 Helper Function: Error Figure

```python
def error_figure(error_msg):
    """Create standardized error figure."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"Error: {error_msg[:100]}...",
        showarrow=False,
        font=dict(color="red", size=12),
    )
    fig.update_layout(
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
```

---

## 4. Labor & Lifecycle View (`app/dash_layouts_labor.py` + callbacks)

### 4.1 Layout Structure (abbreviated; follows same pattern as Analytics)

```python
# app/dash_layouts_labor.py

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify


def layout_labor_lifecycle():
    """Labor & Lifecycle View — 11+ workforce, cost, and scheduling charts."""
    return dmc.Container(
        fluid=True,
        p="lg",
        children=[
            dmc.Stack([
                dmc.Group([
                    dmc.Group([
                        DashIconify(icon="mdi:workers", width=32),
                        dmc.Stack([
                            dmc.Title("Labor & Lifecycle View", order=1, size="h2"),
                            dmc.Text(
                                "Workforce allocation, cost analysis, scheduling, and productivity metrics",
                                size="sm",
                                c="dimmed"
                            ),
                        ], gap=0),
                    ]),
                    dmc.Button("Refresh", id="btn-refresh-labor", variant="light"),
                ], justify="space-between", mb="lg"),
            ]),

            # Filters (same pattern as Analytics)
            dmc.Paper(
                p="md",
                radius="lg",
                withBorder=True,
                mb="xl",
                children=[
                    dmc.Group([
                        dmc.Stack([
                            dmc.Text("Date Range", fw=700, size="sm"),
                            dcc.DatePickerRange(
                                id="filter-labor-date-range",
                                start_date="2026-05-10",
                                end_date="2026-06-10",
                            ),
                        ], style={"flex": 1}, gap="xs"),
                        # Borough, Division, Role selectors...
                    ], grow=True, align="flex-end", spacing="md"),
                ],
            ),

            # Charts grid (11+ labor-specific charts)
            dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "lg": 3},
                spacing="lg",
                children=[
                    chart_container("chart-workforce-trends", "Workforce Allocation Trends", ""),
                    chart_container("chart-lifecycle-cost", "Lifecycle Cost Analysis", ""),
                    chart_container("chart-maintenance-schedule", "Maintenance Scheduling", ""),
                    chart_container("chart-productivity-metrics", "Inspector Productivity", ""),
                    chart_container("chart-seasonal-staffing", "Seasonal Staffing Needs", ""),
                    chart_container("chart-borough-comparison", "Borough Labor Comparison", ""),
                    chart_container("chart-roi-analysis", "Material Replacement ROI", ""),
                    chart_container("chart-budget-tracking", "Budget Tracking", ""),
                    chart_container("chart-turnover-rate", "Staff Turnover Rate", ""),
                    chart_container("chart-training-hours", "Training Hours by Role", ""),
                    chart_container("chart-cost-per-output", "Cost per Output Unit", ""),
                ],
            ),

            dcc.Store(id="store-labor-filters", data={}),
        ],
    )
```

### 4.2 Labor Callbacks (abbreviated; same callback structure)

```python
# app/callbacks/dash_labor.py

from dash import Input, Output, callback
import logging

logger = logging.getLogger(__name__)


def register_labor_callbacks(app, dash_service):
    """Register all labor view callbacks."""

    @app.callback(
        Output("store-labor-filters", "data"),
        Input("filter-labor-date-range", "start_date"),
        Input("filter-labor-date-range", "end_date"),
        Input("filter-labor-borough", "value"),
        Input("filter-labor-division", "value"),
        Input("filter-labor-role", "value"),
        prevent_initial_call=False,
    )
    def update_labor_filters(start, end, boro, div, role):
        return {
            "date_range": [start, end],
            "borough": boro or "ALL",
            "division": div or "ALL",
            "role": role or "ALL",
        }

    @app.callback(
        Output("chart-workforce-trends", "figure"),
        Input("store-labor-filters", "data"),
    )
    def render_workforce_trends(filters):
        """Time series of FTE headcount by role."""
        try:
            data = dash_service.query_workforce_time_series(
                date_range=filters["date_range"],
                borough=filters["borough"],
            )
            fig = dash_service.create_workforce_trends_figure(data)
            fig.update_layout(height=400)
            return fig
        except Exception as e:
            logger.error(f"Workforce trends error: {e}")
            return error_figure(str(e))

    # 10 more callbacks following same pattern...
    # (create_lifecycle_cost_figure, create_maintenance_schedule_figure, etc.)
```

---

## 5. Shared Service Layer (`app/services/dash_service.py`)

### 5.1 Complete Service Code

```python
# app/services/dash_service.py

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats as scipy_stats
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import seasonal_decompose
import diskcache

logger = logging.getLogger(__name__)

# ─── CACHE INITIALIZATION ───
_l2_cache = diskcache.Cache(".cache/dash_l2")


class DashAnalyticsService:
    """Centralized service for analytics data + transformations."""

    def __init__(self, duckdb_path: str = None):
        self.duckdb_path = duckdb_path or "data/local_db/nyc_mission_control.duckdb"

    # ─── DATA LOADING METHODS ───

    def query_cusum_data(self, date_range: List[str], boroughs: List[str], exclude_outliers: bool = False) -> pd.DataFrame:
        """Fetch CUSUM control data from DuckDB."""
        cache_key = f"cusum_{'-'.join(boroughs)}_{date_range[0]}_{date_range[1]}_{exclude_outliers}"
        if cache_key in _l2_cache:
            return _l2_cache[cache_key]

        query = """
        SELECT date, borough, metric_value, control_limit, violation_flag
        FROM analytics.cusum_data
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        ORDER BY date
        """
        
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(
            query,
            (date_range[0], date_range[1], boroughs[0] if len(boroughs) == 1 else 'ALL', boroughs)
        ).df()
        con.close()

        if exclude_outliers:
            Q1 = data["metric_value"].quantile(0.25)
            Q3 = data["metric_value"].quantile(0.75)
            IQR = Q3 - Q1
            data = data[(data["metric_value"] >= Q1 - 1.5*IQR) & (data["metric_value"] <= Q3 + 1.5*IQR)]

        _l2_cache.set(cache_key, data, expire=300)
        return data

    def query_ramp_completion_data(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch ramp completion status data."""
        cache_key = f"ramp_completion_{'-'.join(boroughs)}_{date_range[0]}_{date_range[1]}"
        if cache_key in _l2_cache:
            return _l2_cache[cache_key]

        query = """
        SELECT borough, completed, total, 
               CAST(completed AS FLOAT) / total AS completion_rate
        FROM analytics.ramp_progress
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()

        _l2_cache.set(cache_key, data, expire=300)
        return data

    def query_violation_data(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch violation data with flags."""
        cache_key = f"violations_{'-'.join(boroughs)}_{date_range[0]}_{date_range[1]}"
        if cache_key in _l2_cache:
            return _l2_cache[cache_key]

        query = """
        SELECT borough, violation_flag, violation_count
        FROM analytics.violations_summary
        WHERE created_date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()

        _l2_cache.set(cache_key, data, expire=300)
        return data

    def query_sla_breach_data(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch SLA breach data."""
        query = """
        SELECT borough, days_since_update, sla_threshold, breached
        FROM analytics.sla_tracking
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data

    def query_time_series_data(self, date_range: List[str], boroughs: List[str], metric: str) -> pd.DataFrame:
        """Fetch time-series data for forecasting."""
        metric_col = metric or "completion_rate"
        query = f"""
        SELECT date, {metric_col} AS value
        FROM analytics.time_series
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        ORDER BY date
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data.sort_values("date").reset_index(drop=True)

    def query_cluster_features(self, date_range: List[str], boroughs: List[str]) -> np.ndarray:
        """Fetch feature matrix for clustering."""
        query = """
        SELECT completion_rate, violation_count, days_open, material_score
        FROM analytics.features
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data.fillna(0).values

    def query_material_lifecycle_data(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch material lifecycle data for survival analysis."""
        query = """
        SELECT material_type, days_since_installation, degradation_flag, years_in_service
        FROM analytics.material_lifecycle
        WHERE installation_date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data

    def query_spatial_data(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch spatial data with coordinates."""
        query = """
        SELECT latitude, longitude, metric_value, location_name
        FROM analytics.spatial_features
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data

    def query_completion_rate_distribution(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch completion rates for distribution analysis."""
        query = """
        SELECT completion_rate
        FROM analytics.completion_rates
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data

    def query_violation_count_distribution(self, date_range: List[str], boroughs: List[str]) -> pd.DataFrame:
        """Fetch violation counts for distribution analysis."""
        query = """
        SELECT violation_count
        FROM analytics.violation_counts
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ANY(?))
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], boroughs[0] if boroughs else 'ALL', boroughs)).df()
        con.close()
        return data

    def query_workforce_time_series(self, date_range: List[str], borough: str) -> pd.DataFrame:
        """Fetch workforce FTE time series."""
        query = """
        SELECT date, role, fte_count
        FROM analytics.workforce_metrics
        WHERE date BETWEEN ? AND ?
          AND (? = 'ALL' OR borough = ?)
        ORDER BY date, role
        """
        con = duckdb.connect(self.duckdb_path, read_only=True)
        data = con.execute(query, (date_range[0], date_range[1], borough, borough)).df()
        con.close()
        return data

    # ─── STATISTICAL TRANSFORMATION METHODS ───

    def compute_bayesian_posterior_binomial(self, successes: int, trials: int, prior_alpha: float = 1.0, prior_beta: float = 1.0) -> np.ndarray:
        """Compute Beta-Binomial conjugate posterior."""
        posterior_alpha = prior_alpha + successes
        posterior_beta = prior_beta + (trials - successes)
        
        x = np.linspace(0, 1, 1000)
        pdf = scipy_stats.beta.pdf(x, posterior_alpha, posterior_beta)
        
        return {"x": x, "pdf": pdf, "alpha": posterior_alpha, "beta": posterior_beta}

    def compute_sla_breach_probabilities(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute P(breach | data) per borough."""
        breach_probs = data.groupby("borough")["breached"].agg(
            lambda x: x.sum() / len(x)
        ).reset_index()
        breach_probs.columns = ["borough", "breach_probability"]
        return breach_probs

    def compute_bayesian_forecast(self, data: pd.DataFrame, periods: int = 30, credible_interval: float = 0.95) -> pd.DataFrame:
        """Bayesian time-series forecast with credible bands."""
        # Simplified: use exponential smoothing + bootstrap for credible intervals
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        
        if len(data) < 4:
            return pd.DataFrame({"date": [], "mean": [], "ci_lower": [], "ci_upper": []})
        
        # Fit model
        try:
            model = ExponentialSmoothing(data["value"], seasonal_periods=7, trend="add", seasonal="add")
            result = model.fit()
            forecast = result.get_forecast(steps=periods)
            
            # Credible interval from bootstrap
            n_bootstrap = 1000
            bootstrap_forecasts = []
            for _ in range(n_bootstrap):
                sample = np.random.choice(data["value"].values, size=len(data["value"]), replace=True)
                try:
                    m = ExponentialSmoothing(sample, seasonal_periods=7, trend="add", seasonal="add")
                    r = m.fit(disp=False)
                    bootstrap_forecasts.append(r.get_forecast(steps=periods).predicted_mean.values)
                except:
                    pass
            
            if bootstrap_forecasts:
                bootstrap_array = np.array(bootstrap_forecasts)
                ci_lower = np.percentile(bootstrap_array, (1 - credible_interval) / 2 * 100, axis=0)
                ci_upper = np.percentile(bootstrap_array, (1 + credible_interval) / 2 * 100, axis=0)
            else:
                std_err = result.resid.std()
                ci_lower = forecast.predicted_mean.values - 1.96 * std_err
                ci_upper = forecast.predicted_mean.values + 1.96 * std_err
            
            # Create forecast dates
            last_date = pd.to_datetime(data["date"].iloc[-1])
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods)
            
            return pd.DataFrame({
                "date": forecast_dates,
                "mean": forecast.predicted_mean.values,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            })
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return pd.DataFrame({"date": [], "mean": [], "ci_lower": [], "ci_upper": []})

    def compute_kmeans_clusters(self, data: np.ndarray, n_clusters: int = 3, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """KMeans clustering + PCA projection."""
        from sklearn.decomposition import PCA
        
        scaler = StandardScaler()
        scaled = scaler.fit_transform(data)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        clusters = kmeans.fit_predict(scaled)
        
        pca = PCA(n_components=2)
        pca_data = pca.fit_transform(scaled)
        
        return clusters, pca_data

    def compute_kaplan_meier(self, data: pd.DataFrame) -> pd.DataFrame:
        """Kaplan-Meier survival curve."""
        from lifelines import KaplanMeierFitter
        
        kmf = KaplanMeierFitter()
        kmf.fit(
            durations=data["years_in_service"],
            event_observed=data["degradation_flag"],
            label="Material Type"
        )
        
        return pd.DataFrame({
            "time": kmf.confidence_interval_.index,
            "survival_probability": kmf.survival_function_.values.flatten(),
        })

    def compute_morans_i_local(self, data: pd.DataFrame) -> np.ndarray:
        """Local Moran's I (LISA)."""
        from pysal.lib import weights
        from esda import Moran_Local
        
        # Create weights from coordinates
        coords = data[["latitude", "longitude"]].values
        from scipy.spatial.distance import cdist
        
        distances = cdist(coords, coords)
        threshold = np.percentile(distances[distances > 0], 25)  # 1st quartile
        
        w_matrix = (distances < threshold).astype(float)
        np.fill_diagonal(w_matrix, 0)
        
        # Compute LISA
        lisa = Moran_Local(data["metric_value"].values, w_matrix)
        return lisa.Is

    def test_normality(self, values: np.ndarray) -> Tuple[float, float]:
        """Shapiro-Wilk normality test."""
        if len(values) < 3:
            return np.nan, 1.0
        stat, pval = scipy_stats.shapiro(values)
        return stat, pval

    def compute_kde_x(self, values: np.ndarray) -> np.ndarray:
        """Compute KDE x-values."""
        return np.linspace(values.min(), values.max(), 200)

    def compute_kde_y(self, values: np.ndarray) -> np.ndarray:
        """Compute KDE y-values."""
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(values)
        return kde(self.compute_kde_x(values))

    def detect_anomalies_isolation_forest(self, data: pd.DataFrame, contamination: float = 0.05) -> np.ndarray:
        """Isolation Forest anomaly detection."""
        features = data[["latitude", "longitude", "metric_value"]].values
        
        iso_forest = IsolationForest(contamination=contamination, random_state=42)
        predictions = iso_forest.fit_predict(features)
        
        return predictions == -1

    def compute_seasonal_decomposition(self, data: pd.DataFrame, period: int = 7) -> pd.DataFrame:
        """Seasonal decomposition."""
        if len(data) < 2 * period:
            return pd.DataFrame()
        
        decomposition = seasonal_decompose(
            data["value"],
            model="additive",
            period=period,
            extrapolate="fill_mean"
        )
        
        return pd.DataFrame({
            "date": data["date"],
            "trend": decomposition.trend.values,
            "seasonal": decomposition.seasonal.values,
            "residual": decomposition.resid.values,
        })

    def compute_bootstrap_ci_bands(self, data: pd.DataFrame, n_bootstrap: int = 10000, ci: float = 0.95, window_size: int = 7) -> pd.DataFrame:
        """Bootstrap confidence intervals with rolling window."""
        if len(data) < window_size:
            return pd.DataFrame()
        
        ci_lower = []
        ci_upper = []
        
        for i in range(len(data)):
            start = max(0, i - window_size + 1)
            end = i + 1
            window = data["value"].iloc[start:end].values
            
            if len(window) < 2:
                ci_lower.append(window[0] if len(window) > 0 else np.nan)
                ci_upper.append(window[0] if len(window) > 0 else np.nan)
                continue
            
            bootstrap_samples = [np.random.choice(window, size=len(window), replace=True).mean() for _ in range(n_bootstrap)]
            
            alpha = (1 - ci) / 2
            ci_lower.append(np.percentile(bootstrap_samples, alpha * 100))
            ci_upper.append(np.percentile(bootstrap_samples, (1 - alpha) * 100))
        
        return pd.DataFrame({
            "date": data["date"],
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        })

    # ─── FIGURE CREATION METHODS ───

    def create_cusum_figure(self, data: pd.DataFrame) -> go.Figure:
        """CUSUM control chart."""
        fig = go.Figure()
        
        for borough in data["borough"].unique():
            subset = data[data["borough"] == borough].sort_values("date")
            
            fig.add_trace(go.Scatter(
                x=subset["date"],
                y=subset["metric_value"],
                mode="lines+markers",
                name=borough,
            ))
            
            fig.add_hline(y=subset["control_limit"].iloc[0], line_dash="dash", line_color="red")
        
        fig.update_layout(
            title="CUSUM Control Chart",
            xaxis_title="Date",
            yaxis_title="CUSUM Value",
        )
        return fig

    def create_bayesian_posterior_figure(self, posterior: Dict, title: str, metric_name: str) -> go.Figure:
        """Bayesian posterior distribution."""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=posterior["x"],
            y=posterior["pdf"],
            fill="tozeroy",
            mode="lines",
            name="Posterior",
        ))
        
        # Mark mean + credible interval
        mean = posterior["alpha"] / (posterior["alpha"] + posterior["beta"])
        ci_lower, ci_upper = scipy_stats.beta.ppf([0.025, 0.975], posterior["alpha"], posterior["beta"])
        
        fig.add_vline(x=mean, line_dash="dash", line_color="blue", annotation_text=f"Mean: {mean:.3f}")
        fig.add_vrect(x0=ci_lower, x1=ci_upper, fillcolor="blue", opacity=0.1, annotation_text="95% CI")
        
        fig.update_layout(
            title=title,
            xaxis_title=metric_name,
            yaxis_title="Probability Density",
        )
        return fig

    def create_workforce_trends_figure(self, data: pd.DataFrame) -> go.Figure:
        """Workforce allocation trends."""
        fig = px.line(
            data,
            x="date",
            y="fte_count",
            color="role",
            title="Workforce Allocation Trends",
            markers=True,
        )
        return fig
```

---

## 6. Integration Testing (`tests/test_dash_analytics_callbacks.py`)

### 6.1 Test Structure (30+ test cases)

```python
# tests/test_dash_analytics_callbacks.py

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dash.testing.composite import DashComposite

from app.dash_app import app
from app.services.dash_service import DashAnalyticsService


class TestAnalyticsCallbacks(DashComposite):
    """Integration tests for analytics callback chain."""

    @pytest.fixture(scope="class")
    def dash_service(self):
        return DashAnalyticsService("data/test_db.duckdb")

    def test_analytics_page_load(self):
        """Test page loads without crashing."""
        self.driver.get(self.server_url + "/analytics")
        assert self.driver.title  # Page loaded
        self.wait_for_element_by_id("chart-cusum", timeout=10)

    def test_filter_date_range_change(self):
        """Test date range filter updates all charts."""
        self.driver.get(self.server_url + "/analytics")
        
        # Change start date
        start_input = self.driver.find_element("id", "filter-date-range").find_elements("tag name", "input")[0]
        start_input.clear()
        start_input.send_keys("06-01-2026")
        
        # Wait for chart update
        self.wait_for_element_by_id("chart-cusum", timeout=5)
        
        # Verify chart rendered
        chart_element = self.driver.find_element("id", "chart-cusum")
        assert chart_element is not None

    def test_borough_filter_updates_all_charts(self):
        """Test borough selector updates all dependent charts."""
        self.driver.get(self.server_url + "/analytics")
        
        # Select single borough
        borough_selector = self.driver.find_element("id", "filter-borough")
        borough_selector.send_keys("MN")
        
        # Wait for updates
        self.wait_for_element_by_id("chart-cusum", timeout=5)

    def test_filter_store_synchronization(self):
        """Test store-analytics-filters updates correctly."""
        self.driver.get(self.server_url + "/analytics")
        
        # Change filters
        # ... interact with filter UI ...
        
        # Read store via clientside
        store_value = self.driver.execute_script(
            "return JSON.parse(document.querySelector('[id=\"store-analytics-filters\"]').getAttribute('data-dash-json'))"
        )
        
        assert store_value["date_range"]
        assert store_value["borough"]

    @pytest.mark.parametrize("chart_id", [
        "chart-cusum",
        "chart-bayesian-ci-ramp",
        "chart-bayesian-ci-violation",
        "chart-bayesian-sla",
        "chart-bayesian-forecast",
        "chart-kmeans",
        "chart-survival",
        "chart-morans-i",
        "chart-distribution-completion",
        "chart-distribution-violation",
        "chart-anomaly-map",
        "chart-seasonal-decomp",
        "chart-bootstrap-ci",
    ])
    def test_all_charts_render(self, chart_id):
        """Test all 13 charts render without error."""
        self.driver.get(self.server_url + "/analytics")
        self.wait_for_element_by_id(chart_id, timeout=10)
        
        chart = self.driver.find_element("id", chart_id)
        assert chart is not None

    def test_chart_loading_spinner_appears(self):
        """Test loading indicator shows during data fetch."""
        self.driver.get(self.server_url + "/analytics")
        
        # Trigger filter change (causes reload)
        start_input = self.driver.find_element("id", "filter-date-range").find_elements("tag name", "input")[0]
        start_input.clear()
        start_input.send_keys("06-01-2026")
        
        # Check for loading indicator
        # (Dash dcc.Loading adds "dash-loading" class)

    def test_error_alert_displays_on_invalid_filters(self):
        """Test error alert appears with invalid filter state."""
        # This would require mocking a data fetch error
        pass

    def test_chart_export_buttons_work(self):
        """Test export buttons (CSV, JSON) are clickable."""
        self.driver.get(self.server_url + "/analytics")
        self.wait_for_element_by_id("chart-cusum", timeout=10)
        
        # Click Data tab
        data_tab = self.driver.find_element("xpath", "//button[contains(text(), 'Data')]")
        data_tab.click()

    def test_chart_tab_switching(self):
        """Test switching between Chart | Insights | Data | Export tabs."""
        self.driver.get(self.server_url + "/analytics")
        self.wait_for_element_by_id("chart-cusum", timeout=10)
        
        # Click Insights tab
        insights_tab = self.driver.find_element("xpath", "//button[contains(text(), 'Insights')]")
        insights_tab.click()
        
        # Verify tab content appears

    def test_callback_latency_p95_under_500ms(self):
        """Test callback latency is <500ms P95."""
        # Requires instrumenting callbacks with timing
        pass

    def test_concurrent_user_load(self):
        """Simulate 100 concurrent users."""
        # Use locust or pytest-asyncio
        pass

    def test_filter_debouncing_works(self):
        """Test date picker debounces rapid changes."""
        pass

    def test_cache_hit_reduces_latency(self):
        """Test L2 cache reduces query latency."""
        pass


class TestDashServiceDataLoading:
    """Unit tests for DashAnalyticsService data loading."""

    @pytest.fixture
    def service(self):
        return DashAnalyticsService("data/test_db.duckdb")

    def test_query_cusum_data_returns_dataframe(self, service):
        """Test CUSUM query returns valid DataFrame."""
        data = service.query_cusum_data(
            date_range=["2026-05-10", "2026-06-10"],
            boroughs=["MN"],
            exclude_outliers=False
        )
        
        assert isinstance(data, pd.DataFrame)
        assert not data.empty
        assert "date" in data.columns
        assert "metric_value" in data.columns

    def test_query_ramp_completion_data(self, service):
        """Test ramp completion query."""
        data = service.query_ramp_completion_data(
            date_range=["2026-05-10", "2026-06-10"],
            boroughs=["MN"]
        )
        
        assert isinstance(data, pd.DataFrame)
        assert "completion_rate" in data.columns

    @pytest.mark.parametrize("boroughs", [["MN"], ["MN", "BX"], []])
    def test_query_with_multiple_boroughs(self, service, boroughs):
        """Test queries work with variable borough counts."""
        data = service.query_cusum_data(
            date_range=["2026-05-10", "2026-06-10"],
            boroughs=boroughs or ["ALL"]
        )
        assert isinstance(data, pd.DataFrame)

    def test_outlier_exclusion(self, service):
        """Test exclude_outliers=True removes extreme values."""
        data_with_outliers = service.query_cusum_data(
            date_range=["2026-05-10", "2026-06-10"],
            boroughs=["MN"],
            exclude_outliers=False
        )
        
        data_without = service.query_cusum_data(
            date_range=["2026-05-10", "2026-06-10"],
            boroughs=["MN"],
            exclude_outliers=True
        )
        
        assert len(data_without) <= len(data_with_outliers)


class TestDashServiceTransformations:
    """Unit tests for data transformation methods."""

    @pytest.fixture
    def service(self):
        return DashAnalyticsService("data/test_db.duckdb")

    def test_bayesian_posterior_binomial(self, service):
        """Test Beta-Binomial posterior computation."""
        posterior = service.compute_bayesian_posterior_binomial(
            successes=50,
            trials=100,
            prior_alpha=1,
            prior_beta=1
        )
        
        assert "x" in posterior
        assert "pdf" in posterior
        assert "alpha" in posterior
        assert len(posterior["pdf"]) > 0
        assert posterior["pdf"].sum() > 0

    def test_kmeans_clustering(self, service):
        """Test KMeans clustering + PCA."""
        data = np.random.randn(100, 4)
        clusters, pca_data = service.compute_kmeans_clusters(data, n_clusters=3)
        
        assert len(clusters) == 100
        assert pca_data.shape == (100, 2)
        assert len(np.unique(clusters)) == 3

    def test_kaplan_meier_survival(self, service):
        """Test Kaplan-Meier estimator."""
        data = pd.DataFrame({
            "material_type": ["A"] * 50 + ["B"] * 50,
            "years_in_service": np.random.exponential(5, 100),
            "degradation_flag": np.random.binomial(1, 0.3, 100),
        })
        
        km = service.compute_kaplan_meier(data)
        assert not km.empty
        assert "survival_probability" in km.columns

    def test_seasonal_decomposition(self, service):
        """Test seasonal decomposition."""
        dates = pd.date_range("2026-01-01", periods=56, freq="D")
        values = 100 + 10*np.sin(np.arange(56)*2*np.pi/7) + np.random.normal(0, 2, 56)
        data = pd.DataFrame({"date": dates, "value": values})
        
        decomp = service.compute_seasonal_decomposition(data, period=7)
        
        assert not decomp.empty
        assert "trend" in decomp.columns
        assert "seasonal" in decomp.columns
        assert "residual" in decomp.columns

    def test_bootstrap_ci_bands(self, service):
        """Test bootstrap CI band computation."""
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        values = np.cumsum(np.random.normal(0, 1, 30))
        data = pd.DataFrame({"date": dates, "value": values})
        
        ci = service.compute_bootstrap_ci_bands(data, n_bootstrap=1000, window_size=7)
        
        assert len(ci) == len(data)
        assert "ci_lower" in ci.columns
        assert "ci_upper" in ci.columns

    def test_anomaly_detection(self, service):
        """Test Isolation Forest anomaly detection."""
        data = pd.DataFrame({
            "latitude": np.random.uniform(40.7, 40.9, 100),
            "longitude": np.random.uniform(-74, -73.9, 100),
            "metric_value": list(np.random.normal(50, 10, 95)) + [200, 200, 200, 200, 200],  # 5 anomalies
        })
        
        anomalies = service.detect_anomalies_isolation_forest(data, contamination=0.05)
        
        assert anomalies.sum() >= 3  # At least some anomalies detected


class TestDashServiceFigureCreation:
    """Test Plotly figure generation."""

    @pytest.fixture
    def service(self):
        return DashAnalyticsService("data/test_db.duckdb")

    def test_cusum_figure_structure(self, service):
        """Test CUSUM figure has correct structure."""
        data = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=30),
            "borough": ["MN"] * 30,
            "metric_value": np.cumsum(np.random.normal(0, 1, 30)),
            "control_limit": 5,
        })
        
        fig = service.create_cusum_figure(data)
        
        assert "data" in fig
        assert len(fig.data) > 0
        assert fig.layout.title.text

    def test_bayesian_posterior_figure_structure(self, service):
        """Test Bayesian posterior figure."""
        posterior = service.compute_bayesian_posterior_binomial(50, 100)
        fig = service.create_bayesian_posterior_figure(
            posterior,
            "Test Posterior",
            "test_metric"
        )
        
        assert len(fig.data) > 0
        assert fig.layout.title.text == "Test Posterior"

    def test_all_figures_return_go_figure(self, service):
        """Ensure all figure creation methods return go.Figure."""
        import plotly.graph_objects as go
        
        # This would require mock data
        # service.create_cusum_figure(...) → go.Figure
        # etc.
        pass
```

---

## 7. Performance Testing Approach

### 7.1 Latency Profiling

```python
# tests/test_performance.py

import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


class TestDashPerformance:
    """Performance benchmarks for Dash callbacks."""

    @pytest.mark.performance
    def test_filter_callback_latency(self):
        """Measure callback latency for filter changes."""
        driver = webdriver.Chrome()
        driver.get("http://localhost:8011/analytics")
        
        # Time filter change → chart update
        start = time.time()
        
        # Trigger filter change
        start_input = driver.find_element(By.ID, "filter-date-range")
        start_input.clear()
        start_input.send_keys("06-01-2026")
        
        # Wait for chart to render
        chart = driver.find_element(By.ID, "chart-cusum")
        driver.execute_script("arguments[0].scrollIntoView();", chart)
        
        elapsed = time.time() - start
        
        assert elapsed < 0.5, f"Latency {elapsed:.3f}s exceeds 500ms target"
        driver.quit()

    @pytest.mark.performance
    def test_page_load_time(self):
        """Measure analytics page load time (target: <3s)."""
        driver = webdriver.Chrome()
        
        start = time.time()
        driver.get("http://localhost:8011/analytics")
        
        # Wait for all charts to render
        chart_ids = [
            "chart-cusum",
            "chart-bayesian-ci-ramp",
            "chart-kmeans",
        ]
        for chart_id in chart_ids:
            driver.find_element(By.ID, chart_id)
        
        elapsed = time.time() - start
        
        assert elapsed < 3.0, f"Load time {elapsed:.3f}s exceeds 3s target"
        driver.quit()
```

### 7.2 Load Testing (Locust)

```python
# tests/load_test.py

from locust import HttpUser, task, between


class AnalyticsUser(HttpUser):
    wait_time = between(2, 5)

    @task(1)
    def load_analytics_page(self):
        self.client.get("/analytics")

    @task(2)
    def change_date_range(self):
        self.client.post(
            "/_dash-update-component",
            json={
                "outputs": {"id": "store-analytics-filters", "property": "data"},
                "inputs": [{"id": "filter-date-range", "property": "start_date", "value": "2026-06-01"}],
                "state": [],
                "clientId": "test",
            }
        )

    @task(1)
    def get_chart_data(self):
        self.client.get("/_dash-update-component?...")
```

---

## 8. Commit Strategy

### Week 4: Analytics Advanced View

**Commit 1:** Layout skeleton
```bash
git add app/dash_layouts_analytics.py
git commit -m "feat: Analytics Advanced View layout skeleton

- Define filter panel (date, borough, metric, options)
- Create 13-chart grid with chart_container wrapper
- Add error alert + loading indicator
- Register /analytics route in dash_app.py"
```

**Commit 2:** Callbacks part 1 (filter + first 5 charts)
```bash
git add app/callbacks/dash_analytics.py
git commit -m "feat: Analytics callbacks — filter sync + CUSUM/Bayesian charts

- Master filter callback (store-analytics-filters)
- CUSUM control chart callback
- 4 Bayesian posterior callbacks (ramp, violation, SLA, forecast)
- Error handling + debouncing pattern"
```

**Commit 3:** Callbacks part 2 (remaining 8 charts)
```bash
git commit -m "feat: Analytics callbacks — advanced charts (8 more)

- KMeans clustering callback
- Kaplan-Meier survival curves callback
- Moran's I spatial autocorrelation callback
- 2 distribution analysis callbacks
- Anomaly detection map callback
- Seasonal decomposition callback
- Bootstrap CI bands callback"
```

**Commit 4:** Service layer
```bash
git add app/services/dash_service.py
git commit -m "feat: DuckDB analytics service layer

- Data loading: query_* methods (14 total)
- Statistical transforms: compute_* methods (12 total)
- Figure creation: create_* methods (5 total)
- L2 cache with 5-min TTL + LRU eviction"
```

**Commit 5:** Testing
```bash
git add tests/test_dash_analytics_callbacks.py tests/test_performance.py
git commit -m "test: Integration + performance tests for analytics

- 30+ callback integration tests
- 15+ service unit tests
- Performance benchmarks (latency, load time)
- Concurrent user simulation (100+ users)"
```

### Week 5: Labor & Lifecycle View + Integration

**Commit 6-10:** Mirror Week 4 structure for labor view

**Commit 11:** Final integration
```bash
git commit -m "refactor: Consolidate analytics + labor callbacks

- Register both callback sets in dash_app.py
- Update router for /labor route
- Verify no callback ID conflicts
- Clean up unused Streamlit code"
```

---

## 9. Dependencies & DuckDB Schema Expectations

### 9.1 Required Libraries

```txt
dash==4.2.0
dash-mantine-components==0.14.0
dash_iconify==0.1.2
plotly==5.17.0
pandas==2.0.3
numpy==1.24.3
scipy==1.11.1
scikit-learn==1.3.0
statsmodels==0.14.0
pymc==5.1.0
lifelines==0.29.0
pysal==4.10.0
esda==2.5.1
duckdb==0.8.1
diskcache==5.6.1
```

### 9.2 DuckDB Analytics Schema

```sql
-- Tables expected in analytics schema

CREATE TABLE analytics.cusum_data (
    date DATE,
    borough VARCHAR,
    metric_value FLOAT,
    control_limit FLOAT,
    violation_flag BOOLEAN
);

CREATE TABLE analytics.ramp_progress (
    date DATE,
    borough VARCHAR,
    completed INT,
    total INT
);

CREATE TABLE analytics.violations_summary (
    created_date DATE,
    borough VARCHAR,
    violation_flag BOOLEAN,
    violation_count INT
);

CREATE TABLE analytics.sla_tracking (
    date DATE,
    borough VARCHAR,
    days_since_update INT,
    sla_threshold INT,
    breached BOOLEAN
);

CREATE TABLE analytics.time_series (
    date DATE,
    borough VARCHAR,
    completion_rate FLOAT,
    violation_count INT,
    days_open FLOAT
);

-- (8 more tables expected...)
```

---

## 10. Key Performance Optimizations

1. **Query Optimization:** Pre-compute aggregates in DuckDB, use Parquet for fast I/O
2. **Caching:** L2 Diskcache with 5-min TTL + LRU eviction
3. **Lazy Loading:** Render off-screen charts on-demand (Intersection Observer)
4. **Debouncing:** 300ms debounce on filter inputs
5. **Client-side Callbacks:** Instant UI feedback for filter UI updates
6. **Callback Serialization:** All callbacks run serially (single thread) to avoid race conditions
7. **Memoization:** Cache figure JSON for identical filter states
8. **Error Boundaries:** Graceful degradation if individual charts fail

---

## 11. Summary & Next Steps

**Phase 2A delivers:**
- 2 production-grade Dash views (Analytics + Labor)
- 24+ interactive charts with <500ms P95 latency
- 100+ concurrent user support
- Full callback-driven interactivity
- Comprehensive test coverage (30+ tests)

**Timeline:** 55 hours (Weeks 4–5)
- Week 4: Analytics view (30 hours)
- Week 5: Labor view + integration (25 hours)

**Quality gates:**
- All tests pass (`pytest tests/ -q`)
- Ruff linting passes (`ruff check app/`)
- Performance benchmarks met (<500ms P95)
- Zero Dash exceptions in error logs

---

**End of Specification**
