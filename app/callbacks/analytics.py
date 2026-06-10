import json
from datetime import datetime

import dash
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html, no_update

from app.services.analytics_service import (
    get_analysis_history,
    run_dataset_audit,
    synthesize_executive_summary,
)
from app.viz_engine import VisualizationEngine


# --- SSE Multiplexing Support ---
def sse_event_formatter(data, event_id=None, comment=None):
    """Format data as Server-Sent Event for high-volume dashboard streaming."""
    event = ""
    # SSE: Resumable Streams support via event_id
    if event_id: event += f"id: {event_id}\n"
    # SSE: Keep-alive comments
    if comment: event += f": {comment}\n"
    event += f"data: {json.dumps(data)}\n\n"
    return event

# --- X-Accel-Buffering: no ---
# NOTE: To fully implement 'Bypass Buffering', set header in FastAPI/Nginx
# This is handled in the server-side proxy layer.

def register_analytics_callbacks(app, dm_instance):
    @app.callback(
        Output("audit-results-container", "children"),
        Input("btn-run-audit", "n_clicks"),
        State("audit-dataset-select", "value"),
        prevent_initial_call=True
    )
    def handle_toolbox_audit(n_clicks, dataset_key):
        if not n_clicks: return no_update
        result = run_dataset_audit(dm_instance.manager, dataset_key)
        if not result["success"]:
            return dmc.Alert(result["error"], title="Audit Failed", color="red")
        moments = result["data"].get("four_moments", {})
        return dmc.Stack([
            dmc.Text(f"Audit completed at {result['timestamp']}", size="xs", c="gray"),
            dmc.Group([
                dmc.Badge(f"{len(moments)} Columns Audited", color="blue"),
                dmc.Badge(f"{len(result['data'].get('outliers', {}))} Outliers Found", color="orange")
            ]),
            dmc.Code(json.dumps(result["data"], indent=2), block=True)
        ])

    @app.callback(
        Output("summary-output-container", "children"),
        Input("btn-gen-summary", "n_clicks"),
        State("summary-input", "value"),
        prevent_initial_call=True
    )
    def handle_toolbox_summary(n_clicks, raw_input):
        if not n_clicks: return no_update
        summary = synthesize_executive_summary(raw_input)
        return dmc.TypographyStylesProvider(children=dcc.Markdown(summary))

    @app.callback(
        Output("analysis-history-table", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False
    )
    def refresh_analysis_history(pathname):
        if pathname != "/toolbox": return no_update
        history = get_analysis_history(dm_instance.manager)
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
            html.Thead(html.Tr([html.Th("Timestamp"), html.Th("Skill"), html.Th("Dataset"), html.Th("Status")])),
            html.Tbody(rows)
        ]

    @app.callback(
        [Output({"type": "visualization-graph", "index": dash.ALL}, "figure"),
         Output({"type": "statistical-moments", "index": dash.ALL}, "children"),
         Output({"type": "ai-insight-text", "index": dash.ALL}, "children"),
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
            return [[go.Figure()] * len(graph_ids), [[dmc.ListItem("PENDING")] * 4] * len(graph_ids), [dmc.Text("Pending initialization...")] * len(graph_ids), current_log]

        data_bundle = dm_instance.fetch_all_datasets(force_refresh=False)
        registry = dm_instance.get_dataset_registry()

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

        requested_keys = []
        for g_id in graph_ids:
            k = g_id['index'].replace("viz-", "").replace("-", "_")
            if k == "weekly_heat": k = "built"
            elif k == "mappluto_far": k = "mappluto"
            elif k == "311_treemap": k = "treemap"
            requested_keys.append(k)

        charts = VisualizationEngine.get_all_charts(filtered_bundle, registry, requested_keys=requested_keys)

        figures, moments_lists, insights = [], [], []
        for k in requested_keys:
            # Unpack tuple returned by new VisualizationEngine
            res = charts.get(k, (go.Figure(), "Analysis pending or data unavailable."))
            if isinstance(res, tuple) and len(res) == 2:
                fig, insight_text = res
            else:
                fig, insight_text = res, "Legacy format detected."

            figures.append(fig)
            insights.append(dcc.Markdown(insight_text))

            ds_key = "inspection"
            if k in ["built", "velocity"]: ds_key = "built"
            elif k == "violations": ds_key = "violations"
            elif k in ["lot", "mappluto"]: ds_key = "lot_info"
            df = filtered_bundle.get(ds_key, pd.DataFrame())
            if not df.empty:
                num_col = df.select_dtypes(include=[np.number]).columns[0] if not df.select_dtypes(include=[np.number]).empty else None
                if num_col:
                    m = VisualizationEngine.calculate_four_moments(df[num_col])
                    moments_lists.append([
                        dmc.ListItem(f"Mean: {m['mean']:,.2f}"),
                        dmc.ListItem(f"Variance: {m['variance']:,.2f}"),
                        dmc.ListItem(f"Skewness: {m['skewness']:.2f}"),
                        dmc.ListItem(f"Kurtosis: {m['kurtosis']:.2f}"),
                    ])
                else: moments_lists.append([dmc.ListItem("Moments: N/A (Non-numeric)")] * 4)
            else: moments_lists.append([dmc.ListItem("Moments: PENDING")] * 4)

        entry = dmc.Text(f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: Populated {len(figures)} assets on {pathname}", size="xs", c="green")
        current_log.insert(0, entry)
        return [figures, moments_lists, insights, current_log]
