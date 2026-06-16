"""
GIS Dashboard layout for Dash.
Week 1-3 Phase 1 GIS Pilot - Layout extraction from Streamlit.
Contains filter controls, map visualizations, and data stores.
"""

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify


def layout_gis():
    """
    Complete GIS Dashboard layout.
    Includes:
    - Filter controls (borough, severity, date range)
    - Primary visualizations (condition map, hotspot, conflict detection)
    - Secondary visualizations (borough aggregation, clustering)
    - Data stores for session state management
    """
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            # ===== HEADER =====
            dmc.Group(
                [
                    dmc.Group(
                        [
                            DashIconify(
                                icon="mdi:map-search", width=32, color="#0033A0"
                            ),
                            dmc.Text(
                                "GIS & SPATIAL INTELLIGENCE",
                                fw=900,
                                size="xl",
                                c="black",
                            ),
                        ]
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Refresh Data",
                                id="btn-gis-refresh",
                                leftSection=DashIconify(
                                    icon="mdi:refresh", width=16
                                ),
                                variant="default",
                                size="sm",
                            ),
                            dmc.Button(
                                "Export CSV",
                                id="btn-export-csv",
                                leftSection=DashIconify(
                                    icon="mdi:download", width=16
                                ),
                                variant="default",
                                size="sm",
                            ),
                        ],
                        gap="md",
                    ),
                ],
                justify="space-between",
                mb="lg",
            ),
            # ===== DATA STORES =====
            dcc.Store(
                id="gis-session-filters",
                storage_type="session",
                data={},
            ),
            dcc.Store(
                id="gis-data-store",
                storage_type="memory",
                data={},
            ),
            dcc.Store(
                id="gis-permits-store",
                storage_type="memory",
                data={},
            ),
            dcc.Store(
                id="gis-export-trigger",
                storage_type="memory",
            ),
            dcc.Download(id="download-gis-csv"),
            # ===== FILTERS ROW =====
            dmc.Paper(
                p="lg",
                withBorder=True,
                radius="lg",
                mb="lg",
                children=[
                    dmc.Text(
                        "Filters",
                        fw=700,
                        size="md",
                        mb="md",
                    ),
                    dmc.Grid(
                        [
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.MultiSelect(
                                        id="gis-borough-filter",
                                        label="Borough",
                                        placeholder="Select boroughs",
                                        searchable=True,
                                        clearable=True,
                                        data=[
                                            {
                                                "value": "MANHATTAN",
                                                "label": "Manhattan",
                                            },
                                            {
                                                "value": "BROOKLYN",
                                                "label": "Brooklyn",
                                            },
                                            {"value": "QUEENS", "label": "Queens"},
                                            {"value": "BRONX", "label": "Bronx"},
                                            {
                                                "value": "STATEN_ISLAND",
                                                "label": "Staten Island",
                                            },
                                        ],
                                        value=["MANHATTAN", "BROOKLYN"],
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.Select(
                                        id="gis-severity-filter",
                                        label="Severity",
                                        placeholder="All Severities",
                                        searchable=True,
                                        data=[
                                            {"value": "ALL", "label": "All"},
                                            {
                                                "value": "CRITICAL",
                                                "label": "Critical (0-30)",
                                            },
                                            {
                                                "value": "HIGH",
                                                "label": "High (31-60)",
                                            },
                                            {
                                                "value": "MEDIUM",
                                                "label": "Medium (61-80)",
                                            },
                                            {
                                                "value": "LOW",
                                                "label": "Low (81-100)",
                                            },
                                        ],
                                        value="ALL",
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.DatePickerInput(
                                        id="gis-date-range",
                                        label="Date Range",
                                        placeholder="Select date range",
                                        type="range",
                                        valueFormat="YYYY-MM-DD",
                                    ),
                                ],
                            ),
                        ],
                        gutter="md",
                    ),
                ],
            ),
            # ===== TAB INTERFACE =====
            dmc.Tabs(
                [
                    dmc.TabsList(
                        [
                            dmc.TabsTab(
                                "📍 Condition Map",
                                value="map",
                                leftSection=DashIconify(
                                    icon="mdi:map-marker", width=16
                                ),
                            ),
                            dmc.TabsTab(
                                "🔥 Hotspot Analysis",
                                value="hotspot",
                                leftSection=DashIconify(
                                    icon="mdi:fire", width=16
                                ),
                            ),
                            dmc.TabsTab(
                                "⚠️ Conflict Detection",
                                value="conflicts",
                                leftSection=DashIconify(
                                    icon="mdi:alert-circle", width=16
                                ),
                            ),
                            dmc.TabsTab(
                                "📊 Aggregation",
                                value="aggregation",
                                leftSection=DashIconify(
                                    icon="mdi:chart-bar", width=16
                                ),
                            ),
                            dmc.TabsTab(
                                "🎯 Clustering",
                                value="clustering",
                                leftSection=DashIconify(
                                    icon="mdi:target", width=16
                                ),
                            ),
                        ],
                        id="gis-tabs",
                        value="map",
                        grow=True,
                    ),
                    # ===== TAB 1: CONDITION MAP =====
                    dmc.TabsPanel(
                        value="map",
                        children=[
                            dmc.Space(h="md"),
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                radius="lg",
                                children=[
                                    dmc.Text(
                                        "Condition Map - Inspection Locations",
                                        fw=700,
                                        size="md",
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "Color indicates condition score (red=poor, green=good)",
                                        size="sm",
                                        c="gray",
                                        mb="md",
                                    ),
                                    dcc.Graph(
                                        id="viz-condition-map",
                                        figure=go.Figure().add_annotation(
                                            text="Loading...",
                                            showarrow=False,
                                            xref="paper",
                                            yref="paper",
                                            x=0.5,
                                            y=0.5,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # ===== TAB 2: HOTSPOT ANALYSIS =====
                    dmc.TabsPanel(
                        value="hotspot",
                        children=[
                            dmc.Space(h="md"),
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                radius="lg",
                                children=[
                                    dmc.Text(
                                        "Hotspot Analysis - Kernel Density Estimation",
                                        fw=700,
                                        size="md",
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "Shows concentration of critical locations (score ≤ 35)",
                                        size="sm",
                                        c="gray",
                                        mb="md",
                                    ),
                                    dcc.Graph(
                                        id="viz-hotspot-kde",
                                        figure=go.Figure().add_annotation(
                                            text="Loading...",
                                            showarrow=False,
                                            xref="paper",
                                            yref="paper",
                                            x=0.5,
                                            y=0.5,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # ===== TAB 3: CONFLICT DETECTION =====
                    dmc.TabsPanel(
                        value="conflicts",
                        children=[
                            dmc.Space(h="md"),
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                radius="lg",
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.Text(
                                                "Spatial Conflict Detection",
                                                fw=700,
                                                size="md",
                                            ),
                                            dmc.Badge(
                                                id="conflict-stats-text",
                                                children="No data",
                                                color="blue",
                                                variant="light",
                                            ),
                                        ],
                                        justify="space-between",
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "Identifies inspection locations overlapping with active permits",
                                        size="sm",
                                        c="gray",
                                        mb="md",
                                    ),
                                    dcc.Graph(
                                        id="viz-conflict-map",
                                        figure=go.Figure().add_annotation(
                                            text="Load permits data to detect conflicts",
                                            showarrow=False,
                                            xref="paper",
                                            yref="paper",
                                            x=0.5,
                                            y=0.5,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # ===== TAB 4: AGGREGATION =====
                    dmc.TabsPanel(
                        value="aggregation",
                        children=[
                            dmc.Space(h="md"),
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                radius="lg",
                                children=[
                                    dmc.Text(
                                        "Borough-Level Aggregation",
                                        fw=700,
                                        size="md",
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "Inspection count and average condition score by borough",
                                        size="sm",
                                        c="gray",
                                        mb="md",
                                    ),
                                    dcc.Graph(
                                        id="viz-borough-bar",
                                        figure=go.Figure().add_annotation(
                                            text="Loading...",
                                            showarrow=False,
                                            xref="paper",
                                            yref="paper",
                                            x=0.5,
                                            y=0.5,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # ===== TAB 5: CLUSTERING =====
                    dmc.TabsPanel(
                        value="clustering",
                        children=[
                            dmc.Space(h="md"),
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                radius="lg",
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.Text(
                                                "DBSCAN Spatial Clustering",
                                                fw=700,
                                                size="md",
                                            ),
                                            dmc.Badge(
                                                id="cluster-stats-text",
                                                children="No data",
                                                color="blue",
                                                variant="light",
                                            ),
                                        ],
                                        justify="space-between",
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "Density-based spatial clustering (DBSCAN) to identify patrol zones",
                                        size="sm",
                                        c="gray",
                                        mb="md",
                                    ),
                                    dcc.Graph(
                                        id="viz-dbscan-clusters",
                                        figure=go.Figure().add_annotation(
                                            text="Loading...",
                                            showarrow=False,
                                            xref="paper",
                                            yref="paper",
                                            x=0.5,
                                            y=0.5,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
                id="gis-main-tabs",
            ),
            # ===== FOOTER INFO =====
            dmc.Space(h="lg"),
            dmc.Paper(
                p="md",
                withBorder=True,
                radius="lg",
                bg="rgba(0,0,0,0.02)",
                children=[
                    dmc.Text(
                        "GIS Dashboard - Phase 1 Pilot",
                        fw=700,
                        size="sm",
                        c="gray",
                    ),
                    dmc.Text(
                        "Callback-based architecture with Redis session state and Plotly visualizations",
                        size="xs",
                        c="gray",
                    ),
                ],
            ),
            # Hidden div for data loader trigger
            html.Div(id="gis-data-loader", children=""),
        ],
    )
