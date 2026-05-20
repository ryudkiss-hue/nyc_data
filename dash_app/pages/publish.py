"""Publish page — push Analyst Pack outputs to destinations."""

import os
import sys
from concurrent.futures import Future
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from dash_app.background_jobs import run_subprocess
from dash_app.components.interactive import tip_card
from dash_app.components.shell import page_shell
from dash_app.data.analyst_pack import latest_pack_dir, load_manifest
from dash_app.data.state import load_state

dash.register_page(__name__, path="/publish", name="Publish", order=8)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PUBLISH_PROFILE = ROOT / "config" / "publish_profile.yaml"
EXAMPLE_PUBLISH_PROFILE = ROOT / "config" / "publish_profile.example.yaml"
PROFILES_ROOT = ROOT / "config" / "profiles"
_publish_future: Future | None = None


def _profile_publish_presets() -> list[Path]:
    prof = (os.getenv("TOOLKIT_PROFILE", "") or "default").strip() or "default"
    preset_dir = PROFILES_ROOT / prof / "publish_presets"
    if not preset_dir.exists():
        return []
    return sorted([p for p in preset_dir.glob("*.yaml") if p.is_file()])


def _default_pack() -> Path | None:
    st = load_state()
    p = st.get("last_pack_dir")
    if p and Path(p).exists():
        return Path(p)
    return latest_pack_dir()


def _stepper(current: str) -> html.Div:
    steps = ["Setup", "Connect Sources", "Validate", "Run", "Review", "Publish"]
    out = []
    for s in steps:
        props = {"aria-current": "step"} if s == current else {}
        out.append(html.Div(s, className="nyc-workflow-step", **props))
    return html.Div(className="nyc-workflow-steps", children=out, role="list")


pack = _default_pack()
manifest = load_manifest(pack) if pack else {}

layout = dbc.Container(
    [
        *page_shell(
            "Publish",
            "Push an Analyst Pack to share folders, BI staging, Teams, email, and optional PPTX.",
            page_key="publish",
            pack_dir=pack,
            children=[
                _stepper("Publish"),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H2("Select pack and publish profile", style={"fontSize": "1.1rem"}),
                            dbc.Label("Pack folder", style={"fontSize": "0.8rem", "fontWeight": 600}),
                            dbc.Input(
                                id="pub-pack-dir",
                                value=str(pack) if pack else "",
                                placeholder="outputs/analyst_pack/YYYY-MM-DD",
                                className="mb-2",
                            ),
                            dbc.Label("Publish profile YAML", style={"fontSize": "0.8rem", "fontWeight": 600}),
                            dbc.Label("Preset (optional)", style={"fontSize": "0.75rem", "fontWeight": 600, "marginTop": "4px"}),
                            dcc.Dropdown(
                                id="pub-preset",
                                options=[
                                    {"label": f"{p.stem} (profile preset)", "value": str(p)}
                                    for p in _profile_publish_presets()
                                ],
                                value="",
                                placeholder="Select a preset from config/profiles/<name>/publish_presets/",
                                clearable=True,
                                className="mb-2",
                            ),
                            dbc.Input(
                                id="pub-profile-path",
                                value=str(
                                    DEFAULT_PUBLISH_PROFILE
                                    if DEFAULT_PUBLISH_PROFILE.exists()
                                    else EXAMPLE_PUBLISH_PROFILE
                                ),
                                className="mb-2",
                            ),
                            html.H3("Destinations", style={"fontSize": "0.95rem", "marginTop": "8px"}),
                            dbc.Checklist(
                                id="pub-destinations",
                                options=[
                                    {"label": "Share folder / network drive", "value": "share"},
                                    {"label": "BI staging folder", "value": "bi"},
                                    {"label": "Teams webhook", "value": "teams"},
                                    {"label": "Email summary", "value": "email"},
                                    {"label": "Optional PPTX deck", "value": "pptx"},
                                ],
                                value=["share", "bi"],
                                className="mb-2",
                            ),
                            html.Div(id="pub-destination-tips", className="mb-2"),
                            dbc.Checklist(
                                options=[{"label": "Dry-run (preview only)", "value": "dry"}],
                                value=["dry"],
                                id="pub-dryrun",
                                switch=True,
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "Preview / Publish",
                                        id="pub-run",
                                        className="nyc-btn-primary",
                                        **{"aria-label": "Run publish"},
                                    ),
                                    html.A(
                                        "Open example profile",
                                        href=f"file:///{str(EXAMPLE_PUBLISH_PROFILE).replace(chr(92), '/')}",
                                        target="_blank",
                                        style={"marginLeft": "12px", "fontSize": "0.85rem"},
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(id="pub-feedback"),
                            dcc.Interval(id="pub-run-poll", interval=1000, disabled=True, n_intervals=0),
                        ]
                    ),
                    style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"},
                ),
                html.H2("Pack summary", style={"fontSize": "1.1rem", "marginTop": "16px"}),
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    html.Div([html.Strong("Run date: "), html.Span(manifest.get("run_date", "—"))]),
                                    html.Div([html.Strong("Profile: "), html.Span(manifest.get("profile_name", "—"))]),
                                    html.Div(
                                        [
                                            html.Strong("Artifacts: "),
                                            html.Span(str(len(manifest.get("artifacts", {}) or {}))),
                                        ]
                                    ),
                                ],
                                style={"fontSize": "0.85rem"},
                            ),
                        ]
                    ),
                    style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"},
                ),
                dcc.Store(id="pub-last-report"),
            ],
        ),
    ],
    fluid=True,
)


_DEST_TIPS = {
    "share": "Copies pack artifacts to the configured UNC or local share path.",
    "bi": "Stages CSV/Excel extracts for Power BI refresh.",
    "teams": "Posts a summary card to the Teams incoming webhook.",
    "email": "Sends manifest summary and links via SMTP.",
    "pptx": "Builds an optional executive slide deck from pack HTML.",
}


@callback(
    Output("pub-destination-tips", "children"),
    Input("pub-destinations", "value"),
)
def show_destination_tips(dests):
    dests = dests or []
    return html.Div(
        [tip_card(d.replace("_", " ").title(), _DEST_TIPS.get(d, "Configured in publish_profile.yaml."), id=f"pub-tip-{d}") for d in dests]
        or [html.P("Select at least one destination.", style={"fontSize": "0.85rem", "color": "var(--text-muted)"})]
    )


@callback(
    Output("pub-feedback", "children"),
    Output("pub-run-poll", "disabled"),
    Input("pub-run", "n_clicks"),
    State("pub-pack-dir", "value"),
    State("pub-profile-path", "value"),
    State("pub-preset", "value"),
    State("pub-dryrun", "value"),
    prevent_initial_call=True,
)
def start_publish(_, pack_dir: str, profile_path: str, preset_path: str, dryrun_val: list[str]):
    global _publish_future
    if _publish_future is not None and not _publish_future.done():
        return (
            dbc.Alert("Publish is already running. Please wait.", color="warning"),
            False,
        )
    pack_path = Path(pack_dir) if pack_dir else None
    if not pack_path or not pack_path.exists():
        return html.Div(f"Pack not found: {pack_dir}", className="nyc-error-banner", role="alert"), True
    chosen = preset_path or profile_path
    prof = Path(chosen) if chosen else None
    if not prof or not prof.exists():
        return html.Div(f"Publish profile not found: {chosen}", className="nyc-error-banner", role="alert"), True

    dry_run = "dry" in (dryrun_val or [])
    cmd = [
        sys.executable,
        "-m",
        "socrata_toolkit.core.cli",
        "analyst",
        "publish",
        "--profile",
        str(prof),
        "--pack",
        str(pack_path),
    ]
    if dry_run:
        cmd.append("--dry-run")

    _publish_future = run_subprocess(cmd, cwd=str(ROOT), timeout=180)
    return (
        dbc.Alert(
            f"{'Dry-run' if dry_run else 'Publish'} started in the background.",
            color="info",
        ),
        False,
    )


@callback(
    Output("pub-feedback", "children", allow_duplicate=True),
    Output("pub-run-poll", "disabled", allow_duplicate=True),
    Output("pub-last-report", "data"),
    Input("pub-run-poll", "n_intervals"),
    prevent_initial_call=True,
)
def poll_publish(_):
    global _publish_future
    if _publish_future is None:
        raise PreventUpdate
    if not _publish_future.done():
        raise PreventUpdate
    try:
        proc = _publish_future.result()
    except Exception as exc:
        _publish_future = None
        return html.Div(str(exc), className="nyc-error-banner", role="alert"), True, {}
    _publish_future = None
    if proc.returncode != 0:
        return (
            html.Div(
                [html.Strong("Publish failed"), html.Pre(proc.stderr or proc.stdout)],
                className="nyc-error-banner",
                role="alert",
            ),
            True,
            {},
        )
    out = proc.stdout.strip()
    msg = dbc.Alert("Publish complete. Report captured.", color="success")
    return html.Div([msg, html.Details([html.Summary("View raw report JSON"), html.Pre(out)])]), True, {"raw": out}

