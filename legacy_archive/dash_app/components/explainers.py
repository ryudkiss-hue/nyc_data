"""Plain-language explainer content for interactive pages."""

from __future__ import annotations

from dash import html

from dash_app.components.interactive import tip_card


def construction_scoring_explainer() -> html.Div:
    return tip_card(
        "How is priority score calculated?",
        (
            "Each location gets a score from 0 to 1 by combining normalized factors: "
            "severity (30%), pedestrian volume (20%), age since issued (15%), "
            "ADA flag (15%), Smart Spine corridor (10%), and 311 complaints (10%). "
            "Sliders on this page adjust those weights for what-if preview only — "
            "the Analyst Pack run still uses your profile defaults until you apply changes."
        ),
        id="explainer-construction-score",
    )


def evm_explainer_diagram() -> html.Div:
    return html.Div(
        className="nyc-evm-explainer",
        children=[
            tip_card(
                "Earned Value Management (EVM) basics",
                (
                    "Planned Value (PV) is the budgeted cost of work scheduled. "
                    "Earned Value (EV) is the budgeted cost of work performed. "
                    "Actual Cost (AC) is what you spent. "
                    "Cost Performance Index (CPI) = EV ÷ AC — above 1.0 means under budget; "
                    "below 1.0 means over budget. Schedule Performance Index (SPI) = EV ÷ PV."
                ),
                id="explainer-evm-text",
            ),
            html.Div(
                className="nyc-evm-svg-wrap",
                role="img",
                **{"aria-label": "EVM diagram: planned bar, earned bar, actual bar"},
                children=[
                    html.Div(
                        className="nyc-evm-bar nyc-evm-planned",
                        children=[html.Span("Planned (PV)", className="nyc-evm-label")],
                        title="Budgeted work scheduled",
                    ),
                    html.Div(
                        className="nyc-evm-bar nyc-evm-earned",
                        children=[html.Span("Earned (EV)", className="nyc-evm-label")],
                        title="Budgeted work completed",
                    ),
                    html.Div(
                        className="nyc-evm-bar nyc-evm-actual",
                        children=[html.Span("Actual (AC)", className="nyc-evm-label")],
                        title="Money spent",
                    ),
                ],
            ),
            html.P(
                "Hover each bar for a short definition. CPI compares earned value to actual cost.",
                className="nyc-evm-caption",
            ),
        ],
    )


def kpi_metric_explainer(metric_name: str, description: str, metric_id: str) -> html.Div:
    return tip_card(
        f"What does “{metric_name}” mean?",
        description or "See METRICS_GLOSSARY.md for the full definition.",
        id=f"explainer-kpi-{metric_id}",
    )


_KPI_DESCRIPTIONS: dict[str, str] = {
    "backlog": "Open high-severity locations not yet on the construction list.",
    "completion": "Share of planned repair locations completed this period.",
    "conflicts": "Locations where proposed work overlaps active permits.",
    "ada": "ADA-flagged or highest-severity items requiring accessible treatment.",
    "budget": "Spend vs plan; CPI below 1.0 signals cost overrun risk.",
    "productivity": "Square feet completed per crew-day — throughput indicator.",
}


def default_kpi_description(name: str) -> str:
    key = name.lower().split()[0] if name else ""
    for token, desc in _KPI_DESCRIPTIONS.items():
        if token in name.lower():
            return desc
    return f"Program metric: {name}. Compare value to target; green = on track, yellow = at risk, red = critical."


def lineage_explainer(sources: dict) -> html.Div:
    if not sources:
        return html.P("Run an Analyst Pack to see source → artifact lineage.", className="nyc-page-sub")
    nodes = []
    for name in sorted(sources.keys()):
        nodes.append(
            html.Div(
                className="nyc-lineage-node",
                children=[
                    html.Span(name, className="nyc-lineage-source"),
                    html.I(className="bi bi-arrow-right", **{"aria-hidden": "true"}),
                    html.Span("pack artifacts", className="nyc-lineage-artifact"),
                ],
            )
        )
    return html.Div(
        className="nyc-lineage-diagram",
        role="list",
        **{"aria-label": "Data source lineage"},
        children=nodes,
    )
