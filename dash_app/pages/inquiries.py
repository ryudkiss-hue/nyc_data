"""Inquiry draft preview and copy-to-clipboard."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dash_app.data.analyst_pack import latest_pack_dir, load_manifest

dash.register_page(__name__, path="/inquiries", name="Inquiries", order=4)

pack = latest_pack_dir()
manifest = load_manifest(pack)
drafts: list = []
if pack:
    inq_dir = pack / "inquiry_drafts"
    if inq_dir.exists():
        drafts = sorted(inq_dir.glob("*.md"))

sections = []
for i, path in enumerate(drafts):
    body = path.read_text(encoding="utf-8")
    sections.append(
        dbc.AccordionItem(
            [
                html.Pre(body, style={"whiteSpace": "pre-wrap"}, id=f"inquiry-text-{i}"),
                html.Button(
                    "Copy to clipboard",
                    id={"type": "copy-inquiry", "index": i},
                    className="nyc-btn-primary mt-2",
                    style={"fontSize": "0.85rem", "padding": "0.4rem 1rem"},
                    **{"aria-label": f"Copy {path.name} to clipboard"},
                ),
                html.Div(id={"type": "copy-msg", "index": i}, className="mt-1"),
            ],
            title=path.name,
        )
    )

layout = dbc.Container(
    [
        html.H1("Inquiries", className="nyc-page-title"),
        html.P(
            f"Pack: {manifest.get('run_date', 'n/a')} — templates from config/inquiry_templates/",
            className="nyc-page-sub",
        ),
        dbc.Accordion(sections, start_collapsed=True, flush=True)
        if sections
        else html.P("No inquiry drafts — enable inquiry_templates in analyst profile."),
        dcc.Store(id="inquiry-copy-store"),
    ],
    fluid=True,
)


@callback(
    Output({"type": "copy-msg", "index": dash.MATCH}, "children"),
    Input({"type": "copy-inquiry", "index": dash.MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def copy_hint(n):
    return html.Span("Select text and press Ctrl+C, or use browser copy.", className="text-muted small")
