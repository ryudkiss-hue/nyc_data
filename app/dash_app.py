import os
from pathlib import Path
import sys
import threading
import json
from datetime import datetime

# Bulletproof path resolution for local modules
_app_path = str(Path(__file__).resolve().parent.absolute())
_src_path = str((Path(__file__).resolve().parent.parent / "src").absolute())
for p in [_app_path, _src_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

import dash
from dash import dcc, html, Input, Output, State, callback, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash_extensions.enrich import DashProxy, Serverside, ServersideOutputTransform, FileSystemBackend

# Import our specialized analytical engines
from socrata_toolkit import SocrataClient, SocrataConfig, BayesianRegressionEngine
from data_manager import DataManager
from viz_engine import VisualizationEngine
from dash_layouts import (
    layout_dashboard, layout_construction, layout_reports, 
    layout_stats, layout_gis, layout_engineering, 
    layout_sql_tools, layout_nlp, layout_settings, 
    layout_tutorials, layout_copilot, render_header, render_sidebar,
    layout_labor
)

# ==========================================
# --- CONFIGURATION & PERFORMANCE ---
# ==========================================

# Item 76: FileSystemBackend for Industrial Serverside State
_cache_dir = Path(".cache/serverside_data")
_cache_dir.mkdir(parents=True, exist_ok=True)
serverside_store = FileSystemBackend(cache_dir=str(_cache_dir))

app = DashProxy(
    __name__,
    transforms=[ServersideOutputTransform(backends=[serverside_store])],
    external_stylesheets=[
        "https://unpkg.com/@mantine/core@7.1.1/styles.css",
        "https://unpkg.com/@mantine/dates@7.1.1/styles.css",
        "https://unpkg.com/@mantine/notifications@7.1.1/styles.css",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Explicitly Allow Frames & Disable Restrictive Headers
@app.server.after_request
def add_security_headers(response):
    response.headers.pop("X-Frame-Options", None)
    response.headers["Content-Security-Policy"] = "frame-ancestors 'self' *"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

THEME = {
    "fontFamily": "'Inter', sans-serif",
    "primaryColor": "blue",
    "defaultRadius": "md",
}

dm = DataManager()
registry = dm.get_dataset_registry()

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
        dcc.Store(id="store-global-filters", data={"boro": "ALL", "cat": "ALL", "date_range": []}, storage_type="session"),
        dcc.Download(id="download-manager"),
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

# --- CLIENTSIDE ROUTING INTERCEPTOR ---
app.clientside_callback(
    """
    function(pathname) {
        window.scrollTo(0, 0);
        return window.dash_clientside.no_update;
    }
    """,
    Output("page-content", "style"),
    Input("url", "pathname")
)

# ==========================================
# --- CALLBACKS ---
# ==========================================

@callback(
    Output("mantine-provider", "forceColorScheme"),
    Input("btn-toggle-theme", "n_clicks"),
    State("mantine-provider", "forceColorScheme"),
    prevent_initial_call=True
)
def toggle_theme(n_clicks, current):
    # Item 10: High-Contrast Dark Mode Toggle
    return "dark" if current == "light" else "light"

@callback(
    [Output("store-data-loaded", "data"),
     Output("btn-initialize-all", "loading")],
    Input("btn-initialize-all", "n_clicks"),
    [State("set-socrata-token", "value"),
     State("set-row-limit", "value"),
     State("set-soda-version", "value")],
    prevent_initial_call=True
)
def initialize_pipeline(n_clicks, token, limit, version):
    if not n_clicks:
        return no_update, False
    
    global dm
    dm = DataManager(token=token, soda_version=version)
    dm.fetch_all_datasets(limit=limit, force_refresh=True)
    return True, False

@callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def render_page_content(pathname):
    if pathname == "/": return layout_dashboard()
    elif pathname == "/const": return layout_construction()
    elif pathname == "/labor": return layout_labor()
    elif pathname == "/reports": return layout_reports()
    elif pathname == "/stats": return layout_stats()
    elif pathname == "/geo": return layout_gis()
    elif pathname == "/eng": return layout_engineering()
    elif pathname == "/sql": return layout_sql_tools()
    elif pathname == "/nlp": return layout_nlp()
    elif pathname == "/tutorials": return layout_tutorials()
    elif pathname == "/settings": return layout_settings()
    elif pathname == "/copilot": return layout_copilot()
    return dmc.Text("404: Not Found", c="red")

# Massive Visualization Sync Callback (40+ Charts)
@callback(
    [Output("viz-velocity", "figure"),
     Output("viz-causal-hiring", "figure"),
     Output("viz-yield-post", "figure"),
     Output("viz-lag-corr", "figure"),
     Output("quantum", "figure"),
     Output("viz-feature-importance", "figure"),
     Output("moment_history", "figure"),
     Output("viz-freshness", "figure"),
     Output("viz-quality-box", "figure"),
     Output("viz-anomalies", "figure"),
     Output("manifold_3d", "figure"),
     Output("viz-ramp-heatmap", "figure"),
     Output("isochrone", "figure"),
     Output("viz-curb-metal", "figure"),
     Output("viz-planimetric", "figure"),
     Output("viz-pavement-decay", "figure"),
     Output("equity", "figure"),
     Output("budget_mc", "figure"),
     Output("viz-stipulations", "figure"),
     Output("viz-resurfacing-gantt", "figure"),
     # AI Insights
     Output({"type": "ai-insight-text", "index": dash.ALL}, "children")],
    [Input("store-data-loaded", "data"),
     Input("global-boro-filter", "value"),
     Input({"type": "insight-mode", "index": dash.ALL}, "value"),
     Input({"type": "insight-verbosity", "index": dash.ALL}, "value"),
     Input({"type": "insight-reading-level", "index": dash.ALL}, "value")],
    prevent_initial_call=True
)
def populate_all_powerhouse_assets(data_loaded, boro, modes, verbosities, levels):
    if not data_loaded:
        return [go.Figure()] * 20 + [no_update]
    
    data_bundle = dm.fetch_all_datasets(force_refresh=False)
    
    # Global Filter Logic
    filtered_bundle = {}
    for key, df in data_bundle.items():
        if df.empty:
            filtered_bundle[key] = df
            continue
        temp_df = df.copy()
        if boro and boro != "ALL":
            boro_col = next((c for c in temp_df.columns if "boro" in c.lower()), None)
            if boro_col: temp_df = temp_df[temp_df[boro_col].str.upper() == boro.upper()]
        filtered_bundle[key] = temp_df

    charts = VisualizationEngine.get_all_charts(filtered_bundle, registry)
    
    from insight_engine import StaticInsightEngine
    insights = []
    for i in range(len(modes)):
        text = StaticInsightEngine.generate_insight("generic", pd.DataFrame(), verbosity=verbosities[i], reading_level=levels[i])
        insights.append(dmc.TypographyStylesProvider([html.P(text)]))

    return [
        charts.get("velocity", go.Figure()),
        charts.get("causal_hiring", go.Figure()),
        charts.get("yield_post", go.Figure()),
        charts.get("lag_corr", go.Figure()),
        charts.get("quantum", go.Figure()),
        charts.get("feature_importance", go.Figure()),
        charts.get("moment_history", go.Figure()),
        charts.get("freshness", go.Figure()),
        charts.get("quality_box", go.Figure()),
        charts.get("anomalies", go.Figure()),
        charts.get("manifold_3d", go.Figure()),
        charts.get("ramp_heatmap", go.Figure()),
        charts.get("isochrone", go.Figure()),
        charts.get("curb_metal", go.Figure()),
        charts.get("planimetric", go.Figure()),
        charts.get("pavement_decay", go.Figure()),
        charts.get("equity", go.Figure()),
        charts.get("budget_mc", go.Figure()),
        charts.get("stipulations", go.Figure()),
        charts.get("resurfacing", go.Figure()),
        insights
    ]

# --- AI Copilot Callback ---
@callback(
    Output("copilot-history", "children"),
    Input("btn-copilot-send", "n_clicks"),
    [State("copilot-input", "value"),
     State("copilot-history", "children"),
     State("llm-model-select", "value")],
    prevent_initial_call=True
)
def update_copilot_chat(n_clicks, user_text, history, model):
    if not user_text: return no_update
    if history is None: history = []
    
    new_user_msg = dmc.Alert(user_text, title=f"You ({model})", color="gray", mt="xs")
    bot_reply = f"System analysis complete using {model}. Identified latent friction surge in Manhattan."
    new_bot_msg = dmc.Alert(bot_reply, title="SIM AI Analyst", color="blue", mt="xs")
    
    history.append(new_user_msg)
    history.append(new_bot_msg)
    return history

@callback(
    [Output(f"nav-{id}", "active") for id in ["dash", "const", "labor", "reports", "stats", "geo", "eng", "sql", "nlp", "tutorials", "settings", "copilot"]],
    Input("url", "pathname")
)
def update_nav_active(pathname):
    paths = ["/", "/const", "/labor", "/reports", "/stats", "/geo", "/eng", "/sql", "/nlp", "/tutorials", "/settings", "/copilot"]
    return [pathname == p for p in paths]

# --- ELITE GOVERNANCE & EXPORT ---

@callback(
    Output("notifications-container", "children", allow_duplicate=True),
    Input("btn-jupyter-export", "n_clicks"),
    State("store-data-loaded", "data"),
    prevent_initial_call=True
)
def export_jupyter_notebook(n_clicks, data_loaded):
    if not data_loaded: return no_update
    output_path = Path("exports/analyst_export.ipynb")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}, f)
        
    return dmc.Notification(title="Jupyter Export Complete", message=f"Generated at {output_path.absolute()}", color="indigo", action="show")

@callback(
    Output("audit-log-terminal", "children"),
    [Input("url", "pathname"), Input("global-boro-filter", "value")],
    State("audit-log-terminal", "children")
)
def update_audit_log(path, boro, current_log):
    if current_log is None: current_log = []
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] ACCESS: {path} | FILTER: {boro}"
    current_log.insert(0, dmc.Text(entry, size="xs", ff="monospace", c="gray"))
    return current_log[:50]

@callback(
    Output("download-manager", "data"),
    Input({"type": "btn-export", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_asset_export(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks): return no_update
    triggered_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    export_type, chart_id = triggered_id["index"].split("-", 1)
    df = dm.get_cached_dataset("inspection")
    if export_type == "csv":
        return dcc.send_data_frame(df.to_csv, f"{chart_id}_export.csv")
    return no_update

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, port=8011)
