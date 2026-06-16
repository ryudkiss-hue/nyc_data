"""Settings Page Layout."""
import dash_bootstrap_components as dbc
from dash import html

layout = dbc.Container([
    dbc.Row([dbc.Col([html.H2("Settings", className="mb-4")], width=12)]),
    dbc.Row([dbc.Col([
        dbc.Alert("🚧 Page under construction. Theme, export, and refresh settings.", color="info")
    ], width=12)]),
], fluid=True, className="mt-4")
