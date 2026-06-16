"""Shell layout components for NYC DOT Dash app."""

from __future__ import annotations

from dash import html


def page_shell(title: str, subtitle: str = "", page_key: str = "", children=None, **kwargs) -> list:
    """Wrap page content in the standard NYC DOT page shell layout."""
    return [
        html.Div(
            className="nyc-page-shell",
            children=[
                html.Div(
                    className="nyc-page-header",
                    children=[
                        html.H1(title, className="nyc-page-title"),
                        html.P(subtitle, className="nyc-page-subtitle") if subtitle else None,
                    ],
                ),
                html.Div(
                    className="nyc-page-body",
                    children=children or [],
                ),
            ],
        )
    ]


def empty_state(message: str, icon: str = "mdi:database-off", **kwargs):
    """Render an empty-state placeholder."""
    return html.Div(
        className="nyc-empty-state",
        children=[
            html.P(message, className="nyc-empty-state-message"),
        ],
    )
