"""Construction management page."""

from __future__ import annotations

from dash import html

layout = html.Div(
    id="construction-page",
    children=[
        html.H1("Construction Management"),
        html.Div(id="construction-content"),
    ],
)
