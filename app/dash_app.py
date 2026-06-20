"""
Dash Mission Control — PRIMARY UI Framework

FastAPI-backed Dash/Plotly dashboard with Mantine UI for NYC DOT SIM analysis.
This is the primary entry point for the Mission Control dashboard.

Launch:
  python app/dash_app.py         → http://localhost:8011 (PRIMARY — Dash)
  python main.py                  → Launcher shim (auto-selects primary UI)
  streamlit run app/app.py        → http://localhost:8501 (SECONDARY — Streamlit alternative)

Architecture:
  - Backend: FastAPI (async, production-grade)
  - Frontend: Dash 4.2 with Mantine UI components
  - Charts: Plotly interactive visualizations
  - State: dcc.Store for reactive updates
  - Callbacks: Real-time filter + export pipelines
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bulletproof path resolution for local modules
_app_path = str(Path(__file__).resolve().parent.absolute())
_src_path = str((Path(__file__).resolve().parent.parent / "src").absolute())
for p in [_app_path, _src_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

if sys.platform.startswith("win"):
    MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
    os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
    os.environ["PYTENSOR_FLAGS"] = (
        f"cxx={os.path.join(MINGW_BIN, 'g++.exe')},gcc_version_str=14.1.0"
    )

import logging

import dash
import dash_mantine_components as dmc
import uvicorn
from dash import dcc, html
from fastapi.middleware.cors import CORSMiddleware

from app.callbacks.analytics import register_analytics_callbacks
from app.callbacks.copilot import register_copilot_callbacks
from app.callbacks.export import register_export_callbacks
from app.callbacks.ingestion import register_ingestion_callbacks

# Import Modular Callbacks
from app.callbacks.navigation import register_navigation_callbacks
from app.components.filter_system import register_filter_callbacks
from app.components.kpi_cards import register_kpi_callbacks
from app.dash_layouts import (
    layout_construction,
    layout_copilot,
    layout_dashboard,
    layout_engineering,
    layout_gis,
    layout_labor,
    layout_nlp,
    layout_reports,
    layout_settings,
    layout_sql_tools,
    layout_stats,
    layout_toolbox,
    layout_tutorials,
    render_header,
    render_sidebar,
)
from app.data_manager import DataManager

logger = logging.getLogger(__name__)

# ==========================================
# --- CONFIGURATION & PERFORMANCE ---
# ==========================================

# Item 76: FileSystemBackend for Industrial Serverside State
_cache_dir = Path(".cache/serverside_data")
_cache_dir.mkdir(parents=True, exist_ok=True)

# Item: Industrial "Enterprise" Cache (Manual Serverside Offloading)
import diskcache

_serverside_cache = diskcache.Cache(".cache/serverside_manual")

# Native Dash 4.2.0 "The Freedom Update"
app = dash.Dash(
    __name__,
    backend="fastapi",
    external_stylesheets=[
        "https://unpkg.com/@mantine/core@8.0.0-alpha.1/styles.css",
        "https://unpkg.com/@mantine/dates@8.0.0-alpha.1/styles.css",
        "https://unpkg.com/@mantine/notifications@8.0.0-alpha.1/styles.css",
        "https://unpkg.com/@mantine/charts@8.0.0-alpha.1/styles.css",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server


@server.get("/api/v1/health")
async def health_check():
    return {"status": "optimized", "engine": "FastAPI (Dash 4.2 Native)", "mode": "Enterprise"}


# Item 118: Industrial Security via FastAPI Middleware
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

THEME = {
    "fontFamily": "'Inter', sans-serif",
    "primaryColor": "blue",
    "defaultRadius": "md",
}

dm = DataManager(read_only=True)

# Initialize cache audit table for observability tracking (after DataManager to avoid DB lock)
from app.utils.cache_manager import init_cache_audit_table
try:
    # Use DataManager's existing connection to avoid locking issues
    if hasattr(dm, 'manager') and dm.manager is not None:
        init_cache_audit_table(dm.manager)
        logger.info("Cache audit table initialized successfully")
    else:
        logger.info("DataManager not ready for cache_audit init")
except Exception as e:
    logger.debug(f"Cache audit initialization deferred (non-critical): {e}")

# ==========================================
# --- APP CORE LAYOUT ---
# ==========================================

app.layout = dmc.MantineProvider(
    id="mantine-provider",
    forceColorScheme="light",
    theme=THEME,
    children=[
        html.A(
            "Skip to main content", href="#page-content", **{"aria-label": "Skip to main content"}
        ),
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="store-data-loaded", data=False, storage_type="session"),
        dcc.Store(id="store-ingestion-active", data=False, storage_type="session"),
        dcc.Store(
            id="store-global-filters",
            data={
                "boroughs": ["MN", "BK", "BX", "QN", "SI"],
                "date_start": None,
                "date_end": None,
                "metric_type": "all",
            },
            storage_type="session",
        ),
        dcc.Download(id="download-manager"),
        dcc.Interval(id="ingestion-poller", interval=2000, n_intervals=0),
        dmc.NotificationProvider(),
        html.Div(id="notifications-container"),
        dmc.AppShell(
            header={"height": 70},
            navbar={"width": 300, "breakpoint": "sm"},
            padding="md",
            children=[
                render_header(),
                render_sidebar(),
                dmc.AppShellMain(id="page-content", children=[html.Div()]),
            ],
            style={"backgroundColor": "#FFFFFF"},
        ),
    ],
)


# --- ROUTING ENGINE ---
def render_page_content(pathname):
    if pathname == "/":
        return layout_dashboard()
    elif pathname == "/const":
        return layout_construction()
    elif pathname == "/labor":
        return layout_labor()
    elif pathname == "/reports":
        return layout_reports()
    elif pathname == "/stats":
        return layout_stats()
    elif pathname == "/geo":
        return layout_gis()
    elif pathname == "/eng":
        return layout_engineering()
    elif pathname == "/sql":
        return layout_sql_tools()
    elif pathname == "/nlp":
        return layout_nlp()
    elif pathname == "/settings":
        return layout_settings()
    elif pathname == "/tutorials":
        return layout_tutorials()
    elif pathname == "/toolbox":
        return layout_toolbox()
    elif pathname == "/copilot":
        return layout_copilot()
    return dmc.Center(dmc.Text("404: Mission target not found.", size="xl", fw=700, c="red"))


# --- REGISTER CALLBACKS ---
register_navigation_callbacks(app)
register_ingestion_callbacks(app, dm)
register_analytics_callbacks(app, dm)
register_export_callbacks(app, dm)
register_copilot_callbacks(app)
register_filter_callbacks()
register_kpi_callbacks()

if __name__ == "__main__":
    # Item 125: High-Performance ASGI Server (Uvicorn)
    uvicorn.run(server, host="127.0.0.1", port=8011, log_level="debug")
