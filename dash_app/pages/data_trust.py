"""Data Trust page — visibility into sources, freshness, and warnings."""

from __future__ import annotations

from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, html

from dash_app.components.explainers import lineage_explainer
from dash_app.components.interactive import param_checkbox, tip_card
from dash_app.components.shell import empty_state, page_shell
from dash_app.data.analyst_pack import latest_pack_dir, load_manifest
from dash_app.data.state import load_state

dash.register_page(__name__, path="/data-trust", name="Data Trust", order=7)

ROOT = Path(__file__).resolve().parents[2]


def _default_pack() -> Path | None:
    st = load_state()
    p = st.get("last_pack_dir")
    if p and Path(p).exists():
        return Path(p)
    return latest_pack_dir()


def _sources_table(manifest: dict) -> html.Div:
    sources = manifest.get("sources") or {}
    if not sources:
        return html.P("No source stats found. Run an Analyst Pack first.", style={"color": "var(--text-muted)"})
    rows = []
    for name, s in sources.items():
        if not isinstance(s, dict):
            continue
        rows.append(
            html.Tr(
                [
                    html.Td(html.Code(name)),
                    html.Td(str(s.get("type", "—"))),
                    html.Td(str(s.get("status", "—"))),
                    html.Td(str(s.get("rows", "—"))),
                ]
            )
        )
    header = html.Thead(html.Tr([html.Th("Source"), html.Th("Authority"), html.Th("Status"), html.Th("Rows")]))
    body = html.Tbody(rows)
    return dbc.Table([header, body], bordered=True, hover=True, responsive=True, size="sm")


pack = _default_pack()
manifest = load_manifest(pack) if pack else {}

_trust_body = (
    [
        tip_card(
            "Source lineage",
            "Each connected source feeds specific pack artifacts. Use the diagram to trace provenance before publishing.",
            id="data-trust-lineage-tip",
        ),
        param_checkbox("Show manifest warnings", "dt-show-warnings", default=True),
        param_checkbox("Show partial failures", "dt-show-failures", default=True),
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Div([html.Strong("Pack: "), html.Span((pack.name if pack else "—"))]),
                            html.Div([html.Strong("Profile: "), html.Span(str(manifest.get("profile_name", "—")))]),
                            html.Div([html.Strong("Toolkit: "), html.Span(str(manifest.get("toolkit_version", "—")))]),
                        ],
                        style={"fontSize": "0.85rem"},
                    ),
                    html.Hr(style={"borderColor": "var(--border-color)"}),
                    html.H2("Source lineage", style={"fontSize": "1.0rem"}),
                    html.Div(id="dt-lineage"),
                    html.H2("Sources and authority", style={"fontSize": "1.0rem", "marginTop": "12px"}),
                    _sources_table(manifest),
                    html.H2("Warnings / partial failures", style={"fontSize": "1.0rem", "marginTop": "12px"}),
                    html.Div(id="dt-warnings-panel"),
                    html.H2("KPI derivations", style={"fontSize": "1.0rem", "marginTop": "12px"}),
                    html.P(
                        [
                            "Plain-language derivations live in the docs. See ",
                            html.A(
                                "USER_MANUAL.md",
                                href=f"file:///{str(ROOT / 'docs' / 'USER_MANUAL.md').replace(chr(92), '/')}",
                                target="_blank",
                            ),
                            " (Interactive exploration) and ",
                            html.A(
                                "PUBLISHING.md",
                                href=f"file:///{str(ROOT / 'docs' / 'PUBLISHING.md').replace(chr(92), '/')}",
                                target="_blank",
                            ),
                            ".",
                        ],
                        style={"fontSize": "0.85rem", "color": "var(--text-muted)"},
                    ),
                ]
            ),
            style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)"},
        ),
    ]
    if pack
    else [empty_state("No Analyst Pack loaded — run Analyst Pack to view source lineage.", show_demo=False)]
)

layout = dbc.Container(
    [
        *page_shell(
            "Data Trust",
            "Source lineage, freshness, warnings, and partial failures from the pack manifest.",
            page_key="data-trust",
            pack_dir=pack,
            children=_trust_body,
        ),
    ],
    fluid=True,
)


@callback(
    Output("dt-lineage", "children"),
    Input("dt-show-warnings", "value"),
)
def update_lineage(_):
    return lineage_explainer(manifest.get("sources") or {})


@callback(
    Output("dt-warnings-panel", "children"),
    Input("dt-show-warnings", "value"),
    Input("dt-show-failures", "value"),
)
def update_warnings(show_warn, show_fail):
    parts = []
    if show_warn:
        parts.append(
            html.Details(
                [html.Summary("Warnings"), html.Pre("\n".join(manifest.get("warnings") or []) or "(none)")],
            )
        )
    if show_fail:
        parts.append(
            html.Details(
                [
                    html.Summary("Partial failures"),
                    html.Pre(str(manifest.get("partial_failures") or []) or "(none)"),
                ],
            )
        )
    return parts or html.P("Warnings hidden — enable checkboxes above.", style={"color": "var(--text-muted)"})
