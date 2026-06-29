"""
Filter System: Borough, Date Range, Metric Type selectors for dashboard.

Implements a centralized filter UI component that broadcasts to all callbacks
via the 'store-global-filters' dcc.Store component.

Components:
- Borough selector (MN, BX, BK, QN, SI)
- Date range picker (start, end)
- Metric type selector (all, critical, active, etc.)

Usage in layouts:
    from app.components.filter_system import render_filter_bar
    layout = html.Div([
        render_filter_bar(),
        # rest of dashboard
    ])

Data flow:
    User selects filter → callback updates store-global-filters
    → all phase callbacks receive filter data
    → visualizations update with filtered data
"""

import logging
from typing import Any

import dash_mantine_components as dmc
from dash import Input, Output, State, callback, html

logger = logging.getLogger(__name__)

# Constants
BOROUGHS = [
    {"label": "Manhattan", "value": "MN"},
    {"label": "Brooklyn", "value": "BK"},
    {"label": "Bronx", "value": "BX"},
    {"label": "Queens", "value": "QN"},
    {"label": "Staten Island", "value": "SI"},
]

METRIC_TYPES = [
    {"label": "All Metrics", "value": "all"},
    {"label": "Critical Only", "value": "critical"},
    {"label": "Active Cases", "value": "active"},
    {"label": "Completed", "value": "completed"},
]


def render_filter_bar() -> html.Div:
    """
    Render the filter bar with borough, date range, and metric selectors.

    Returns:
        html.Div: Filter bar component containing all filter controls

    Layout:
        ┌─────────────────────────────────────────────┐
        │ 🏙️ Borough │ 📅 Date Range │ 📊 Metric Type │
        └─────────────────────────────────────────────┘
    """
    return html.Div(
        [
            dmc.Group(
                [
                    # Dataset Selector
                    dmc.MultiSelect(
                        id="filter-dataset-select",
                        label="Datasets",
                        searchable=True,
                        clearable=True,
                        data=[
                            {"label": "Capital Projects", "value": "capital_projects"},
                            {"label": "Street Paving", "value": "street_paving"},
                            {"label": "Vision Zero", "value": "vision_zero"},
                            {"label": "311 Complaints", "value": "311_complaints"}
                        ],
                        value=["capital_projects", "street_paving", "vision_zero", "311_complaints"],
                        style={"flex": 1, "minWidth": "200px"},
                    ),
                    # Data Limit Selector
                    dmc.Select(
                        id="filter-data-limit",
                        label="Data Limit",
                        data=[
                            {"label": "None (Unlimited)", "value": "none"},
                            {"label": "1,000 records", "value": "1000"},
                            {"label": "10,000 records", "value": "10000"},
                            {"label": "100,000 records", "value": "100000"}
                        ],
                        value="none",
                        style={"flex": 1, "minWidth": "150px"},
                    ),
                ],
                grow=True,
                gap="md",
                mb="md"
            ),
            dmc.Group(
                [
                    # Borough Selector
                    dmc.MultiSelect(
                        id="filter-borough-select",
                        label="Borough",
                        searchable=True,
                        clearable=True,
                        data=BOROUGHS,
                        value=["MN", "BK", "BX", "QN", "SI"],  # Default: all
                        style={"flex": 1, "minWidth": "200px"},
                    ),
                    # Date Range Picker
                    dmc.DateInput(
                        id="filter-date-start",
                        label="Start Date",
                        placeholder="Start date",
                        valueFormat="YYYY-MM-DD",
                        style={"flex": 1, "minWidth": "150px"},
                    ),
                    dmc.DateInput(
                        id="filter-date-end",
                        label="End Date",
                        placeholder="End date",
                        valueFormat="YYYY-MM-DD",
                        style={"flex": 1, "minWidth": "150px"},
                    ),
                    # Metric Type Selector
                    dmc.Select(
                        id="filter-metric-type",
                        label="Metric Type",
                        data=METRIC_TYPES,
                        value="all",
                        searchable=True,
                        clearable=False,
                        style={"flex": 1, "minWidth": "180px"},
                    ),
                    # Apply/Reset Buttons
                    dmc.Group(
                        [
                            dmc.Button(
                                "Apply Filters",
                                id="filter-apply-btn",
                                size="sm",
                                variant="filled",
                                color="blue",
                            ),
                            dmc.Button(
                                "Reset",
                                id="filter-reset-btn",
                                size="sm",
                                variant="outline",
                                color="gray",
                            ),
                        ],
                        grow=False,
                        gap="sm",
                        align="flex-end"
                    ),
                ],
                grow=True,
                gap="md",
            ),
            # Loading indicator
            dmc.LoadingOverlay(
                id="filter-loading-overlay",
                visible=False,
                loaderProps={"type": "bars", "color": "blue"},

            ),
        ],
        style={
            "padding": "20px",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "8px",
            "marginBottom": "20px",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
        },
    )


def register_filter_callbacks() -> None:
    """
    Register callbacks for filter system.

    Callbacks:
    1. Apply button → updates store-global-filters
    2. Reset button → clears all filters
    3. Filter changes → broadcasts to all phase callbacks
    """

    @callback(
        Output("store-global-filters", "data"),
        Input("filter-apply-btn", "n_clicks"),
        Input("filter-reset-btn", "n_clicks"),
        State("filter-borough-select", "value"),
        State("filter-date-start", "value"),
        State("filter-date-end", "value"),
        State("filter-metric-type", "value"),
        State("filter-dataset-select", "value"),
        State("filter-data-limit", "value"),
        prevent_initial_call=True,
    )
    def update_global_filters(
        apply_clicks: int,
        reset_clicks: int,
        boroughs: list[str],
        date_start: str,
        date_end: str,
        metric_type: str,
        datasets: list[str],
        data_limit: str,
    ) -> dict[str, Any]:
        """
        Update global filter store on apply/reset button click.

        Args:
            apply_clicks: Number of apply button clicks
            reset_clicks: Number of reset button clicks
            boroughs: Selected boroughs (list of strings)
            date_start: Start date (ISO format)
            date_end: End date (ISO format)
            metric_type: Selected metric type
            datasets: Selected datasets (list of strings)
            data_limit: Data limit as string ('none', '1000', etc)

        Returns:
            dict: Updated filter dictionary to be stored in dcc.Store
        """
        ctx_id = None
        try:
            from dash import ctx

            ctx_id = ctx.triggered_id if ctx.triggered_id else None
        except Exception:
            pass

        # Reset button clicked → clear all filters
        if ctx_id == "filter-reset-btn":
            logger.info("Filters reset to defaults")
            return {
                "boroughs": ["MN", "BK", "BX", "QN", "SI"],
                "date_start": None,
                "date_end": None,
                "metric_type": "all",
                "datasets": ["capital_projects", "street_paving", "vision_zero", "311_complaints"],
                "data_limit": "none",
            }

        # Apply button clicked → update filters
        if ctx_id == "filter-apply-btn":
            filters_dict = {
                "boroughs": boroughs or ["MN", "BK", "BX", "QN", "SI"],
                "date_start": date_start,
                "date_end": date_end,
                "metric_type": metric_type or "all",
                "datasets": datasets or ["capital_projects", "street_paving", "vision_zero", "311_complaints"],
                "data_limit": data_limit or "none",
            }
            logger.info(f"Filters applied: {filters_dict}")
            return filters_dict

        # Default: return current filter state
        return {
            "boroughs": boroughs or ["MN", "BK", "BX", "QN", "SI"],
            "date_start": date_start,
            "date_end": date_end,
            "metric_type": metric_type or "all",
            "datasets": datasets or ["capital_projects", "street_paving", "vision_zero", "311_complaints"],
            "data_limit": data_limit or "none",
        }
