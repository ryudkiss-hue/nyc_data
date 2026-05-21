"""Review page — resolve conflicts and approvals with persistence."""

from __future__ import annotations

import sys
from concurrent.futures import Future
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from dash_app.background_jobs import run_subprocess
from dash_app.components.interactive import feedback_toast
from dash_app.components.shell import page_shell
from dash_app.data.analyst_pack import latest_pack_dir, load_construction_list, load_manifest
from dash_app.data.state import load_state

dash.register_page(__name__, path="/review", name="Review", order=6)

ROOT = Path(__file__).resolve().parents[2]
_list_future: Future | None = None
_save_future: Future | None = None


def _default_pack() -> Path | None:
    st = load_state()
    p = st.get("last_pack_dir")
    if p and Path(p).exists():
        return Path(p)
    return latest_pack_dir()


def _review_cmd(args: list[str]) -> list[str]:
    return [sys.executable, "-m", "socrata_toolkit.core.cli", "review", *args]


pack = _default_pack()
manifest = load_manifest(pack) if pack else {}

layout = dbc.Container(
    [
        *page_shell(
            "Review",
            "Track decisions for conflicts and construction approvals; persisted via socrata review CLI.",
            page_key="review",
            pack_dir=pack,
            children=[
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Pack folder", style={"fontSize": "0.8rem", "fontWeight": 600}),
                                            dbc.Input(
                                                id="rev-pack-dir",
                                                value=str(pack) if pack else "",
                                                placeholder="outputs/analyst_pack/YYYY-MM-DD",
                                                className="mb-2",
                                            ),
                                        ],
                                        md=8,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Kind", style={"fontSize": "0.8rem", "fontWeight": 600}),
                                            dcc.Dropdown(
                                                id="rev-kind",
                                                options=[
                                                    {"label": "Conflicts", "value": "conflict"},
                                                    {"label": "Approvals", "value": "approval"},
                                                ],
                                                value="conflict",
                                                clearable=False,
                                                className="mb-2",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Input(id="rev-q", placeholder="Search key / notes / assignee", className="mb-2"),
                                        md=8,
                                    ),
                                    dbc.Col(
                                        dbc.Input(id="rev-status-filter", placeholder="Status filter (optional)", className="mb-2"),
                                        md=4,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    dbc.Button("Refresh", id="rev-refresh", color="secondary", size="sm", className="me-2"),
                                ],
                                className="mb-2",
                            ),
                            html.Div(id="rev-summary", style={"fontSize": "0.8rem", "color": "var(--text-muted)"}),
                            html.Hr(style={"borderColor": "var(--border-color)"}),
                            html.H2("Set decision", style={"fontSize": "1.0rem"}),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Input(id="rev-key-type", placeholder="key_type", value="location_id"),
                                        md=3,
                                    ),
                                    dbc.Col(dbc.Input(id="rev-key", placeholder="key value", value=""), md=3),
                                    dbc.Col(
                                        dcc.Dropdown(
                                            id="rev-status",
                                            options=[
                                                {"label": "Resolved", "value": "resolved"},
                                                {"label": "Deferred", "value": "deferred"},
                                                {"label": "Needs coordination", "value": "needs_coordination"},
                                                {"label": "Approved", "value": "approved"},
                                                {"label": "Hold", "value": "hold"},
                                            ],
                                            value="resolved",
                                            clearable=False,
                                        ),
                                        md=2,
                                    ),
                                    dbc.Col(dbc.Input(id="rev-assigned", placeholder="assigned_to", value=""), md=2),
                                    dbc.Col(dbc.Input(id="rev-reason", placeholder="reason (approvals)", value=""), md=2),
                                ],
                                className="mb-2",
                            ),
                            dbc.Textarea(id="rev-notes", placeholder="notes", value="", className="mb-2", style={"minHeight": "80px"}),
                            dbc.Button("Save decision", id="rev-save", color="primary", size="sm"),
                            html.Div(id="rev-save-msg", className="mt-2"),
                            dcc.Interval(id="rev-save-poll", interval=800, disabled=True, n_intervals=0),
                            dcc.Interval(id="rev-list-poll", interval=800, disabled=True, n_intervals=0),
                        ]
                    ),
                    style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"},
                ),
                html.H2("Recent decisions", style={"fontSize": "1.1rem", "marginTop": "16px"}),
                dcc.Loading(
                    type="default",
                    color="var(--accent)",
                    children=dbc.Card(
                        dbc.CardBody([html.Div(id="rev-table")]),
                        style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"},
                    ),
                ),
                dcc.Store(id="rev-pack-date", data=manifest.get("run_date", "")),
                feedback_toast("rev-feedback"),
            ],
        ),
    ],
    fluid=True,
)


@callback(
    Output("rev-table", "children"),
    Output("rev-summary", "children"),
    Output("rev-pack-date", "data"),
    Output("rev-list-poll", "disabled"),
    Input("rev-refresh", "n_clicks"),
    Input("rev-list-poll", "n_intervals"),
    State("rev-pack-dir", "value"),
    State("rev-kind", "value"),
    State("rev-q", "value"),
    State("rev-status-filter", "value"),
)
def refresh_table(_, __poll, pack_dir: str, kind: str, q: str, status: str):
    global _list_future
    if _list_future is not None and not _list_future.done():
        return (
            dbc.Alert("Loading decisions…", color="info"),
            "Loading…",
            no_update,
            False,
        )
    if _list_future is not None and _list_future.done():
        try:
            proc = _list_future.result()
        except Exception as exc:
            _list_future = None
            return html.Div(str(exc), className="nyc-error-banner", role="alert"), "Failed.", "", True
        _list_future = None
        if proc.returncode != 0:
            return html.Pre(proc.stderr or proc.stdout), "Failed to load decisions.", no_update, True
        return html.Pre(proc.stdout or "(no decisions)"), "Loaded.", no_update, True

    p = Path(pack_dir) if pack_dir else None
    if not p or not p.exists():
        return html.Div("Pack not found.", className="nyc-error-banner", role="alert"), "—", "", True
    pack_date = p.name
    args = ["list", "--pack-date", pack_date, "--kind", kind, "--limit", "2000"]
    if q:
        args += ["--q", q]
    if status:
        args += ["--status", status]
    _list_future = run_subprocess(_review_cmd(args), cwd=str(ROOT), timeout=60)
    note = ""
    if kind == "approval":
        total = len(load_construction_list(p))
        note = f" (construction rows: {total})"
    return dbc.Alert("Loading decisions in background…", color="info"), f"Pack date: {pack_date}{note}", pack_date, False


@callback(
    Output("rev-save-msg", "children"),
    Output("rev-feedback", "children"),
    Output("rev-save-poll", "disabled"),
    Input("rev-save", "n_clicks"),
    State("rev-pack-date", "data"),
    State("rev-kind", "value"),
    State("rev-key-type", "value"),
    State("rev-key", "value"),
    State("rev-status", "value"),
    State("rev-assigned", "value"),
    State("rev-reason", "value"),
    State("rev-notes", "value"),
    prevent_initial_call=True,
)
def save_decision(_, pack_date: str, kind: str, key_type: str, key_value: str, status: str, assigned_to: str, reason: str, notes: str):
    global _save_future
    if _save_future is not None and not _save_future.done():
        return (
            dbc.Alert("Save already in progress…", color="warning"),
            dbc.Alert("Save already in progress…", color="warning"),
            False,
        )
    if not pack_date:
        err = html.Div("Pack date not set. Refresh first.", className="nyc-error-banner", role="alert")
        return err, err, True
    if not key_value:
        err = html.Div("Key value required.", className="nyc-error-banner", role="alert")
        return err, err, True
    args = [
        "set",
        "--pack-date",
        pack_date,
        "--kind",
        kind,
        "--key-type",
        key_type or "location_id",
        "--key",
        key_value,
        "--status",
        status,
        "--assigned-to",
        assigned_to or "",
        "--notes",
        notes or "",
    ]
    if reason:
        args += ["--reason", reason]
    _save_future = run_subprocess(_review_cmd(args), cwd=str(ROOT), timeout=60)
    saving = dbc.Alert(
        [html.I(className="bi bi-hourglass-split me-2", **{"aria-hidden": "true"}), f"Saving as {status}…"],
        color="info",
    )
    return saving, saving, False


@callback(
    Output("rev-save-msg", "children", allow_duplicate=True),
    Output("rev-feedback", "children", allow_duplicate=True),
    Output("rev-save-poll", "disabled", allow_duplicate=True),
    Input("rev-save-poll", "n_intervals"),
    prevent_initial_call=True,
)
def poll_save(_):
    global _save_future
    if _save_future is None:
        raise PreventUpdate
    if not _save_future.done():
        raise PreventUpdate
    try:
        proc = _save_future.result()
    except Exception as exc:
        _save_future = None
        err = html.Div(str(exc), className="nyc-error-banner", role="alert")
        return err, err, True
    _save_future = None
    if proc.returncode != 0:
        err = html.Div([html.Strong("Save failed"), html.Pre(proc.stderr or proc.stdout)], className="nyc-error-banner", role="alert")
        return err, err, True
    toast = dbc.Alert(
        [html.I(className="bi bi-check-circle-fill", **{"aria-hidden": "true"}), " Saved."],
        color="success",
        dismissable=True,
    )
    return dbc.Alert("Saved.", color="success", dismissable=True), toast, True
