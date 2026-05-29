"""Explore — what-if parameter sandbox (does not mutate pack runs)."""



from __future__ import annotations



import os

import sys

from pathlib import Path



import pandas as pd

import plotly.express as px

import plotly.graph_objects as go



import dash

import dash_ag_grid as dag

import dash_bootstrap_components as dbc

from dash import Input, Output, State, callback, ctx, dcc, html, no_update



from dash_app.components.debounce import debounce_bundle

from dash_app.components.explainers import construction_scoring_explainer

from dash_app.components.interactive import (

    feedback_toast,

    param_checkbox,

    param_slider,

    tip_card,

)

from dash_app.components.shell import empty_state, page_shell

from dash_app.data.demo_pack import copy_fixtures_to_demo, demo_construction_records, ensure_demo_pack

from dash_app.data.explore_prefs import load_explore_prefs, save_explore_prefs

from dash_app.data.pack_loader import construction_records, resolve_pack_dir

from socrata_toolkit.analyst.explore import (

    borough_bar_counts,

    normalize_weights,

    preview_priority,

    profile_weight_snippet,

)

from socrata_toolkit.engineering.construction_list import DEFAULT_PRIORITY_WEIGHTS



dash.register_page(__name__, path="/explore", name="Explore", order=1)



_prefs = load_explore_prefs()

_pack = resolve_pack_dir() or ensure_demo_pack()

_records = construction_records(_pack) if _pack else demo_construction_records()



_DEFAULTS = {

    "w_severity": _prefs.get("w_severity", DEFAULT_PRIORITY_WEIGHTS["severity"]),

    "w_volume": _prefs.get("w_volume", DEFAULT_PRIORITY_WEIGHTS["pedestrian_volume"]),

    "w_age": _prefs.get("w_age", DEFAULT_PRIORITY_WEIGHTS["age_days"]),

    "w_ada": _prefs.get("w_ada", DEFAULT_PRIORITY_WEIGHTS["ada_flag"]),

    "w_spine": _prefs.get("w_spine", DEFAULT_PRIORITY_WEIGHTS["smart_spine"]),

    "w_complaints": _prefs.get("w_complaints", DEFAULT_PRIORITY_WEIGHTS["complaint_count"]),

    "top_n": _prefs.get("top_n", 25),

    "borough": _prefs.get("borough", "ALL"),

    "conflicts_only": _prefs.get("conflicts_only", False),

    "ada_only": _prefs.get("ada_only", False),

    "buffer_m": _prefs.get("buffer_m", 0),

}



borough_opts = [{"label": "All boroughs", "value": "ALL"}]

if _records:

    df0 = pd.DataFrame(_records)

    if "borough" in df0.columns:

        for b in sorted(df0["borough"].dropna().unique()):

            borough_opts.append({"label": str(b), "value": str(b)})



_controls = html.Div(

    className="nyc-explore-panel",

    children=[

        html.H2("Controls", style={"fontSize": "1.1rem"}),

        param_slider("Severity weight", 0, 1, 0.05, _DEFAULTS["w_severity"], "explore-w-severity", aria_label="Severity weight slider"),

        param_slider("Pedestrian volume weight", 0, 1, 0.05, _DEFAULTS["w_volume"], "explore-w-volume", aria_label="Pedestrian volume weight slider"),

        param_slider("Age weight", 0, 1, 0.05, _DEFAULTS["w_age"], "explore-w-age", aria_label="Age weight slider"),

        param_slider("ADA weight", 0, 1, 0.05, _DEFAULTS["w_ada"], "explore-w-ada", aria_label="ADA weight slider"),

        param_slider("Smart Spine weight", 0, 1, 0.05, _DEFAULTS["w_spine"], "explore-w-spine", aria_label="Smart spine weight slider"),

        param_slider("Complaints weight", 0, 1, 0.05, _DEFAULTS["w_complaints"], "explore-w-complaints", aria_label="Complaints weight slider"),

        param_slider("Top N preview", 5, 100, 5, _DEFAULTS["top_n"], "explore-top-n", aria_label="Number of rows to preview"),

        param_slider("Conflict buffer (m)", 0, 50, 5, _DEFAULTS["buffer_m"], "explore-buffer-m", aria_label="Conflict buffer meters for preview"),

        html.Label("Borough filter", className="nyc-param-label"),

        dcc.Dropdown(id="explore-borough", options=borough_opts, value=_DEFAULTS["borough"], clearable=False, className="mb-2"),

        param_checkbox("Show only conflicts", "explore-conflicts-only", default=_DEFAULTS["conflicts_only"]),

        param_checkbox("ADA locations only", "explore-ada-only", default=_DEFAULTS["ada_only"]),

        html.Div(

            [

                html.Button("Reset to profile defaults", id="explore-reset", className="nyc-btn-secondary me-2", title="Reset sliders to default weights"),

                html.Button("Save preferences", id="explore-save-prefs", className="nyc-btn-secondary", title="Save explore preferences locally"),

            ],

            className="mt-2",

        ),

        html.Hr(style={"borderColor": "var(--border-color)"}),

        html.Button("Show profile snippet", id="explore-apply-snippet", className="nyc-btn-primary", title="Generate YAML snippet for profile weights"),

        html.Pre(id="explore-snippet", className="nyc-explore-snippet mt-2"),

    ],

)



_preview = dcc.Loading(

    type="default",

    color="var(--accent)",

    children=html.Div(

        [

            html.H2("Live preview", style={"fontSize": "1.1rem"}),

            html.Div(id="explore-preview-meta", className="nyc-page-sub"),

            dag.AgGrid(

                id="explore-preview-grid",

                rowData=[],

                columnDefs=[],

                defaultColDef={"filter": True, "sortable": True},

                style={"height": "360px"},

                className="ag-theme-alpine-dark mb-3",

            ),

            html.H2("By borough", style={"fontSize": "1.1rem"}),

            dcc.Graph(id="explore-borough-chart", config={"displayModeBar": False}),

        ],

        id="explore-preview-panel",

    ),

)



layout = dbc.Container(

    [

        *page_shell(

            "Explore",

            "Adjust parameters and see live previews. Analyst Pack runs stay canonical until you copy weights into your profile.",

            page_key="explore",

            pack_dir=_pack,

            children=[

                construction_scoring_explainer(),

                tip_card(

                    "Conflict buffer (preview only)",

                    "Spatial buffer distance in meters is shown for planning context. Pack conflict detection uses profile settings and permit joins.",

                    id="explore-buffer-tip",

                ),

                dcc.Store(id="explore-records", data=_records),

                dcc.Store(id="explore-pack-path", data=str(_pack) if _pack else ""),

                *debounce_bundle("explore"),

                html.Div(

                    className="nyc-explore-layout",

                    children=[

                        _controls,

                        html.Div(children=[_preview] if _records else [empty_state("No construction list — run Analyst Pack or load demo data.", demo_id="explore-load-demo", run_pack_id="explore-run-pack")]),

                    ],

                ),

                feedback_toast("explore-feedback"),

            ],

        ),

    ],

    fluid=True,

)





def _collect_params(ws, wv, wa, wada, wsp, wc, top_n, borough, conflicts_only, ada_only):

    return {

        "ws": ws, "wv": wv, "wa": wa, "wada": wada, "wsp": wsp, "wc": wc,

        "top_n": top_n, "borough": borough,

        "conflicts_only": bool(conflicts_only), "ada_only": bool(ada_only),

    }





@callback(

    Output("explore-w-severity-value", "children"),

    Output("explore-w-volume-value", "children"),

    Output("explore-w-age-value", "children"),

    Output("explore-w-ada-value", "children"),

    Output("explore-w-spine-value", "children"),

    Output("explore-w-complaints-value", "children"),

    Output("explore-top-n-value", "children"),

    Output("explore-buffer-m-value", "children"),

    Input("explore-w-severity", "value"),

    Input("explore-w-volume", "value"),

    Input("explore-w-age", "value"),

    Input("explore-w-ada", "value"),

    Input("explore-w-spine", "value"),

    Input("explore-w-complaints", "value"),

    Input("explore-top-n", "value"),

    Input("explore-buffer-m", "value"),

)

def update_slider_labels(s, v, a, ada, sp, c, n, buf):

    fmt = lambda x: f"{float(x):.2f}" if x is not None else "—"

    return [fmt(x) for x in (s, v, a, ada, sp, c, n, buf)]





@callback(

    Output("explore-pending", "data"),

    Output("explore-debounce-tick", "disabled"),

    Input("explore-w-severity", "value"),

    Input("explore-w-volume", "value"),

    Input("explore-w-age", "value"),

    Input("explore-w-ada", "value"),

    Input("explore-w-spine", "value"),

    Input("explore-w-complaints", "value"),

    Input("explore-top-n", "value"),

    Input("explore-borough", "value"),

    Input("explore-conflicts-only", "value"),

    Input("explore-ada-only", "value"),

)

def queue_explore_debounce(ws, wv, wa, wada, wsp, wc, top_n, borough, conflicts_only, ada_only):

    return _collect_params(ws, wv, wa, wada, wsp, wc, top_n, borough, conflicts_only, ada_only), False





@callback(

    Output("explore-debounced", "data"),

    Output("explore-debounce-tick", "disabled", allow_duplicate=True),

    Input("explore-debounce-tick", "n_intervals"),

    State("explore-pending", "data"),

    prevent_initial_call=True,

)

def flush_explore_debounce(_, pending):

    if pending is None:

        raise dash.exceptions.PreventUpdate

    return pending, True





@callback(

    Output("explore-preview-grid", "rowData"),

    Output("explore-preview-grid", "columnDefs"),

    Output("explore-borough-chart", "figure"),

    Output("explore-preview-meta", "children"),

    Input("explore-records", "data"),

    Input("explore-debounced", "data"),

)

def update_preview(records, params):

    empty_fig = go.Figure()

    empty_fig.update_layout(template="plotly_dark", height=240)

    if not records:

        return [], [], empty_fig, "No construction list — run Analyst Pack or load demo data."

    params = params or {}

    df = pd.DataFrame(records)

    weights = normalize_weights(

        params.get("ws") or 0,

        params.get("wv") or 0,

        params.get("wa") or 0,

        params.get("wada") or 0,

        params.get("wsp") or 0,

        params.get("wc") or 0,

    )

    preview = preview_priority(

        df,

        weights=weights,

        top_n=int(params.get("top_n") or 25),

        borough=params.get("borough"),

        conflicts_only=params.get("conflicts_only", False),

        ada_only=params.get("ada_only", False),

    )

    counts = borough_bar_counts(preview)

    if counts:

        fig = px.bar(

            x=list(counts.keys()),

            y=list(counts.values()),

            labels={"x": "Borough", "y": "Mean priority score"},

            title="Preview mean score by borough",

            template="plotly_dark",

        )

        fig.update_layout(height=240, margin=dict(l=40, r=20, t=40, b=40))

    else:

        fig = empty_fig

    cols = [{"field": c} for c in preview.columns] if not preview.empty else []

    meta = f"Showing {len(preview)} of {len(df)} locations (preview only, weights sum to 1.0)."

    return preview.to_dict("records"), cols, fig, meta





@callback(

    Output("explore-records", "data", allow_duplicate=True),

    Output("explore-pack-path", "data", allow_duplicate=True),

    Input("explore-load-demo", "n_clicks"),

    prevent_initial_call=True,

)

def load_demo(_):

    pack = copy_fixtures_to_demo() or ensure_demo_pack()

    recs = construction_records(pack) if pack else demo_construction_records()

    return recs, str(pack) if pack else ""





@callback(

    Output("url", "pathname", allow_duplicate=True),

    Input("explore-run-pack", "n_clicks"),

    prevent_initial_call=True,

)

def goto_home_run(_):

    return "/"





@callback(

    Output("explore-w-severity", "value"),

    Output("explore-w-volume", "value"),

    Output("explore-w-age", "value"),

    Output("explore-w-ada", "value"),

    Output("explore-w-spine", "value"),

    Output("explore-w-complaints", "value"),

    Output("explore-top-n", "value"),

    Output("explore-borough", "value"),

    Output("explore-conflicts-only", "value"),

    Output("explore-ada-only", "value"),

    Output("explore-buffer-m", "value"),

    Input("explore-reset", "n_clicks"),

    prevent_initial_call=True,

)

def reset_defaults(_):

    return (

        DEFAULT_PRIORITY_WEIGHTS["severity"],

        DEFAULT_PRIORITY_WEIGHTS["pedestrian_volume"],

        DEFAULT_PRIORITY_WEIGHTS["age_days"],

        DEFAULT_PRIORITY_WEIGHTS["ada_flag"],

        DEFAULT_PRIORITY_WEIGHTS["smart_spine"],

        DEFAULT_PRIORITY_WEIGHTS["complaint_count"],

        25,

        "ALL",

        False,

        False,

        0,

    )





@callback(

    Output("explore-snippet", "children"),

    Output("explore-feedback", "children"),

    Input("explore-apply-snippet", "n_clicks"),

    State("explore-w-severity", "value"),

    State("explore-w-volume", "value"),

    State("explore-w-age", "value"),

    State("explore-w-ada", "value"),

    State("explore-w-spine", "value"),

    State("explore-w-complaints", "value"),

    prevent_initial_call=True,

)

def show_snippet(_, ws, wv, wa, wada, wsp, wc):

    weights = normalize_weights(ws or 0, wv or 0, wa or 0, wada or 0, wsp or 0, wc or 0)

    text = profile_weight_snippet(weights)

    toast = dbc.Alert(

        [html.I(className="bi bi-check-circle-fill nyc-success-check", **{"aria-hidden": "true"}), " Snippet ready — copy into your profile; pack not modified."],

        color="success",

        dismissable=True,

    )

    return text, toast





@callback(

    Output("explore-feedback", "children", allow_duplicate=True),

    Input("explore-save-prefs", "n_clicks"),

    State("explore-w-severity", "value"),

    State("explore-w-volume", "value"),

    State("explore-w-age", "value"),

    State("explore-w-ada", "value"),

    State("explore-w-spine", "value"),

    State("explore-w-complaints", "value"),

    State("explore-top-n", "value"),

    State("explore-borough", "value"),

    State("explore-conflicts-only", "value"),

    State("explore-ada-only", "value"),

    State("explore-buffer-m", "value"),

    prevent_initial_call=True,

)

def save_prefs(_, ws, wv, wa, wada, wsp, wc, top_n, borough, conflicts_only, ada_only, buffer_m):

    save_explore_prefs(

        {

            "w_severity": ws,

            "w_volume": wv,

            "w_age": wa,

            "w_ada": wada,

            "w_spine": wsp,

            "w_complaints": wc,

            "top_n": top_n,

            "borough": borough,

            "conflicts_only": bool(conflicts_only),

            "ada_only": bool(ada_only),

            "buffer_m": buffer_m,

        }

    )

    return dbc.Alert("Preferences saved.", color="success", dismissable=True)


