"""
Dash Layout Components for Analytics Integration (Phase C-F)
Provides layout generators for:
- Phase C: Distribution Classification (Analytics View)
- Phase D: Anomaly Detection (Quality Dashboard)
- Phase E: Seasonal Decomposition (Temporal Patterns View)
- Phase F: Bootstrap CI (KPI Dashboard)
"""

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

# =============================================================================
# PHASE C: DISTRIBUTION CLASSIFICATION LAYOUT
# =============================================================================

def layout_phase_c_distribution():
    """
    Phase C: Distribution Classification Section.
    Analyzes numeric column distributions.

    Location: Analytics View, "Data Shapes" tab
    """
    return dmc.Stack([
        # Header
        dmc.Group([
            dmc.Group([
                DashIconify(icon="mdi:chart-box", width=24, color="#0033A0"),
                dmc.Stack([
                    dmc.Text("Distribution Classification", fw=700, size="lg"),
                    dmc.Text("Analyze the shape of numeric columns (normal, skewed, heavy-tailed, etc.)", size="sm", c="dimmed"),
                ], gap=0),
            ]),
            dmc.Badge("PHASE C", color="blue", variant="light"),
        ], justify="space-between", mb="lg"),

        # Controls
        dmc.Grid([
            dmc.GridCol(span={"base": 12, "md": 6}, children=[
                dmc.NumberInput(
                    id="distribution-column-limit",
                    value=8,
                    min=1,
                    max=20,
                    step=1,
                    description="Sorted by variance (highest first)",
                )
            ]),
            dmc.GridCol(span={"base": 12, "md": 6}, children=[
                dmc.Select(
                    id="distribution-dataset-selector",
                    value="inspection",
                    data=[
                        {"value": "inspection", "label": "Inspection Data"},
                        {"value": "violations", "label": "Violations"},
                        {"value": "ramp_progress", "label": "Ramp Progress"},
                    ],
                    description="Select dataset for analysis",
                )
            ]),
        ], gutter="md", mb="md"),

        # Chart Area
        dmc.Paper(
            withBorder=True,
            p="md",
            radius="lg",
            shadow="sm",
            children=[
                html.Div(
                    id="distribution-chart-container",
                    children=[
                        dmc.Skeleton(height=300, circle=False, mb="xl"),
                        dmc.Skeleton(height=300, circle=False, mb="xl"),
                    ]
                ),
            ]
        ),

        # Narrative Panel
        dmc.Accordion([
            dmc.AccordionItem(
                children=[
                    dmc.Text(
                        id="distribution-narrative",
                        children="Load a dataset to begin analysis...",
                        size="sm",
                        style={"lineHeight": "1.6"}
                    )
                ],
                value="narrative",
            ),
        ], variant="contained", mb="lg"),

        # Metadata
        dmc.Group([
            dmc.Badge("Performance", size="sm", variant="dot"),
            dmc.Text("Cache TTL: 10 minutes | Latency target: <300ms", size="xs", c="dimmed"),
        ]),
    ], gap="md", p="md")

# =============================================================================
# PHASE D: ANOMALY DETECTION LAYOUT
# =============================================================================

def layout_phase_d_anomaly():
    """
    Phase D: Spatial Anomaly Detection Section.
    Detects outliers using IQR method.

    Location: Quality Dashboard, "Data Quality" expander
    """
    return dmc.Stack([
        # Header
        dmc.Group([
            dmc.Group([
                DashIconify(icon="mdi:alert-circle", width=24, color="#DC2626"),
                dmc.Stack([
                    dmc.Text("Spatial Anomaly Detection", fw=700, size="lg"),
                    dmc.Text("Identify outliers and spatial anomalies in the data", size="sm", c="dimmed"),
                ], gap=0),
            ]),
            dmc.Badge("PHASE D", color="red", variant="light"),
        ], justify="space-between", mb="lg"),

        # Controls
        dmc.Grid([
            dmc.GridCol(span={"base": 12, "sm": 6}, children=[
                dmc.Switch(
                    id="anomaly-detection-toggle",
                    description="Check to run IQR-based outlier analysis",
                    checked=True,
                )
            ]),
            dmc.GridCol(span={"base": 12, "sm": 6}, children=[
                dmc.Badge(
                    id="anomaly-count-badge",
                    children="0 anomalies",
                    color="gray",
                    size="lg",
                )
            ]),
        ], gutter="md", mb="md"),

        # Chart Area
        dmc.Paper(
            withBorder=True,
            p="md",
            radius="lg",
            shadow="sm",
            children=[
                html.Div(
                    id="anomaly-detection-chart",
                    children=[
                        dmc.Skeleton(height=350, circle=False, mb="md"),
                        dmc.Skeleton(height=200, circle=False),
                    ]
                ),
            ]
        ),

        # Narrative Panel
        dmc.Accordion([
            dmc.AccordionItem(
                children=[
                    dmc.Text(
                        id="anomaly-narrative",
                        children="No anomaly analysis yet. Enable and refresh.",
                        size="sm",
                        style={"lineHeight": "1.6"}
                    )
                ],
                value="narrative",
            ),
        ], variant="contained", mb="lg"),

        # Metadata
        dmc.Group([
            dmc.Badge("Performance", size="sm", variant="dot"),
            dmc.Text("Cache TTL: 5 minutes | Latency target: <400ms", size="xs", c="dimmed"),
        ]),
    ], gap="md", p="md")

# =============================================================================
# PHASE E: SEASONAL DECOMPOSITION LAYOUT
# =============================================================================

def layout_phase_e_decomposition():
    """
    Phase E: Time Series Decomposition Section.
    Splits time series into trend, seasonal, residual.

    Location: Labor View or new Temporal Patterns view
    """
    return dmc.Stack([
        # Header
        dmc.Group([
            dmc.Group([
                DashIconify(icon="mdi:chart-line", width=24, color="#10B981"),
                dmc.Stack([
                    dmc.Text("Seasonal Decomposition", fw=700, size="lg"),
                    dmc.Text("Decompose time series into trend, seasonal, and residual components", size="sm", c="dimmed"),
                ], gap=0),
            ]),
            dmc.Badge("PHASE E", color="green", variant="light"),
        ], justify="space-between", mb="lg"),

        # Controls
        dmc.Grid([
            dmc.GridCol(span={"base": 12, "sm": 6}, children=[
                dmc.Select(
                    id="decomposition-date-col",
                    placeholder="Select date column (e.g., created_date)",
                    data=[
                        {"value": "created_date", "label": "Created Date"},
                        {"value": "inspection_date", "label": "Inspection Date"},
                        {"value": "date", "label": "Date"},
                    ],
                    description="Temporal axis for decomposition",
                )
            ]),
            dmc.GridCol(span={"base": 12, "sm": 6}, children=[
                dmc.Select(
                    id="decomposition-value-col",
                    placeholder="Select numeric column to decompose",
                    data=[
                        {"value": "violation_count", "label": "Violation Count"},
                        {"value": "count", "label": "Count"},
                        {"value": "score", "label": "Score"},
                    ],
                    description="Numeric axis for analysis",
                )
            ]),
        ], gutter="md", mb="md"),

        # Chart Area
        dmc.Paper(
            withBorder=True,
            p="md",
            radius="lg",
            shadow="sm",
            children=[
                html.Div(
                    id="decomposition-chart-container",
                    children=[
                        dmc.Skeleton(height=600, circle=False, mb="md"),
                    ]
                ),
            ]
        ),

        # Narrative Panel
        dmc.Accordion([
            dmc.AccordionItem(
                children=[
                    dmc.Text(
                        id="decomposition-narrative",
                        children="Configure date and value columns to begin decomposition.",
                        size="sm",
                        style={"lineHeight": "1.6"}
                    )
                ],
                value="narrative",
            ),
        ], variant="contained", mb="lg"),

        # Metadata
        dmc.Group([
            dmc.Badge("Performance", size="sm", variant="dot"),
            dmc.Text("Cache TTL: 15 minutes | Latency target: <500ms | Window: 7-day moving average", size="xs", c="dimmed"),
        ]),
    ], gap="md", p="md")

# =============================================================================
# PHASE F: BOOTSTRAP CONFIDENCE INTERVALS LAYOUT
# =============================================================================

def layout_phase_f_bootstrap_ci():
    """
    Phase F: Bootstrap Confidence Intervals Section.
    Wraps KPI metrics with uncertainty quantification.

    Location: Executive Dashboard, KPI section
    """
    return dmc.Stack([
        # Header
        dmc.Group([
            dmc.Group([
                DashIconify(icon="mdi:gauge", width=24, color="#6366F1"),
                dmc.Stack([
                    dmc.Text("KPI Metrics with Confidence Intervals", fw=700, size="lg"),
                    dmc.Text("Monitor key metrics with statistical uncertainty quantification", size="sm", c="dimmed"),
                ], gap=0),
            ]),
            dmc.Badge("PHASE F", color="indigo", variant="light"),
        ], justify="space-between", mb="lg"),

        # Controls
        dmc.Grid([
            dmc.GridCol(span={"base": 12, "sm": 6}, children=[
                dmc.NumberInput(
                    id="kpi-bootstrap-samples",
                    value=10000,
                    min=1000,
                    max=50000,
                    step=1000,
                    description="Number of bootstrap iterations",
                )
            ]),
            dmc.GridCol(span={"base": 12, "sm": 6}, children=[
                dmc.Select(
                    id="kpi-confidence-level",
                    value="95",
                    data=[
                        {"value": "90", "label": "90%"},
                        {"value": "95", "label": "95%"},
                        {"value": "99", "label": "99%"},
                    ],
                    description="Statistical confidence for CI bands",
                )
            ]),
        ], gutter="md", mb="md"),

        # Refresh trigger (polling)
        dcc.Interval(
            id="kpi-refresh-interval",
            interval=30000,  # 30 seconds
            n_intervals=0,
        ),

        # KPI Grid
        dmc.Paper(
            withBorder=True,
            p="md",
            radius="lg",
            shadow="sm",
            children=[
                html.Div(
                    id="kpi-bootstrap-figures",
                    children=[
                        dmc.Skeleton(height=300, circle=False, mb="md"),
                        dmc.Skeleton(height=300, circle=False, mb="md"),
                        dmc.Skeleton(height=300, circle=False, mb="md"),
                        dmc.Skeleton(height=300, circle=False),
                    ]
                ),
            ]
        ),

        # Summary
        dmc.Accordion([
            dmc.AccordionItem(
                children=[
                    dmc.Text(
                        id="kpi-bootstrap-summary",
                        children="Bootstrap CI summarizes uncertainty in KPI estimates.",
                        size="sm",
                        style={"lineHeight": "1.6"}
                    )
                ],
                value="summary",
            ),
        ], variant="contained", mb="lg"),

        # Metadata
        dmc.Group([
            dmc.Badge("Performance", size="sm", variant="dot"),
            dmc.Text("Cache TTL: 10 minutes | Latency target: <300ms | Method: Non-parametric bootstrap", size="xs", c="dimmed"),
        ]),
    ], gap="md", p="md")

# =============================================================================
# PHASE B (EXISTING): MORAN'S I LAYOUT
# =============================================================================

def layout_phase_b_morans_i():
    """
    Phase B: Moran's I Spatial Autocorrelation Section.
    Detects spatial clustering.

    Location: GIS Dashboard, "Spatial Patterns" tab
    """
    return dmc.Stack([
        # Header
        dmc.Group([
            dmc.Group([
                DashIconify(icon="mdi:map-marker", width=24, color="#7C3AED"),
                dmc.Stack([
                    dmc.Text("Moran's I Spatial Autocorrelation", fw=700, size="lg"),
                    dmc.Text("Detect spatial clustering vs. dispersion patterns", size="sm", c="dimmed"),
                ], gap=0),
            ]),
            dmc.Badge("PHASE B", color="violet", variant="light"),
        ], justify="space-between", mb="lg"),

        # Controls
        dmc.Select(
            id="morans-i-column-select",
            placeholder="Auto-select first numeric column",
            data=[
                {"value": "violation_count", "label": "Violation Count"},
                {"value": "score", "label": "Score"},
                {"value": "count", "label": "Count"},
            ],
        ),

        # Chart
        dmc.Paper(
            withBorder=True,
            p="md",
            radius="lg",
            shadow="sm",
            children=[
                dcc.Graph(id="morans-i-gauge", config={'displayModeBar': True}),
            ]
        ),

        # Narrative
        dmc.Accordion([
            dmc.AccordionItem(
                children=[
                    dmc.Text(
                        id="morans-i-narrative",
                        children="Moran's I indicates spatial autocorrelation.",
                        size="sm",
                        style={"lineHeight": "1.6"}
                    )
                ],
                value="narrative",
            ),
        ], variant="contained", mb="lg"),

        # Metadata
        dmc.Group([
            dmc.Badge("Performance", size="sm", variant="dot"),
            dmc.Text("Cache TTL: 10 minutes | Latency target: <200ms | Method: K-nearest neighbors weights", size="xs", c="dimmed"),
        ]),
    ], gap="md", p="md")

# =============================================================================
# UNIVERSAL COMPONENTS
# =============================================================================

def render_analytics_integration_tabs() -> dmc.Tabs:
    """
    Render all Phase C-F analytics integration tabs.
    Used in Analytics View or dedicated Integration Dashboard.
    """
    return dmc.Tabs([
        dmc.TabsList([
            dmc.TabsTab("Distribution (C)", value="phase-c", leftSection=DashIconify(icon="mdi:chart-box")),
            dmc.TabsTab("Anomalies (D)", value="phase-d", leftSection=DashIconify(icon="mdi:alert-circle")),
            dmc.TabsTab("Decomposition (E)", value="phase-e", leftSection=DashIconify(icon="mdi:chart-line")),
            dmc.TabsTab("KPI CI (F)", value="phase-f", leftSection=DashIconify(icon="mdi:gauge")),
            dmc.TabsTab("Spatial (B)", value="phase-b", leftSection=DashIconify(icon="mdi:map-marker")),
        ]),
        dmc.TabsPanel(value="phase-c", children=[layout_phase_c_distribution()]),
        dmc.TabsPanel(value="phase-d", children=[layout_phase_d_anomaly()]),
        dmc.TabsPanel(value="phase-e", children=[layout_phase_e_decomposition()]),
        dmc.TabsPanel(value="phase-f", children=[layout_phase_f_bootstrap_ci()]),
        dmc.TabsPanel(value="phase-b", children=[layout_phase_b_morans_i()]),
    ], value="phase-c", variant="pills", radius="md")

# Hidden store for global filter synchronization
def render_analytics_stores() -> html.Div:
    """
    Render hidden stores for filter synchronization.
    Used by all analytics integration callbacks.
    """
    return html.Div([
        dcc.Store(id="store-global-filters", data={}),
        dcc.Store(id="analytics-refresh-trigger", data={}),
    ], style={"display": "none"})
