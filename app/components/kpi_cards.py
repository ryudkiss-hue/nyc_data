"""
KPI Card System: Dynamic KPI display for dashboard header.

Implements 18 KPI cards that fetch values from app_queries.v_kpi_dashboard
and update dynamically on filter change.

KPI Categories:
1. Inspection Performance (5 KPIs)
2. Quality Metrics (5 KPIs)
3. Ramp Accessibility (4 KPIs)
4. Spatial Patterns (4 KPIs)

Usage in layouts:
    from app.components.kpi_cards import render_kpi_dashboard
    layout = html.Div([
        render_filter_bar(),
        render_kpi_dashboard(),
        # rest of dashboard
    ])

Data flow:
    Filter change → store-global-filters updated
    → kpi_callback fetches from v_kpi_dashboard with filters
    → renders 18 dynamic KPI cards with loading states
"""

import logging
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
from dash import ALL, Input, Output, State, callback, dcc, html

logger = logging.getLogger(__name__)

# KPI Configuration
KPI_CONFIG = {
    "Inspection Performance": {
        "color": "blue",
        "icon": "📋",
        "kpis": [
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
        "kpis": [
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
        "kpis": [
            {"id": "ramp_completion_rate", "label": "Ramp Completion", "unit": "%", "metric": "pct"},
            {"id": "ramp_complaints", "label": "Ramp Complaints", "unit": "", "metric": "count"},
            {"id": "ramp_progress_month", "label": "Progress This Month", "unit": "", "metric": "count"},
            {"id": "ramp_sla_breach", "label": "SLA Breach Risk", "unit": "%", "metric": "pct"},
        ]
    },
    "Spatial Patterns": {
        "color": "orange",
        "icon": "🗺️",
        "kpis": [
            {"id": "morans_i_statistic", "label": "Moran's I", "unit": "", "metric": "stat"},
            {"id": "spatial_clusters", "label": "Spatial Clusters", "unit": "", "metric": "count"},
            {"id": "hotspot_concentration", "label": "Hotspot Concentration", "unit": "%", "metric": "pct"},
            {"id": "outlier_count", "label": "Anomaly Count", "unit": "", "metric": "count"},
        ]
    },
}

def render_kpi_dashboard() -> html.Div:
    """
    Render the 18 KPI cards organized by category.

    Returns:
        html.Div: KPI dashboard with 4 categories × 5 KPIs (18 total)
    """
    sections = []

    for category, config in KPI_CONFIG.items():
        kpi_cards = []
        for kpi in config["kpis"]:
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
                            dmc.Text(kpi["label"], size="xs", c="dimmed", fw=500),
                        ],
                        spacing="xs",
                    ),
                    dmc.Group(
                        [
                            dmc.Text(
                                id={"type": "kpi-value", "index": kpi["id"]},
                                children="—",
                                size="xl",
                                fw=700,
                                c=config["color"],
                            ),
                            dmc.Text(
                                kpi["unit"],
                                size="sm",
                                c="dimmed",
                            ),
                        ],
                        spacing="xs",
                        align="baseline",
                    ),
                    dmc.Text(
                        id={"type": "kpi-change", "index": kpi["id"]},
                        size="xs",
                        c="gray",
                        style={"marginTop": "8px"},
                    ),
                ],
            )
            kpi_cards.append(card)

        # Section with title
        section = dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text(category, size="lg", fw=700, c=config["color"]),
                        dmc.Badge(
                            len(config["kpis"]),
                            color=config["color"],
                            variant="light",
                            size="lg",
                        ),
                    ],
                    spacing="sm",
                ),
                dmc.Group(
                    kpi_cards,
                    grow=True,
                    spacing="md",
                ),
            ],
            spacing="md",
            style={"marginBottom": "24px"},
        )
        sections.append(section)

    return html.Div(
        [
            dmc.Stack(sections, spacing="xl"),
            dcc.Loading(
                id="kpi-loading",
                type="default",
                children=html.Div(id="kpi-loading-placeholder"),
            ),
        ],
        style={"padding": "20px"},
    )

def register_kpi_callbacks() -> None:
    """
    Register callbacks for KPI card updates.

    Callback:
    - store-global-filters change → fetch from v_kpi_dashboard
    - Update all 18 KPI card values + change indicators
    """

    @callback(
        Output({"type": "kpi-value", "index": ALL}, "children"),
        Output({"type": "kpi-change", "index": ALL}, "children"),
        Input("store-global-filters", "data"),
        prevent_initial_call=False,
    )
    def update_kpi_values(filters: dict[str, Any]) -> tuple:
        """
        Fetch and display KPI values from MotherDuck.

        Args:
            filters: Global filter state (boroughs, date_start, date_end, metric_type)

        Returns:
            tuple: (kpi_values, change_indicators)
        """
        try:
            from app.services.motherduck_service import fetch_kpi_data

            # Fetch KPI data from v_kpi_dashboard
            kpi_data = fetch_kpi_data(filters)
            if kpi_data is None or kpi_data.empty:
                logger.warning("No KPI data available")
                return [], []

            # Extract values in KPI config order
            values = []
            changes = []

            for category_config in KPI_CONFIG.values():
                for kpi in category_config["kpis"]:
                    kpi_id = kpi["id"]
                    # Look up value in kpi_data
                    row = kpi_data[kpi_data["metric_id"] == kpi_id]
                    if not row.empty:
                        value = row.iloc[0].get("value", None)
                        change = row.iloc[0].get("change_pct", 0)

                        # Format value based on metric type
                        if kpi["metric"] in ["pct", "score"]:
                            formatted_value = f"{value:.1f}" if value else "—"
                        else:
                            formatted_value = f"{value:,.0f}" if value else "—"

                        values.append(formatted_value)
                        changes.append(f"↑ {change:+.1f}%" if change else "→ No change")
                    else:
                        values.append("—")
                        changes.append("N/A")

            logger.info(f"KPI values updated for filters: {filters}")
            return values, changes

        except Exception as e:
            logger.error(f"Error updating KPI values: {e}", exc_info=True)
            # Return empty values for all KPIs on error
            kpi_count = sum(len(cat["kpis"]) for cat in KPI_CONFIG.values())
            return ["—"] * kpi_count, ["Error"] * kpi_count
