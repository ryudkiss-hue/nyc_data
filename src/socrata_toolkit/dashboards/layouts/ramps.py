"""Ramp Accessibility Page Layout."""
import dash_bootstrap_components as dbc
from dash import html

layout = dbc.Container([
    dbc.Row([dbc.Col([html.H2("Ramp Accessibility", className="mb-4")], width=12)]),
    dbc.Row([dbc.Col([
        dbc.Alert("🚧 Page under construction. Implementing ramp completion visualizations.", color="info")
    ], width=12)]),
], fluid=True, className="mt-4")
