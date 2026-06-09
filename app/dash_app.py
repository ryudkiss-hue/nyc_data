import json
import os
import sys
import threading
from datetime import datetime
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

# Item 42: Bulletproof environment configuration for High-Performance Bayesian Engine
MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
os.environ["PYTENSOR_FLAGS"] = f"cxx={os.path.join(MINGW_BIN, 'g++.exe')},gcc_version_str=14.1.0"

import logging
import dash
import dash_mantine_components as dmc
import pandas as pd
import uvicorn
from dash import dcc, html, Input, Output, State, callback, no_update
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dash_layouts import render_header, render_sidebar
from app.data_manager import DataManager

# Import Modular Callbacks
from app.callbacks.navigation import register_navigation_callbacks
from app.callbacks.ingestion import register_ingestion_callbacks
from app.callbacks.analytics import register_analytics_callbacks
from app.callbacks.export import register_export_callbacks
from app.callbacks.copilot import register_copilot_callbacks

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

dm = DataManager()

# ==========================================
# --- APP CORE LAYOUT ---
# ==========================================

app.layout = dmc.MantineProvider(
    id="mantine-provider",
    forceColorScheme="light",
    theme=THEME,
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="store-data-loaded", data=False, storage_type="session"),
        dcc.Store(id="store-ingestion-active", data=False, storage_type="session"),
        dcc.Store(id="store-global-filters", data={"boro": "ALL", "cat": "ALL", "date_range": []}, storage_type="session"),
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
                dmc.AppShellMain(id="page-content", children=[html.Div()])
            ],
            style={"backgroundColor": "#FFFFFF"}
        )
    ]
)

# --- REGISTER CALLBACKS ---
register_navigation_callbacks(app)
register_ingestion_callbacks(app, dm)
register_analytics_callbacks(app, dm)
register_export_callbacks(app, dm)
register_copilot_callbacks(app)

if __name__ == "__main__":
    # Item 125: High-Performance ASGI Server (Uvicorn)
    uvicorn.run(server, host="127.0.0.1", port=8011, log_level="debug")
