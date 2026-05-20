"""Accessible interactive controls for analyst exploration."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html


def tip_card(title: str, body: str, id: str) -> html.Div:
    """Collapsible help card with keyboard-accessible summary."""
    return html.Div(
        className="nyc-tip-card",
        children=[
            html.Details(
                [
                    html.Summary(
                        [html.Span(title, className="nyc-tip-title")],
                        id=f"{id}-summary",
                        **{"aria-controls": f"{id}-body"},
                    ),
                    html.Div(
                        body if isinstance(body, (list, tuple)) else html.P(body, className="nyc-tip-body"),
                        id=f"{id}-body",
                        className="nyc-tip-body-wrap",
                        role="region",
                        **{"aria-labelledby": f"{id}-summary"},
                    ),
                ],
                className="nyc-tip-details",
            ),
        ],
        id=id,
    )


def param_slider(
    label: str,
    min_val: float,
    max_val: float,
    step: float,
    default: float,
    id: str,
    *,
    aria_label: str | None = None,
    marks: dict[int | float, str] | None = None,
) -> html.Div:
    """Labeled range slider with visible value and screen-reader label."""
    aria = aria_label or label
    return html.Div(
        className="nyc-param-control",
        role="group",
        **{"aria-label": aria},
        children=[
            html.Label(
                [html.Span(label, className="nyc-param-label"), html.Span(id=f"{id}-value", className="nyc-param-value")],
                htmlFor=id,
            ),
            dcc.Slider(
                id=id,
                min=min_val,
                max=max_val,
                step=step,
                value=default,
                marks=marks,
                tooltip={"placement": "bottom", "always_visible": False},
                className="nyc-slider",
            ),
            html.Span(id=f"{id}-sr", className="visually-hidden", **{"aria-live": "polite"}),
        ],
    )


def param_checkbox(
    label: str,
    id: str,
    *,
    default: bool = False,
    aria_label: str | None = None,
) -> html.Div:
    return html.Div(
        className="nyc-param-control nyc-param-checkbox",
        children=[
            dbc.Checkbox(
                id=id,
                label=label,
                value=default,
                className="nyc-checkbox",
            ),
        ],
    )


def param_scale(
    label: str,
    id: str,
    *,
    default: int = 3,
    aria_label: str | None = None,
) -> html.Div:
    """1–5 subjective weight scale (radio buttons for keyboard access)."""
    options = [
        {"label": str(i), "value": i}
        for i in range(1, 6)
    ]
    return html.Div(
        className="nyc-param-control nyc-param-scale",
        children=[
            html.Label(label, className="nyc-param-label", htmlFor=f"{id}-1"),
            dbc.RadioItems(
                id=id,
                options=options,
                value=default,
                inline=True,
                className="nyc-scale-radios",
                inputClassName="nyc-scale-input",
            ),
        ],
    )


def interactive_diagram(
    figure: go.Figure | None,
    id: str,
    *,
    title: str = "",
    empty_message: str = "No data to chart yet.",
) -> html.Div:
    if figure is None:
        return html.Div(
            empty_message,
            className="nyc-diagram-empty",
            id=id,
            role="img",
            **{"aria-label": empty_message},
        )
    fig = figure
    if title:
        fig.update_layout(title=title)
    fig.update_layout(margin=dict(l=40, r=20, t=40, b=40), height=280)
    return html.Div(
        className="nyc-interactive-diagram",
        children=[
            dcc.Graph(
                id=id,
                figure=fig,
                config={"displayModeBar": True, "scrollZoom": True},
                **{"aria-label": title or "Interactive chart"},
            ),
        ],
    )


def feedback_toast(region_id: str = "nyc-feedback-toast") -> html.Div:
    return html.Div(
        id=region_id,
        className="nyc-feedback-toast",
        role="status",
        **{"aria-live": "polite", "aria-atomic": "true"},
    )


def step_hint(text: str, *, id: str | None = None) -> html.Div:
    return html.Div(
        className="nyc-step-hint",
        children=[
            html.I(className="bi bi-lightbulb", **{"aria-hidden": "true"}),
            html.Span(text),
        ],
        id=id,
    )


def loading_spinner(target_id: str) -> Any:
    return dbc.Spinner(
        html.Div(id=target_id),
        size="sm",
        color="primary",
        spinner_class_name="nyc-spinner",
    )
