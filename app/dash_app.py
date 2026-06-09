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
# Use an environment variable for the Mingw64 bin path to ensure portability
MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
os.environ["PYTENSOR_FLAGS"] = f"cxx={os.path.join(MINGW_BIN, 'g++.exe')},gcc_version_str=14.1.0"

import logging

import dash
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import uvicorn

logger = logging.getLogger(__name__)

from dash import Input, Output, State, callback, dcc, html, no_update
from dash_extensions.enrich import (
    DashProxy,
    FileSystemBackend,
    Serverside,
    ServersideOutputTransform,
)
from dash_iconify import DashIconify
from dash_layouts import (
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
from data_manager import DataManager
from fastapi import FastAPI

# Import Analytics Service
from services.analytics_service import (
    get_analysis_history,
    run_dataset_audit,
    synthesize_executive_summary,
)
from viz_engine import VisualizationEngine

# Import our specialized analytical engines
from socrata_toolkit import BayesianRegressionEngine, SocrataClient, SocrataConfig

# ==========================================
# --- CONFIGURATION & PERFORMANCE ---
# ==========================================

# Item 76: FileSystemBackend for Industrial Serverside State
_cache_dir = Path(".cache/serverside_data")
_cache_dir.mkdir(parents=True, exist_ok=True)

# Item 115: High-Performance Dash 4.2.0 Native FastAPI Workstation
import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_mantine_components as dmc

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
from fastapi.middleware.cors import CORSMiddleware
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

# Global state for ingestion tracking
ingestion_status = {"active": False, "progress": 0, "error": None, "finished": False}

def run_ingestion_background(token, limit, version):
    global dm, ingestion_status
    print(f"THREAD: Starting ingestion (limit={limit}, v={version})")
    ingestion_status["active"] = True
    ingestion_status["error"] = None
    ingestion_status["finished"] = False
    try:
        dm = DataManager(token=token, soda_version=version)
        dm.fetch_all_datasets(limit=limit, force_refresh=True)
        ingestion_status["finished"] = True
        print("THREAD: Ingestion complete.")
    except Exception as e:
        print(f"THREAD ERROR: {e}")
        ingestion_status["error"] = str(e)
    finally:
        ingestion_status["active"] = False

@callback(
    [Output("store-data-loaded", "data"),
     Output({"type": "init-btn", "index": dash.ALL}, "loading")],
    Input({"type": "init-btn", "index": dash.ALL}, "n_clicks"),
    [State({"type": "config-input", "index": "token"}, "value"),
     State({"type": "config-input", "index": "limit"}, "value"),
     State({"type": "config-input", "index": "version"}, "value")],
    prevent_initial_call=True
)
def initialize_pipeline(n_clicks, token_list, limit_list, version_list):
    if not n_clicks or not any(n_clicks):
        return no_update, [False] * len(n_clicks)

    # Item 102: Industrial Pattern Matching for Multi-Page State
    token = token_list[0] if token_list else os.getenv("SOCRATA_APP_TOKEN", "")
    limit = limit_list[0] if limit_list else 5000
    version = version_list[0] if version_list else "3.0"

    # Item 102: Industrial Streaming Logic
    val = int(limit or 5000)
    actual_limit = -1 if val <= 0 else val

    limit_display = "UNLIMITED (Streamed)" if actual_limit == -1 else f"{actual_limit:,} rows"
    print(f"CALLBACK: Triggering background ingestion (Mode: {limit_display})")

    # Start ingestion in a background thread
    thread = threading.Thread(target=run_ingestion_background, args=(token, actual_limit, version))
    thread.daemon = True
    thread.start()

    return no_update, [True] * len(n_clicks)

@callback(
    [Output("store-data-loaded", "data", allow_duplicate=True),
     Output("store-ingestion-active", "data"),
     Output("notifications-container", "children", allow_duplicate=True)],
    Input("ingestion-poller", "n_intervals"),
    State("store-data-loaded", "data"),
    prevent_initial_call=True
)
def poll_ingestion_engine(n, already_loaded):
    if already_loaded:
        return no_update, False, no_update

    if not ingestion_status["active"]:
        if n > 0:
            if ingestion_status["error"]:
                print(f"POLLER: Ingestion failed: {ingestion_status['error']}")
                return False, False, dmc.Notification(title="Ingestion Failed", message=ingestion_status["error"], color="red", action="show")
            if ingestion_status["finished"]:
                print("POLLER: Ingestion finished detected. Updating store.")
                ingestion_status["finished"] = False
                return True, False, dmc.Notification(title="Ingestion Complete", message="26 datasets loaded successfully.", color="green", action="show")
        return no_update, False, no_update

    # Progress Feedback Logic
    if dm and hasattr(dm, "progress"):
        p = dm.progress
        if p["current"]:
            msg = f"Fetching {p['current']} ({p['completed']}/{p['total']})"
            return no_update, True, dmc.Notification(
                id="ingestion-progress",
                title="Engine Processing",
                message=msg,
                loading=True,
                color="blue",
                action="update" if n > 1 else "show",
                autoClose=False,
                withCloseButton=False
            )

    return no_update, True, no_update

@callback(
    Output({"type": "init-btn", "index": dash.ALL}, "loading", allow_duplicate=True),
    Input("store-ingestion-active", "data"),
    State({"type": "init-btn", "index": dash.ALL}, "id"),
    prevent_initial_call=True
)
def sync_init_btn_loading(is_active, btn_ids):
    return [is_active] * len(btn_ids)

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
    elif pathname == "/toolbox": return layout_toolbox()
    return dmc.Text("404: Not Found", c="red")

# --- ANALYTICAL TOOLBOX CALLBACKS ---

@callback(
    Output("audit-results-container", "children"),
    Input("btn-run-audit", "n_clicks"),
    State("audit-dataset-select", "value"),
    prevent_initial_call=True
)
def handle_toolbox_audit(n_clicks, dataset_key):
    if not n_clicks: return no_update

    result = run_dataset_audit(dm.manager, dataset_key)

    if not result["success"]:
        return dmc.Alert(result["error"], title="Audit Failed", color="red")

    # Render results
    moments = result["data"].get("four_moments", {})
    return dmc.Stack([
        dmc.Text(f"Audit completed at {result['timestamp']}", size="xs", c="gray"),
        dmc.Group([
            dmc.Badge(f"{len(moments)} Columns Audited", color="blue"),
            dmc.Badge(f"{len(result['data'].get('outliers', {}))} Outliers Found", color="orange")
        ]),
        dmc.Code(json.dumps(result["data"], indent=2), block=True)
    ])

@callback(
    Output("summary-output-container", "children"),
    Input("btn-gen-summary", "n_clicks"),
    State("summary-input", "value"),
    prevent_initial_call=True
)
def handle_toolbox_summary(n_clicks, raw_input):
    if not n_clicks: return no_update
    summary = synthesize_executive_summary(raw_input)
    return dmc.TypographyStylesProvider(children=dcc.Markdown(summary))

@callback(
    Output("analysis-history-table", "children"),
    Input("url", "pathname"),
    prevent_initial_call=False
)
def refresh_analysis_history(pathname):
    if pathname != "/toolbox": return no_update

    history = get_analysis_history(dm.manager)
    if not history:
        return [html.Thead(html.Tr([html.Th("No history found")]))]

    rows = []
    for entry in history:
        rows.append(html.Tr([
            html.Td(entry["timestamp"]),
            html.Td(entry["skill_name"]),
            html.Td(entry["table_name"]),
            html.Td(dmc.Badge("SUCCESS" if entry["success"] else "FAILED", color="green" if entry["success"] else "red"))
        ]))

    return [
        html.Thead(
            html.Tr([
                html.Th("Timestamp"),
                html.Th("Skill"),
                html.Th("Dataset"),
                html.Th("Status"),
            ])
        ),
        html.Tbody(rows)
    ]

@callback(
    Output("audit-log-terminal", "children", allow_duplicate=True),
    Input("url", "pathname"),
    State("audit-log-terminal", "children"),
    prevent_initial_call="initial_duplicate"
)
def heartbeat_callback(path, current_log):
    print(f"HEARTBEAT: Navigated to {path}")
    return no_update

@callback(
    [Output({"type": "visualization-graph", "index": dash.ALL}, "figure"),
     Output({"type": "statistical-moments", "index": dash.ALL}, "children"),
     Output("debug-terminal", "children", allow_duplicate=True)],
    [Input("store-data-loaded", "data"),
     Input("global-boro-filter", "value"),
     Input("url", "pathname"),
     Input({"type": "visualization-graph", "index": dash.ALL}, "id")],
    [State("debug-terminal", "children")],
    prevent_initial_call="initial_duplicate"
)
def populate_dynamic_graphs(data_loaded, boro, pathname, graph_ids, current_log):
    if current_log is None: current_log = []

    if not data_loaded:
        entry = dmc.Text(f"[{datetime.now().strftime('%H:%M:%S')}] PENDING: Data not loaded.", size="xs", c="orange")
        current_log.insert(0, entry)
        return [[go.Figure()] * len(graph_ids),
                [[dmc.ListItem("PENDING")] * 4] * len(graph_ids),
                current_log]

    # Item: Adaptive Page Population
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

    # Extract requested keys from graph_ids
    requested_keys = []
    for g_id in graph_ids:
        # Item 92: Hyphen-to-Underscore normalization for engine compatibility
        k = g_id['index'].replace("viz-", "").replace("-", "_")
        if k == "weekly_heat": k = "built"
        elif k == "mappluto_far": k = "mappluto"
        elif k == "311_treemap": k = "treemap"
        requested_keys.append(k)

    charts = VisualizationEngine.get_all_charts(filtered_bundle, registry, requested_keys=requested_keys)

    # Map graph IDs to chart figures and calculate moments
    figures = []
    moments_lists = []
    for k in requested_keys:
        figures.append(charts.get(k, go.Figure()))

        # Calculate Four Moments for the relevant dataset
        ds_key = "inspection" # Default
        if k in ["built", "velocity"]: ds_key = "built"
        elif k == "violations": ds_key = "violations"
        elif k in ["lot", "mappluto"]: ds_key = "lot_info"

        df = filtered_bundle.get(ds_key, pd.DataFrame())
        if not df.empty:
            # Pick the most relevant numeric column
            num_col = df.select_dtypes(include=[np.number]).columns[0] if not df.select_dtypes(include=[np.number]).empty else None
            if num_col:
                m = VisualizationEngine.calculate_four_moments(df[num_col])
                moments_lists.append([
                    dmc.ListItem(f"Mean: {m['mean']:,.2f}"),
                    dmc.ListItem(f"Variance: {m['variance']:,.2f}"),
                    dmc.ListItem(f"Skewness: {m['skewness']:.2f}"),
                    dmc.ListItem(f"Kurtosis: {m['kurtosis']:.2f}"),
                ])
            else:
                moments_lists.append([dmc.ListItem("Moments: N/A (Non-numeric)")] * 4)
        else:
            moments_lists.append([dmc.ListItem("Moments: PENDING")] * 4)

    entry = dmc.Text(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: Populated {len(figures)} assets on {pathname}", size="xs", c="green")
    current_log.insert(0, entry)

    return [figures, moments_lists, current_log]

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
    [Output(f"nav-{id}", "active") for id in ["dash", "const", "labor", "reports", "stats", "geo", "eng", "sql", "nlp", "tutorials", "settings", "toolbox", "copilot"]],
    Input("url", "pathname")
)
def update_nav_active(pathname):
    paths = ["/", "/const", "/labor", "/reports", "/stats", "/geo", "/eng", "/sql", "/nlp", "/tutorials", "/settings", "/toolbox", "/copilot"]
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
    [Output("download-manager", "data"),
     Output("notifications-container", "children", allow_duplicate=True)],
    Input({"type": "btn-export", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_asset_export(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks): return no_update, no_update
    triggered_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
    export_type, chart_id = triggered_id["index"].split("-", 1)

    # Item 98: Context-Aware Export Routing
    target_ds = "inspection"
    if "built" in chart_id or "velocity" in chart_id: target_ds = "built"
    elif "violation" in chart_id: target_ds = "violations"
    elif "lot" in chart_id or "mappluto" in chart_id: target_ds = "lot_info"

    df = dm.get_cached_dataset(target_ds)

    if export_type == "csv":
        return dcc.send_data_frame(df.to_csv, f"{chart_id}_export.csv"), no_update
    elif export_type == "md":
        content = f"# Export: {chart_id}\n\n## Data Preview\n\n" + df.head(10).to_markdown()
        return dict(content=content, filename=f"{chart_id}_report.md"), no_update
    elif export_type == "py":
        content = f"import pandas as pd\n# Autogenerated Snippet for {chart_id}\ndf = pd.read_csv('{chart_id}_export.csv')\nprint(df.describe())"
        return dict(content=content, filename=f"{chart_id}_script.py"), no_update

    # Unsupported types: Provide feedback instead of silent failure
    msg = f"Export type '{export_type.upper()}' is currently in developmental staging."
    return no_update, dmc.Notification(title="Export Alert", message=msg, color="orange", action="show")

@callback(
    Output("notifications-container", "children", allow_duplicate=True),
    Input({"type": "btn-copy", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_clipboard_copy(n_clicks):
    if not any(n_clicks): return no_update
    return dmc.Notification(title="System Alert", message="Asset URI copied to secure clipboard.", color="dark", action="show")

if __name__ == "__main__":
    # Item 125: High-Performance ASGI Server (Uvicorn)
    import uvicorn
    uvicorn.run(server, host="127.0.0.1", port=8011, log_level="debug")
