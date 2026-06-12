"""
Analytics Integration Test Dashboard (Phase G Testing)
Tests all 5 analytics methods with mock data in a live Dash app.

Run with: python src/socrata_toolkit/dashboards/analytics_integration_test.py
Then open: http://localhost:8050
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[3])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import logging

import dash
import geopandas as gpd
import numpy as np
import pandas as pd
from dash import Input, Output, State, callback, dcc, html
from shapely.geometry import Point

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Phase B-F components
from app.callbacks.analytics import AnalyticsEngine
from app.dash_layouts_analytics_integration import (
    render_analytics_integration_tabs,
    render_analytics_stores,
)
from app.services.analytics_service import (
    get_dataset,
    get_spatial_data,
    get_timeseries_data,
)

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Analytics Integration Test Dashboard"

# ============================================================================
# MOCK DATA GENERATORS
# ============================================================================

def generate_mock_inspection_data(n=150):
    """Generate mock inspection data."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(n),
        "borough": np.random.choice(["MANHATTAN", "BROOKLYN", "BRONX", "QUEENS", "STATEN_ISLAND"], n),
        "violation_count": np.random.poisson(5, n),
        "score": np.random.normal(75, 15, n),
        "response_time_hours": np.random.uniform(1, 24, n),
        "completion_rate": np.random.uniform(0.6, 1.0, n),
        "created_date": pd.date_range("2026-05-01", periods=n, freq="12H"),
        "status": np.random.choice(["COMPLETED", "PENDING", "REJECTED"], n),
    })

def generate_mock_spatial_data(n=50):
    """Generate mock spatial data."""
    np.random.seed(42)
    coords = np.random.uniform(-74.05, -73.75, (n, 2))
    return gpd.GeoDataFrame(
        {
            "id": range(n),
            "borough": np.random.choice(["MN", "BK", "BX", "QN", "SI"], n),
            "violation_count": np.random.poisson(5, n),
            "quality_score": np.random.uniform(60, 95, n),
            "geometry": [Point(xy) for xy in coords],
        },
        crs="EPSG:4326"
    )

def generate_mock_timeseries_data(n=120):
    """Generate mock time series data."""
    np.random.seed(42)
    dates = pd.date_range("2026-02-01", periods=n, freq="D")
    trend = np.linspace(80, 90, n)
    seasonal = 5 * np.sin(np.linspace(0, 4*np.pi, n))
    noise = np.random.normal(0, 2, n)
    return pd.DataFrame({
        "date": dates,
        "violation_count": trend + seasonal + noise,
    })

# ============================================================================
# LAYOUT
# ============================================================================

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Analytics Integration Test Dashboard", style={"margin": "0"}),
        html.P("Live testing of Phase B-F analytics methods", style={"color": "#666"}),
    ], style={"padding": "20px", "borderBottom": "1px solid #ddd"}),

    # Controls
    html.Div([
        html.Button("Refresh Data", id="btn-refresh", n_clicks=0,
                   style={"padding": "8px 16px", "marginRight": "10px"}),
        html.Span(id="status-message", style={"color": "#0066CC", "fontSize": "14px"}),
    ], style={"padding": "15px"}),

    # Main content
    html.Div([
        render_analytics_integration_tabs(),
    ], style={"padding": "20px"}),

    # Stores
    render_analytics_stores(),
    dcc.Store(id="test-data-store", data={}),
], style={"fontFamily": "sans-serif", "backgroundColor": "#f9f9f9", "minHeight": "100vh"})

# ============================================================================
# CALLBACKS: Data Loading
# ============================================================================

@callback(
    Output("test-data-store", "data"),
    Output("status-message", "children"),
    Input("btn-refresh", "n_clicks"),
    prevent_initial_call=False
)
def load_test_data(n_clicks):
    """Load mock data for testing."""
    try:
        data = {
            "tabular": generate_mock_inspection_data().to_dict(),
            "spatial": generate_mock_spatial_data().to_dict(),
            "timeseries": generate_mock_timeseries_data().to_dict(),
        }
        msg = f"✓ Data loaded ({n_clicks} refresh{'es' if n_clicks != 1 else ''})"
        return data, msg
    except Exception as e:
        logger.error(f"Data load error: {e}")
        return {}, f"✗ Error: {str(e)[:50]}"

# ============================================================================
# CALLBACKS: Phase C (Distribution)
# ============================================================================

@callback(
    Output("distribution-narrative", "children"),
    [Input("test-data-store", "data")],
    prevent_initial_call=True
)
def update_distribution(data_dict):
    """Update Phase C distribution chart."""
    try:
        if not data_dict or "tabular" not in data_dict:
            return "Waiting for data..."

        df = pd.DataFrame(data_dict["tabular"])
        fig, narrative = AnalyticsEngine.chart_distribution_classification({"data": df})
        logger.info(f"Phase C: Distribution generated ({len(narrative)} chars narrative)")
        return narrative
    except Exception as e:
        return f"Phase C Error: {str(e)}"

# ============================================================================
# CALLBACKS: Phase D (Anomaly)
# ============================================================================

@callback(
    Output("anomaly-narrative", "children"),
    [Input("test-data-store", "data")],
    prevent_initial_call=True
)
def update_anomaly(data_dict):
    """Update Phase D anomaly chart."""
    try:
        if not data_dict or "spatial" not in data_dict:
            return "Waiting for data..."

        gdf = gpd.GeoDataFrame(data_dict["spatial"])
        fig, narrative = AnalyticsEngine.chart_anomaly_detection({"spatial": gdf})
        logger.info(f"Phase D: Anomaly generated ({len(narrative)} chars narrative)")
        return narrative
    except Exception as e:
        return f"Phase D Error: {str(e)}"

# ============================================================================
# CALLBACKS: Phase E (Decomposition)
# ============================================================================

@callback(
    Output("decomposition-narrative", "children"),
    [Input("test-data-store", "data")],
    prevent_initial_call=True
)
def update_decomposition(data_dict):
    """Update Phase E decomposition chart."""
    try:
        if not data_dict or "timeseries" not in data_dict:
            return "Waiting for data..."

        df = pd.DataFrame(data_dict["timeseries"])
        fig, narrative = AnalyticsEngine.chart_seasonal_decomposition({"data": df})
        logger.info(f"Phase E: Decomposition generated ({len(narrative)} chars narrative)")
        return narrative
    except Exception as e:
        return f"Phase E Error: {str(e)}"

# ============================================================================
# CALLBACKS: Phase F (Bootstrap CI)
# ============================================================================

@callback(
    Output("bootstrap-narrative", "children"),
    [Input("test-data-store", "data")],
    prevent_initial_call=True
)
def update_bootstrap(data_dict):
    """Update Phase F bootstrap CI chart."""
    try:
        if not data_dict or "tabular" not in data_dict:
            return "Waiting for data..."

        df = pd.DataFrame(data_dict["tabular"])
        metrics = {
            "completion_rate": (df["completion_rate"].mean(), 0.80, 0.95),
            "quality_score": (75.0, 70.0, 80.0),
        }
        fig, narrative = AnalyticsEngine.chart_bootstrap_ci({"metrics": metrics})
        logger.info(f"Phase F: Bootstrap generated ({len(narrative)} chars narrative)")
        return narrative
    except Exception as e:
        return f"Phase F Error: {str(e)}"

# ============================================================================
# CALLBACKS: Phase B (Moran's I)
# ============================================================================

@callback(
    Output("morans-narrative", "children"),
    [Input("test-data-store", "data")],
    prevent_initial_call=True
)
def update_morans(data_dict):
    """Update Phase B Moran's I chart."""
    try:
        if not data_dict or "spatial" not in data_dict:
            return "Waiting for data..."

        gdf = gpd.GeoDataFrame(data_dict["spatial"])
        fig, narrative = AnalyticsEngine.chart_morans_i({"spatial": gdf})
        logger.info(f"Phase B: Moran's I generated ({len(narrative)} chars narrative)")
        return narrative
    except Exception as e:
        return f"Phase B Error: {str(e)}"

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Analytics Integration Test Dashboard")
    print("="*70)
    print("\nStarting server on http://localhost:8050")
    print("Testing all 5 analytics methods (Phase B-F)")
    print("\nPress Ctrl+C to stop\n")
    app.run_server(debug=True, port=8050, host="127.0.0.1")
