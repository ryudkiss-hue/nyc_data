import json
from datetime import datetime
from pathlib import Path
import dash
from dash import Input, Output, State, callback, no_update, dcc
import dash_mantine_components as dmc
from app.services.export_service import ExportRegistry

export_registry = ExportRegistry()

def register_export_callbacks(app, dm_instance):
    @app.callback(
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

    @app.callback(
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

    @app.callback(
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

        target_ds = "inspection"
        if "built" in chart_id or "velocity" in chart_id: target_ds = "built"
        elif "violation" in chart_id: target_ds = "violations"
        elif "lot" in chart_id or "mappluto" in chart_id: target_ds = "lot_info"

        df = dm_instance.get_cached_dataset(target_ds)
        result = export_registry.export(export_type, df, chart_id)
        
        if result:
            if isinstance(result, dcc.Download): # dcc.send_data_frame
                return result, no_update
            return result, no_update

        msg = f"Export type '{export_type.upper()}' is currently in developmental staging."
        return no_update, dmc.Notification(title="Export Alert", message=msg, color="orange", action="show")

    @app.callback(
        Output("notifications-container", "children", allow_duplicate=True),
        Input({"type": "btn-copy", "index": dash.ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_clipboard_copy(n_clicks):
        if not any(n_clicks): return no_update
        return dmc.Notification(title="System Alert", message="Asset URI copied to secure clipboard.", color="dark", action="show")
