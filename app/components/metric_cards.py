"""
Metric Card System: Dynamic Metric display for dashboard header.

Implements 18 Metric cards that fetch values from app_queries.v_metric_dashboard
and update dynamically on filter change.

Metric Categories:
1. Inspection Performance (5 Metrics)
2. Quality Metrics (5 Metrics)
3. Ramp Accessibility (4 Metrics)
4. Spatial Patterns (4 Metrics)

Usage in layouts:
    from app.components.metric_cards import render_metric_dashboard
    layout = html.Div([
        render_filter_bar(),
        render_metric_dashboard(),
        # rest of dashboard
    ])

Data flow:
    Filter change → store-global-filters updated
    → metric_callback fetches from v_metric_dashboard with filters
    → renders 18 dynamic Metric cards with loading states
"""

import logging
from typing import Any

import dash_mantine_components as dmc
from dash import ALL, Input, Output, callback, dcc, html

logger = logging.getLogger(__name__)

# Metric Configuration
METRIC_CONFIG = {
    "Inspection Performance": {
        "color": "blue",
        "icon": "📋",
        "metrics": [
            {"id": "total_inspections", "label": "Total Inspections", "unit": "", "metric": "count"},
            {"id": "inspection_rate", "label": "Inspection Rate", "unit": "/week", "metric": "rate"},
            {"id": "avg_violations_per_inspection", "label": "Avg Violations", "unit": "", "metric": "avg"},
            {"id": "critical_violations", "label": "Critical Violations", "unit": "", "metric": "count"},
            {"id": "inspection_backlog", "label": "Inspection Backlog", "unit": "days", "metric": "avg"},
        ]
    },
    "Quality Metrics": {
        "color": "grape",
        "icon": "✓",
        "metrics": [
            {"id": "data_completeness", "label": "Data Completeness", "unit": "%", "metric": "pct"},
            {"id": "data_validity", "label": "Data Validity", "unit": "%", "metric": "pct"},
            {"id": "data_consistency", "label": "Data Consistency", "unit": "%", "metric": "pct"},
            {"id": "data_freshness", "label": "Data Freshness", "unit": "days", "metric": "avg"},
            {"id": "quality_score", "label": "Overall Quality", "unit": "/100", "metric": "score"},
        ]
    },
    "Ramp Accessibility": {
        "color": "green",
        "icon": "♿",
        "metrics": [
            {"id": "ramp_completion_rate", "label": "Ramp Completion", "unit": "%", "metric": "pct"},
            {"id": "ramp_complaints", "label": "Ramp Complaints", "unit": "", "metric": "count"},
            {"id": "ramp_progress_month", "label": "Progress This Month", "unit": "", "metric": "count"},
            {"id": "ramp_sla_breach", "label": "SLA Breach Risk", "unit": "%", "metric": "pct"},
        ]
    },
    "Spatial Patterns": {
        "color": "orange",
        "icon": "🗺️",
        "metrics": [
            {"id": "morans_i_statistic", "label": "Moran's I", "unit": "", "metric": "stat"},
            {"id": "spatial_clusters", "label": "Spatial Clusters", "unit": "", "metric": "count"},
            {"id": "hotspot_concentration", "label": "Hotspot Concentration", "unit": "%", "metric": "pct"},
            {"id": "outlier_count", "label": "Anomaly Count", "unit": "", "metric": "count"},
        ]
    },
}

def render_metric_dashboard() -> html.Div:
    """
    Render the 18 Metric cards organized by category.

    Returns:
        html.Div: Metric dashboard with 4 categories × 5 Metrics (18 total)
    """
    sections = []

    for category, config in METRIC_CONFIG.items():
        metric_cards = []
        for metric in config["metrics"]:
            card = dmc.Paper(
                withBorder=True,
                p="md",
                radius="lg",
                shadow="xs",
                style={
                    "flex": 1,
                    "minWidth": "200px",
                    "backgroundColor": "#ffffff",
                    "borderColor": f"var(--mantine-color-{config['color']}-2)",
                    "borderWidth": "2px",
                },
                children=[
                    dmc.Group(
                        [
                            dmc.Text(config["icon"], size="xl"),
                            dmc.Text(metric["label"], size="xs", c="dimmed", fw=500),
                        ],
                        gap="xs",
                    ),
                    dmc.Group(
                        [
                            dmc.Text(
                                id={"type": "metric-value", "index": metric["id"]},
                                children="—",
                                size="xl",
                                fw=700,
                                c=config["color"],
                            ),
                            dmc.Text(
                                metric["unit"],
                                size="sm",
                                c="dimmed",
                            ),
                        ],
                        gap="xs",
                        align="baseline",
                    ),
                    dmc.Text(
                        id={"type": "metric-change", "index": metric["id"]},
                        size="xs",
                        c="gray",
                        style={"marginTop": "8px"},
                    ),
                ],
            )
            metric_cards.append(card)

        # Section with title
        section = dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text(category, size="lg", fw=700, c=config["color"]),
                        dmc.Badge(
                            len(config["metrics"]),
                            color=config["color"],
                            variant="light",
                            size="lg",
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Group(
                    metric_cards,
                    grow=True,
                    gap="md",
                ),
            ],
            gap="md",
            style={"marginBottom": "24px"},
        )
        sections.append(section)

    return html.Div(
        [
            dmc.Stack(sections, gap="xl"),
            dcc.Loading(
                id="metric-loading",
                type="default",
                children=html.Div(id="metric-loading-placeholder"),
            ),
        ],
        style={"padding": "20px"},
    )

def register_metric_callbacks() -> None:
    """
    Register callbacks for Metric card updates.

    Callback:
    - store-global-filters change → fetch from v_metric_dashboard
    - Update all 18 Metric card values + change indicators
    """

    @callback(
        Output({"type": "metric-value", "index": ALL}, "children"),
        Output({"type": "metric-change", "index": ALL}, "children"),
        Input("store-global-filters", "data"),
        prevent_initial_call=False,
    )
    def update_metric_values(filters: dict[str, Any]) -> tuple:
        """
        Fetch and display Metric values from MotherDuck.

        Args:
            filters: Global filter state (boroughs, date_start, date_end, metric_type)

        Returns:
            tuple: (metric_values, change_indicators)
        """
        try:
            from app.services.motherduck_service import fetch_metric_data

            # Fetch Metric data from v_metric_dashboard
            metric_data = fetch_metric_data(filters)
            metric_count = sum(len(cat["metrics"]) for cat in METRIC_CONFIG.values())
            if metric_data is None or metric_data.empty:
                logger.warning("No Metric data available")
                return ["—"] * metric_count, ["N/A"] * metric_count

            # Extract values in Metric config order
            values = []
            changes = []

            for category_config in METRIC_CONFIG.values():
                for metric in category_config["metrics"]:
                    metric_id = metric["id"]
                    # Look up value in metric_data
                    row = metric_data[metric_data["metric_id"] == metric_id]
                    if not row.empty:
                        value = row.iloc[0].get("value", None)
                        change = row.iloc[0].get("change_pct", 0)

                        # Format value based on metric type
                        if metric["metric"] in ["pct", "score"]:
                            formatted_value = f"{value:.1f}" if value else "—"
                        else:
                            formatted_value = f"{value:,.0f}" if value else "—"

                        values.append(formatted_value)
                        changes.append(f"↑ {change:+.1f}%" if change else "→ No change")
                    else:
                        values.append("—")
                        changes.append("N/A")

            logger.info(f"Metric values updated for filters: {filters}")
            return values, changes

        except Exception as e:
            logger.error(f"Error updating Metric values: {e}", exc_info=True)
            # Return empty values for all Metrics on error
            metric_count = sum(len(cat["metrics"]) for cat in METRIC_CONFIG.values())
            return ["—"] * metric_count, ["Error"] * metric_count
