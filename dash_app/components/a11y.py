"""Accessibility helpers for Dash (WCAG-minded)."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import dash_table, html


def sr_only(text: str) -> html.Div:
    return html.Div(text, className="sr-only")


def accessible_graph(figure, *, summary: str, graph_id: str | None = None) -> html.Div:
    """Wrap Plotly graph with screen-reader summary."""
    from dash import dcc

    return html.Div(
        [
            sr_only(summary),
            dcc.Graph(
                id=graph_id,
                figure=figure,
                config={"displayModeBar": False},
                **{"aria-hidden": "true"},
            ),
        ],
        role="img",
        **{"aria-label": summary},
    )


def accessible_table(
    df,
    *,
    table_id: str,
    caption: str,
    page_size: int = 25,
) -> html.Div:
    return html.Div(
        [
            html.Caption(caption, style={"captionSide": "top", "padding": "8px 0"}),
            dash_table.DataTable(
                id=table_id,
                data=df.to_dict("records") if hasattr(df, "to_dict") else df,
                page_size=page_size,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px"},
                style_header={"fontWeight": "600"},
            ),
        ],
        role="region",
        **{"aria-label": caption},
    )


def focus_ring_style() -> dict[str, str]:
    return {"outline": "none", "boxShadow": "var(--focus-ring)"}
