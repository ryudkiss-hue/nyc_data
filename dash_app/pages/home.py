"""Analyst home — run pack, workflow, latest outputs."""

from __future__ import annotations

import os
import sys
from concurrent.futures import Future
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update
from dash.exceptions import PreventUpdate

from dash_app.background_jobs import run_subprocess
from dash_app.components.interactive import step_hint, tip_card
from dash_app.components.shell import empty_state, page_shell
from dash_app.data.analyst_pack import artifact_links, latest_pack_dir, load_manifest
from dash_app.data.state import load_state
from dash_app.data.ui_prefs import get_ui_pref

_pack_future: Future | None = None

dash.register_page(__name__, path="/", name="Home", order=0)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "config" / "analyst_profile.yaml"
EXAMPLE_PROFILE = ROOT / "config" / "analyst_profile.example.yaml"

_WORKFLOW = [
    (
        "Setup",
        "Run the install wizard, then edit config/analyst_profile.yaml for your data paths.",
        "python -m socrata_toolkit.install_wizard",
    ),
    (
        "Run",
        "Generate this week's Analyst Pack (Excel, reports, KPIs).",
        "socrata analyst run --profile config/analyst_profile.yaml",
    ),
    (
        "Review",
        "Open Review in the dashboard, then Publish when ready.",
        "Dash: /review and /publish",
    ),
]


def _status_text(manifest: dict, pack) -> str:
    if not pack:
        return "No Analyst Pack yet. Complete setup, then run your first pack."
    run_date = manifest.get("run_date", "unknown")
    n = len(manifest.get("artifacts", {}))
    warnings = manifest.get("warnings", [])
    partial = manifest.get("partial_failures", [])
    health = "with warnings" if warnings or partial else "OK"
    return f"Last run: {run_date} — {n} artifacts ({health})"


def _resume_hint() -> html.Div:
    st = load_state()
    last_pack = st.get("last_pack_dir") or ""
    last_pub = st.get("last_publish_profile") or ""
    if not last_pack:
        return html.Div()
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Resume: ", style={"fontWeight": 700}),
                    html.Code(last_pack),
                ],
                style={"fontSize": "0.82rem"},
            ),
            (
                html.Div(
                    [html.Span("Last publish profile: ", style={"fontWeight": 700}), html.Code(last_pub)],
                    style={"fontSize": "0.78rem", "color": "var(--text-muted)"},
                )
                if last_pub
                else html.Div()
            ),
            html.Div(
                [
                    dcc.Link("Go to Publish", href="/publish", className="nyc-nav-link", style={"display": "inline-flex"}),
                    dcc.Link("Explore parameters", href="/explore", className="nyc-nav-link", style={"display": "inline-flex", "marginLeft": "12px"}),
                ],
                style={"marginTop": "6px"},
            ),
        ],
        className="nyc-card",
    )


def _workflow_stepper(has_pack: bool) -> html.Div:
    steps = []
    current_idx = 2 if has_pack else (1 if DEFAULT_PROFILE.exists() or EXAMPLE_PROFILE.exists() else 0)
    for i, (title, why, cmd) in enumerate(_WORKFLOW):
        props = {"aria-current": "step"} if i == current_idx else {}
        steps.append(
            html.Div(
                className="nyc-workflow-step",
                children=[
                    html.Div(title, style={"fontWeight": 700}),
                    html.Div(
                        className="nyc-workflow-step-learn",
                        children=[tip_card(f"Why {title}?", why, id=f"home-why-{title.lower().replace(' ', '-')}")],
                    ),
                    step_hint(cmd, id=f"home-hint-{i}"),
                ],
                **props,
            )
        )
    return html.Div(className="nyc-workflow-steps", children=steps, role="list")


def _warnings_block() -> html.Div:
    manifest = load_manifest(latest_pack_dir())
    items = []
    for w in manifest.get("warnings", []):
        items.append(html.Li(w))
    for pf in manifest.get("partial_failures", []):
        items.append(html.Li(f"FAILED {pf.get('source')}: {pf.get('error')}", style={"color": "var(--danger)"}))
    if not items:
        return html.Div()
    return html.Div(
        [html.H3("Manifest warnings", style={"fontSize": "1rem"}), html.Ul(items)],
        role="status",
    )


def _pack_feedback(proc) -> html.Div | dbc.Alert:
    if proc.returncode != 0:
        return html.Div(
            [html.Strong("Run failed"), html.Pre(proc.stderr or proc.stdout)],
            className="nyc-error-banner",
            role="alert",
        )
    return dbc.Alert(
        f"Pack complete. {proc.stdout[-500:] if proc.stdout else 'See outputs/analyst_pack/'}",
        color="success",
    )


_pack = latest_pack_dir()
_manifest = load_manifest(_pack)

layout = dbc.Container(
    [
        *page_shell(
            "Analyst Home",
            "Run the weekly Analyst Pack, follow the workflow, and open latest artifacts.",
            page_key="home",
            pack_dir=_pack,
            children=[
                html.P(id="home-status-text", className="nyc-page-sub"),
                html.Div(id="home-resume-wrap", children=_resume_hint()),
                html.Div(id="home-workflow-wrap"),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H2("Run Analyst Pack", style={"fontSize": "1.25rem"}),
                            html.P(
                                "Runs `socrata analyst run` using your profile YAML. "
                                "Prefer CLI in production; this button is for local convenience.",
                                className="text-muted",
                            ),
                            dbc.Label("Analyst profile path", html_for="home-profile-path", className="mb-1"),
                            dbc.Input(
                                id="home-profile-path",
                                value=str(
                                    DEFAULT_PROFILE if DEFAULT_PROFILE.exists() else EXAMPLE_PROFILE
                                ),
                                className="mb-2",
                            ),
                            dbc.Checklist(
                                id="home-offline",
                                options=[{"label": "Offline mode (skip Socrata sources)", "value": "offline"}],
                                value=["offline"] if get_ui_pref("offline_mode") else [],
                                className="mb-2",
                                switch=True,
                            ),
                            html.Button(
                                "Run Analyst Pack",
                                id="home-run-pack",
                                className="nyc-btn-primary",
                                **{"aria-label": "Run analyst pack"},
                            ),
                            html.Div(id="home-run-feedback", className="mt-3"),
                            dcc.Interval(id="home-run-poll", interval=1000, disabled=True, n_intervals=0),
                        ]
                    ),
                    className="mb-4 nyc-card",
                ),
                html.H2("Latest outputs", style={"fontSize": "1.1rem"}),
                html.Div(id="home-artifacts-wrap"),
                html.Div(id="home-warnings"),
            ],
        ),
    ],
    fluid=True,
)


@callback(
    Output("home-status-text", "children"),
    Output("home-workflow-wrap", "children"),
    Output("home-artifacts-wrap", "children"),
    Output("home-warnings", "children"),
    Output("nyc-context-pack", "children"),
    Input("url", "pathname"),
)
def refresh_home_on_nav(pathname):
    if pathname not in ("/", ""):
        raise PreventUpdate
    pack = latest_pack_dir()
    manifest = load_manifest(pack)
    artifacts = artifact_links(manifest)
    if artifacts:
        artifact_ui = html.Ul(
            [
                html.Li(
                    html.A(
                        item["label"],
                        href=f"file:///{item['path'].replace(chr(92), '/')}",
                        target="_blank",
                    )
                )
                for item in artifacts
            ],
            id="home-artifact-list",
        )
    else:
        artifact_ui = empty_state(
            "No artifacts yet — run your first Analyst Pack or load demo data.",
            show_run_pack=True,
            show_demo=True,
            run_pack_id="home-empty-run-pack",
            demo_id="home-load-demo",
        )
    run_date = manifest.get("run_date", "") if pack else ""
    pack_part = f"Pack {run_date}" if run_date else "No pack loaded"
    return (
        _status_text(manifest, pack),
        _workflow_stepper(bool(pack)),
        artifact_ui,
        _warnings_block(),
        pack_part,
    )


@callback(
    Output("home-run-feedback", "children"),
    Output("home-run-poll", "disabled"),
    Input("home-run-pack", "n_clicks"),
    Input("home-empty-run-pack", "n_clicks"),
    State("home-profile-path", "value"),
    State("home-offline", "value"),
    prevent_initial_call=True,
)
def start_pack(_n1, _n2, profile_path, offline_vals):
    global _pack_future
    if _pack_future is not None and not _pack_future.done():
        return (
            dbc.Alert("Analyst pack is already running. Please wait.", color="warning"),
            False,
        )
    if not profile_path or not Path(profile_path).exists():
        return (
            html.Div(
                f"Profile not found: {profile_path}. Run: socrata analyst init-config",
                className="nyc-error-banner",
                role="alert",
            ),
            True,
        )
    cmd = [sys.executable, "-m", "socrata_toolkit.core.cli", "analyst", "run", "--profile", profile_path]
    if offline_vals and "offline" in offline_vals:
        cmd.append("--offline")
    _pack_future = run_subprocess(cmd, cwd=str(ROOT), timeout=300)
    mode = " (offline)" if offline_vals and "offline" in offline_vals else ""
    return (
        dbc.Alert(
            f"Analyst pack started in the background{mode}. This page stays responsive while it runs.",
            color="info",
        ),
        False,
    )


@callback(
    Output("home-run-feedback", "children", allow_duplicate=True),
    Output("home-run-poll", "disabled", allow_duplicate=True),
    Output("home-status-text", "children", allow_duplicate=True),
    Output("home-artifacts-wrap", "children", allow_duplicate=True),
    Output("home-warnings", "children", allow_duplicate=True),
    Input("home-run-poll", "n_intervals"),
    prevent_initial_call=True,
)
def poll_pack(_):
    global _pack_future
    if _pack_future is None:
        raise PreventUpdate
    if not _pack_future.done():
        raise PreventUpdate
    try:
        proc = _pack_future.result()
    except Exception as exc:
        _pack_future = None
        err = html.Div(str(exc), className="nyc-error-banner", role="alert")
        return err, True, no_update, no_update, html.Div()
    _pack_future = None
    pack = latest_pack_dir()
    manifest = load_manifest(pack)
    artifacts = artifact_links(manifest)
    artifact_ui = (
        html.Ul(
            [
                html.Li(
                    html.A(
                        item["label"],
                        href=f"file:///{item['path'].replace(chr(92), '/')}",
                        target="_blank",
                    )
                )
                for item in artifacts
            ]
        )
        if artifacts
        else empty_state("No artifacts yet.", show_demo=True, demo_id="home-load-demo")
    )
    return (
        _pack_feedback(proc),
        True,
        _status_text(manifest, pack),
        artifact_ui,
        _warnings_block(),
    )


@callback(
    Output("home-artifacts-wrap", "children", allow_duplicate=True),
    Output("home-status-text", "children", allow_duplicate=True),
    Output("home-workflow-wrap", "children", allow_duplicate=True),
    Output("nyc-context-pack", "children", allow_duplicate=True),
    Input("home-load-demo", "n_clicks"),
    prevent_initial_call=True,
)
def load_demo_pack(_n):
    from dash_app.data.demo_pack import ensure_demo_pack
    from dash_app.data.pack_loader import invalidate_pack_cache

    demo = ensure_demo_pack()
    invalidate_pack_cache()
    if not demo:
        return (
            html.Div("Demo fixtures not found under tests/fixtures/analyst.", className="nyc-error-banner"),
            no_update,
            no_update,
            no_update,
        )
    pack = latest_pack_dir()
    manifest = load_manifest(pack)
    artifacts = artifact_links(manifest)
    artifact_ui = html.Ul(
        [
            html.Li(
                html.A(
                    item["label"],
                    href=f"file:///{item['path'].replace(chr(92), '/')}",
                    target="_blank",
                )
            )
            for item in artifacts
        ]
    ) if artifacts else html.P("Demo pack ready.")
    return (
        artifact_ui,
        _status_text(manifest, pack) + " (demo)",
        _workflow_stepper(True),
        f"Pack {manifest.get('run_date', 'demo')}",
    )
