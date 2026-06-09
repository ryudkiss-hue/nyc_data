import os
import threading
import dash
from dash import Input, Output, State, callback, no_update
import dash_mantine_components as dmc
from app.data_manager import DataManager

# Global state for ingestion tracking (Shared across module)
ingestion_status = {"active": False, "progress": 0, "error": None, "finished": False}

def run_ingestion_background(token, limit, version):
    global ingestion_status

    ingestion_status["active"] = True
    ingestion_status["error"] = None
    ingestion_status["finished"] = False
    try:
        # Note: dm is expected to be a global or passed in. 
        # For simple decomposition, we'll assume DataManager is re-instantiated or uses a shared cache.
        dm = DataManager(token=token, soda_version=version)
        dm.fetch_all_datasets(limit=limit, force_refresh=True)
        
        # Link CMMS alerts to contractor records and SLA tracking
        cmms_data = [] # In real scenario, fetch or get CMMS alerts
        contractor_records = [] # In real scenario, fetch or get contractor records
        dm.link_cmms_to_contractor(cmms_data, contractor_records)
        
        ingestion_status["finished"] = True
    except Exception as e:
        ingestion_status["error"] = str(e)
    finally:
        ingestion_status["active"] = False

def initialize_pipeline(n_clicks, token_list, limit_list, version_list):
    if not n_clicks or not any(n_clicks) or ingestion_status["active"]:
        return no_update, [False] * len(n_clicks) if not ingestion_status["active"] else no_update

    token = token_list[0] if token_list else os.getenv("SOCRATA_APP_TOKEN", "")
    limit = limit_list[0] if limit_list else 5000
    version = version_list[0] if version_list else "3.0"

    val = int(limit or 5000)
    actual_limit = -1 if val <= 0 else val

    thread = threading.Thread(target=run_ingestion_background, args=(token, actual_limit, version))
    thread.daemon = True
    thread.start()

    return no_update, [True] * len(n_clicks)

def register_ingestion_callbacks(app, dm_instance):
    @app.callback(
        [Output("store-data-loaded", "data"),
         Output({"type": "init-btn", "index": dash.ALL}, "loading")],
        Input({"type": "init-btn", "index": dash.ALL}, "n_clicks"),
        [State({"type": "config-input", "index": "token"}, "value"),
         State({"type": "config-input", "index": "limit"}, "value"),
         State({"type": "config-input", "index": "version"}, "value")],
        prevent_initial_call=True
    )
    def initialize_pipeline_callback(n_clicks, token_list, limit_list, version_list):
        return initialize_pipeline(n_clicks, token_list, limit_list, version_list)

    @app.callback(
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
                    return False, False, dmc.Notification(title="Ingestion Failed", message=ingestion_status["error"], color="red", action="show")
                if ingestion_status["finished"]:
                    ingestion_status["finished"] = False
                    return True, False, dmc.Notification(title="Ingestion Complete", message="26 datasets loaded successfully.", color="green", action="show")
            return no_update, False, no_update

        # Progress Feedback Logic
        if dm_instance and hasattr(dm_instance, "progress"):
            p = dm_instance.progress
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

    @app.callback(
        Output({"type": "init-btn", "index": dash.ALL}, "loading", allow_duplicate=True),
        Input("store-ingestion-active", "data"),
        State({"type": "init-btn", "index": dash.ALL}, "id"),
        prevent_initial_call=True
    )
    def sync_init_btn_loading(is_active, btn_ids):
        return [is_active] * len(btn_ids)
