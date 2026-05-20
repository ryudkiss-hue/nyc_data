"""Analyst home — run pack, workflow, latest outputs."""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dash_app.data.analyst_pack import artifact_links, latest_pack_dir, load_manifest

dash.register_page(__name__, path="/", name="Home", order=0)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "config" / "analyst_profile.yaml"
EXAMPLE_PROFILE = ROOT / "config" / "analyst_profile.example.yaml"

_pack = latest_pack_dir()
_manifest = load_manifest(_pack)
_warnings = _manifest.get("warnings", [])
_partial = _manifest.get("partial_failures", [])


def _status_text() -> str:
    if not _pack:
        return "No Analyst Pack yet. Complete setup, then run your first pack."
    run_date = _manifest.get("run_date", "unknown")
    n = len(_manifest.get("artifacts", {}))
    health = "with warnings" if _warnings or _partial else "OK"
    return f"Last run: {run_date} — {n} artifacts ({health})"


layout = dbc.Container(
    [
        html.H1("Analyst Home", className="nyc-page-title"),
        html.P(_status_text(), className="nyc-page-sub", id="home-status-text"),
        html.Div(
            className="nyc-workflow-steps",
            children=[
                html.Div("1. Setup", className="nyc-workflow-step", **{"aria-current": "step"}),
                html.Div("2. Configure profile", className="nyc-workflow-step"),
                html.Div("3. Run pack", className="nyc-workflow-step"),
                html.Div("4. Review outputs", className="nyc-workflow-step"),
            ],
            role="list",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.H2("Run Analyst Pack", style={"fontSize": "1.25rem"}),
                    html.P(
                        "Runs `socrata analyst run` using your profile YAML. "
                        "Prefer CLI in production; this button is for local convenience.",
                        className="text-muted",
                    ),
                    dbc.Input(
                        id="home-profile-path",
                        value=str(
                            DEFAULT_PROFILE if DEFAULT_PROFILE.exists() else EXAMPLE_PROFILE
                        ),
                        className="mb-2",
                        **{"aria-label": "Analyst profile path"},
                    ),
                    html.Button(
                        "Run Analyst Pack",
                        id="home-run-pack",
                        className="nyc-btn-primary",
                        **{"aria-label": "Run analyst pack"},
                    ),
                    html.Div(id="home-run-feedback", className="mt-3"),
                ]
            ),
            className="mb-4",
            style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"},
        ),
        html.H2("Latest outputs", style={"fontSize": "1.1rem"}),
        html.Ul(
            [
                html.Li(
                    [
                        html.A(
                            item["label"],
                            href=f"file:///{item['path'].replace(chr(92), '/')}",
                            target="_blank",
                        )
                    ]
                )
                for item in artifact_links(_manifest)
            ]
            or [html.Li("No artifacts — run the analyst pack.")],
            id="home-artifact-list",
        ),
        html.Div(id="home-warnings"),
    ],
    fluid=True,
)


@callback(
    Output("home-run-feedback", "children"),
    Input("home-run-pack", "n_clicks"),
    State("home-profile-path", "value"),
    prevent_initial_call=True,
)
def run_pack(n, profile_path):
    if not profile_path or not Path(profile_path).exists():
        return html.Div(
            f"Profile not found: {profile_path}. Run: socrata analyst init-config",
            className="nyc-error-banner",
            role="alert",
        )
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "socrata_toolkit.core.cli", "analyst", "run", "--profile", profile_path],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(ROOT),
        )
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
    except subprocess.TimeoutExpired:
        return html.Div("Run timed out after 5 minutes.", className="nyc-error-banner", role="alert")
    except Exception as exc:
        return html.Div(str(exc), className="nyc-error-banner", role="alert")


@callback(Output("home-warnings", "children"), Input("home-run-pack", "n_clicks"))
def show_warnings(_):
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
