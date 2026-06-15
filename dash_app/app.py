"""Dash application entry point for the NYC DOT Socrata Toolkit."""

from __future__ import annotations

import dash
from dash import html

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "NYC DOT Socrata Toolkit"

app.layout = html.Div(
    id="app-root",
    children=[
        html.Div(id="page-content"),
    ],
)

server = app.server

if __name__ == "__main__":
    app.run(debug=True)
