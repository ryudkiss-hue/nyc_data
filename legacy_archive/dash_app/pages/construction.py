"""Construction list, week-over-week diff, and conflicts — with live exploration."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dash_app.components.debounce import debounce_bundle
from dash_app.components.explainers import construction_scoring_explainer
from dash_app.components.interactive import feedback_toast, param_checkbox, param_slider, tip_card
from dash_app.components.shell import empty_state, page_shell
from dash_app.data.analyst_pack import load_construction_diff, load_pack_file
from dash_app.data.demo_pack import copy_fixtures_to_demo, demo_construction_records, ensure_demo_pack
from dash_app.data.pack_loader import construction_records, resolve_pack_dir
from socrata_toolkit.analyst.explore import borough_bar_counts, normalize_weights, preview_priority
from socrata_toolkit.engineering.construction_list import DEFAULT_PRIORITY_WEIGHTS

dash.register_page(__name__, path="/construction", name="Construction", order=2)

_PAGE_SIZE = 100

_pack = resolve_pack_dir() or ensure_demo_pack()
_records = construction_records(_pack) if _pack else demo_construction_records()
_diff_md = ""
if _pack:
    from dash_app.data.analyst_pack import load_manifest

    _manifest = load_manifest(_pack)
    _diff_md = load_construction_diff(_pack)
else:
    _manifest = {}

_controls = html.Div(
    className="nyc-explore-panel",
    children=[
        param_slider(
            "Severity weight",
            0,
            1,
            0.05,
            DEFAULT_PRIORITY_WEIGHTS["severity"],
            "con-w-severity",
            aria_label="Severity weight",
        ),
        param_slider(
            "ADA weight",
            0,
            1,
            0.05,
            DEFAULT_PRIORITY_WEIGHTS["ada_flag"],
            "con-w-ada",
            aria_label="ADA weight",
        ),
        param_slider(
            "Complaints weight",
            0,
            1,
            0.05,
            DEFAULT_PRIORITY_WEIGHTS["complaint_count"],
            "con-w-complaints",
            aria_label="Complaints weight",
        ),
        param_slider("Top N preview", 10, 100, 10, 25, "con-top-n", aria_label="Top N rows"),
        param_checkbox("Show only conflicts", "con-conflicts-only"),
        param_checkbox("ADA locations only", "con-ada-only"),
    ],
)

_preview = dcc.Loading(
    type="default",
    color="var(--accent)",
    children=html.Div(
        [
            html.Div(id="con-preview-meta", className="nyc-loading-inline mb-2"),
            dag.AgGrid(
                id="construction-grid",
                rowData=[],
                columnDefs=[],
                defaultColDef={"filter": True, "sortable": True, "resizable": True},
                style={"height": "360px"},
                className="ag-theme-alpine-dark",
            ),
            html.Button(
                "Show more",
                id="con-show-more",
                className="nyc-btn-secondary mt-2",
                style={"display": "none"},
            ),
            html.H2("By borough", style={"fontSize": "1rem", "marginTop": "1rem"}),
            dcc.Graph(id="con-borough-chart", config={"displayModeBar": False}),
        ],
        id="con-preview-panel",
    ),
)

layout = dbc.Container(
    [
        *page_shell(
            "Construction",
            "Live priority preview, week-over-week diff, and conflict summary from the latest Analyst Pack.",
            page_key="construction",
            pack_dir=_pack,
            children=[
                construction_scoring_explainer(),
                tip_card(
                    "Live preview vs pack run",
                    "Sliders re-rank the staged construction list from the latest pack for exploration. "
                    "Re-run the Analyst Pack to persist new weights in production outputs.",
                    id="construction-preview-tip",
                ),
                dcc.Store(id="construction-records", data=_records),
                dcc.Store(id="con-visible-rows", data=_PAGE_SIZE),
                *debounce_bundle("construction"),
                html.Div(
                    className="nyc-explore-layout",
                    children=[
                        _controls,
                        html.Div(
                            children=[_preview]
                            if _records
                            else [
                                empty_state(
                                    "No construction list — run Analyst Pack or load demo data.",
                                    demo_id="con-load-demo",
                                    run_pack_id="con-run-pack",
                                )
                            ]
                        ),
                    ],
                ),
                html.H2("Week-over-week diff", style={"fontSize": "1.1rem", "marginTop": "1.5rem"}),
                html.Pre(
                    _diff_md
                    or "No diff yet — run a second pack after the first to compare construction lists.",
                    id="con-diff-md",
                    style={"whiteSpace": "pre-wrap", "maxHeight": "240px", "overflow": "auto"},
                ),
                html.H2("Conflicts summary", style={"fontSize": "1.1rem", "marginTop": "1.5rem"}),
                html.Pre(
                    load_pack_file("conflicts_summary.md", _pack)
                    or "Run analyst pack with permits source.",
                    id="con-conflicts-md",
                    style={"whiteSpace": "pre-wrap"},
                ),
                feedback_toast("con-feedback"),
            ],
        ),
    ],
    fluid=True,
)


def _collect_con_params(ws, wada, wc, top_n, conflicts_only, ada_only):
    return {
        "ws": ws,
        "wada": wada,
        "wc": wc,
        "top_n": top_n,
        "conflicts_only": bool(conflicts_only),
        "ada_only": bool(ada_only),
    }


@callback(
    Output("con-w-severity-value", "children"),
    Output("con-w-ada-value", "children"),
    Output("con-w-complaints-value", "children"),
    Output("con-top-n-value", "children"),
    Input("con-w-severity", "value"),
    Input("con-w-ada", "value"),
    Input("con-w-complaints", "value"),
    Input("con-top-n", "value"),
)
def con_slider_labels(s, a, c, n):
    fmt = lambda x: f"{float(x):.2f}" if x is not None else "—"
    return fmt(s), fmt(a), fmt(c), str(int(n)) if n else "—"


@callback(
    Output("construction-pending", "data"),
    Output("construction-debounce-tick", "disabled"),
    Input("con-w-severity", "value"),
    Input("con-w-ada", "value"),
    Input("con-w-complaints", "value"),
    Input("con-top-n", "value"),
    Input("con-conflicts-only", "value"),
    Input("con-ada-only", "value"),
)
def queue_construction_debounce(ws, wada, wc, top_n, conflicts_only, ada_only):
    return _collect_con_params(ws, wada, wc, top_n, conflicts_only, ada_only), False


@callback(
    Output("construction-debounced", "data"),
    Output("construction-debounce-tick", "disabled", allow_duplicate=True),
    Input("construction-debounce-tick", "n_intervals"),
    State("construction-pending", "data"),
    prevent_initial_call=True,
)
def flush_construction_debounce(_, pending):
    if pending is None:
        raise dash.exceptions.PreventUpdate
    return pending, True


@callback(
    Output("construction-grid", "rowData"),
    Output("construction-grid", "columnDefs"),
    Output("con-borough-chart", "figure"),
    Output("con-preview-meta", "children"),
    Output("con-show-more", "style"),
    Input("construction-records", "data"),
    Input("construction-debounced", "data"),
    Input("con-visible-rows", "data"),
)
def update_construction_preview(records, params, visible_rows):
    empty = go.Figure()
    empty.update_layout(template="plotly_dark", height=220)
    hide_more = {"display": "none"}
    if not records:
        return [], [], empty, "No construction list — run Analyst Pack or load demo data.", hide_more
    params = params or {}
    df = pd.DataFrame(records)
    weights = normalize_weights(
        params.get("ws") or 0,
        DEFAULT_PRIORITY_WEIGHTS["pedestrian_volume"],
        DEFAULT_PRIORITY_WEIGHTS["age_days"],
        params.get("wada") or 0,
        DEFAULT_PRIORITY_WEIGHTS["smart_spine"],
        params.get("wc") or 0,
    )
    preview = preview_priority(
        df,
        weights=weights,
        top_n=int(params.get("top_n") or 25),
        conflicts_only=params.get("conflicts_only", False),
        ada_only=params.get("ada_only", False),
    )
    limit = int(visible_rows or _PAGE_SIZE)
    total = len(preview)
    shown = preview.head(limit)
    more_style = {"display": "inline-block"} if total > limit else hide_more
    counts = borough_bar_counts(shown)
    if counts:
        fig = px.bar(
            x=list(counts.keys()),
            y=list(counts.values()),
            labels={"x": "Borough", "y": "Mean score"},
            template="plotly_dark",
        )
        fig.update_layout(height=220, margin=dict(l=40, r=20, t=30, b=40))
    else:
        fig = empty
    cols = [{"field": c} for c in shown.columns] if not shown.empty else []
    meta = f"Showing {len(shown)} of {total} preview rows (page size {limit})."
    return shown.to_dict("records"), cols, fig, meta, more_style


@callback(
    Output("con-visible-rows", "data"),
    Input("con-show-more", "n_clicks"),
    State("con-visible-rows", "data"),
    prevent_initial_call=True,
)
def show_more_rows(n, current):
    return int(current or _PAGE_SIZE) + _PAGE_SIZE


@callback(
    Output("construction-records", "data", allow_duplicate=True),
    Input("con-load-demo", "n_clicks"),
    prevent_initial_call=True,
)
def load_con_demo(_):
    pack = copy_fixtures_to_demo() or ensure_demo_pack()
    return construction_records(pack) if pack else demo_construction_records()


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("con-run-pack", "n_clicks"),
    prevent_initial_call=True,
)
def goto_home_run(_):
    return "/"


@callback(
    Output("con-diff-md", "children"),
    Output("con-conflicts-md", "children"),
    Output("nyc-context-pack", "children"),
    Input("url", "pathname"),
)
def refresh_construction_context(pathname):
    if pathname != "/construction":
        raise dash.exceptions.PreventUpdate
    pack = resolve_pack_dir()
    run_date = ""
    diff = "No diff yet — run a second pack after the first to compare construction lists."
    conflicts = "Run analyst pack with permits source."
    if pack:
        from dash_app.data.analyst_pack import load_manifest

        manifest = load_manifest(pack)
        run_date = manifest.get("run_date", pack.name)
        diff = load_construction_diff(pack) or diff
        conflicts = load_pack_file("conflicts_summary.md", pack) or conflicts
    pack_part = f"Pack {run_date}" if run_date else "No pack loaded"
    return diff, conflicts, pack_part
