import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from app.components.filter_system import render_filter_bar
from app.components.metric_cards import render_metric_dashboard

# ==========================================
# --- ELITE ASSET WRAPPER ---
# ==========================================


def visualization_asset(chart_id, title, description, summary, tier="1"):
    """
    Creates a compartmentalized, multi-tab analytical asset.
    Includes secondary and tertiary nested structures for:
    Visual | Insights | Data | Export
    """
    return dmc.Paper(
        withBorder=True,
        p="md",
        radius="lg",
        shadow="sm",
        mb="xl",
        className=f"viz-tier-{tier} viz-container",
        children=[
            dmc.Group(
                [
                    dmc.Group(
                        [
                            DashIconify(icon="mdi:analytics", width=25, color="#0033A0"),
                            dmc.Text(title, fw=900, size="lg", c="black"),
                        ]
                    ),
                    dmc.Badge("PRODUCTION READY", color="blue", variant="light"),
                ],
                justify="space-between",
                mb="xs",
            ),
            dmc.Text(description, size="sm", c="gray", mb="md"),
            dmc.Tabs(
                [
                    dmc.TabsList(
                        [
                            dmc.TabsTab(
                                "Visual",
                                value="visual",
                                leftSection=DashIconify(icon="mdi:chart-bar"),
                            ),
                            dmc.TabsTab(
                                "Insights",
                                value="insights",
                                leftSection=DashIconify(icon="mdi:lightbulb-on"),
                            ),
                            dmc.TabsTab(
                                "Raw Data", value="data", leftSection=DashIconify(icon="mdi:table")
                            ),
                            dmc.TabsTab(
                                "Export Powerhouse",
                                value="export",
                                leftSection=DashIconify(icon="mdi:export"),
                            ),
                        ],
                        id={"type": "asset-tabs", "index": chart_id},
                    ),
                    # --- Tab: Visual ---
                    dmc.TabsPanel(
                        value="visual",
                        children=[
                            dmc.Stack(
                                [
                                    dmc.Group(
                                        [
                                            dmc.Switch(
                                                label="Show Target Line", size="xs", checked=True
                                            ),
                                            dmc.Switch(label="Enable Log Scale", size="xs"),
                                        ],
                                        gap="lg",
                                        mt="sm",
                                    ),
                                    dmc.LoadingOverlay(
                                        visible=False,
                                        loaderProps={"type": "bars", "color": "blue"},
                                        children=dcc.Graph(
                                            id={"type": "visualization-graph", "index": chart_id},
                                            config={"displayModeBar": True},
                                            style={"minHeight": "420px"},
                                        ),
                                    ),
                                    dmc.Text(
                                        "Source: NYC Open Data · Standard Error: ±1.2%",
                                        size="xs",
                                        c="gray",
                                        ta="right",
                                    ),
                                ]
                            )
                        ],
                    ),
                    # --- Tab: Insights ---
                    dmc.TabsPanel(
                        value="insights",
                        children=[
                            dmc.ScrollArea(
                                h=300,
                                children=[
                                    dmc.Stack(
                                        p="md",
                                        children=[
                                            dmc.Group(
                                                [
                                                    dmc.Text(
                                                        "ANALYTICAL INTERPRETATION",
                                                        fw=700,
                                                        size="sm",
                                                    ),
                                                    dmc.Group(
                                                        [
                                                            dmc.SegmentedControl(
                                                                id={
                                                                    "type": "insight-mode",
                                                                    "index": chart_id,
                                                                },
                                                                value="static",
                                                                data=[
                                                                    {
                                                                        "value": "static",
                                                                        "label": "Static (Semantic)",
                                                                    },
                                                                    {
                                                                        "value": "dynamic",
                                                                        "label": "Dynamic (Agential)",
                                                                    },
                                                                ],
                                                                size="xs",
                                                            ),
                                                            dmc.SegmentedControl(
                                                                id={
                                                                    "type": "insight-verbosity",
                                                                    "index": chart_id,
                                                                },
                                                                value="verbose",
                                                                data=[
                                                                    {
                                                                        "value": "concise",
                                                                        "label": "Concise",
                                                                    },
                                                                    {
                                                                        "value": "verbose",
                                                                        "label": "Verbose",
                                                                    },
                                                                ],
                                                                size="xs",
                                                            ),
                                                            dmc.SegmentedControl(
                                                                id={
                                                                    "type": "insight-reading-level",
                                                                    "index": chart_id,
                                                                },
                                                                value="executive",
                                                                data=[
                                                                    {
                                                                        "value": "executive",
                                                                        "label": "Executive",
                                                                    },
                                                                    {
                                                                        "value": "standard",
                                                                        "label": "Standard (8th Grade)",
                                                                    },
                                                                ],
                                                                size="xs",
                                                            ),
                                                        ],
                                                        gap="xs",
                                                    ),
                                                ],
                                                justify="space-between",
                                            ),
                                            dmc.Divider(),
                                            html.Div(
                                                id={"type": "ai-insight-text", "index": chart_id},
                                                children=[
                                                    dmc.Text(
                                                        summary,
                                                        size="sm",
                                                        style={"lineHeight": "1.6"},
                                                    )
                                                ],
                                            ),
                                            dmc.Divider(),
                                            dmc.Text(
                                                "STATISTICAL FINDINGS (THE FOUR MOMENTS)",
                                                fw=700,
                                                size="sm",
                                            ),
                                            dmc.List(
                                                id={
                                                    "type": "statistical-moments",
                                                    "index": chart_id,
                                                },
                                                children=[
                                                    dmc.ListItem("Mean: PENDING"),
                                                    dmc.ListItem("Variance: PENDING"),
                                                    dmc.ListItem("Skewness: PENDING"),
                                                    dmc.ListItem("Kurtosis: PENDING"),
                                                ],
                                                size="sm",
                                            ),
                                        ],
                                    )
                                ],
                            )
                        ],
                    ),
                    # --- Tab: Raw Data ---
                    dmc.TabsPanel(
                        value="data",
                        children=[
                            dmc.Paper(
                                mt="md",
                                withBorder=True,
                                p="xs",
                                children=[
                                    dmc.Text(
                                        "Live data grid loading...",
                                        size="xs",
                                        c="gray",
                                        id={"type": "grid-status", "index": chart_id},
                                    ),
                                    html.Div(
                                        id={"type": "grid-container", "index": chart_id},
                                        style={"maxHeight": "300px", "overflow": "auto"},
                                    ),
                                ],
                            )
                        ],
                    ),
                    # --- Tab: Export ---
                    dmc.TabsPanel(
                        value="export",
                        children=[
                            dmc.SimpleGrid(
                                cols=3,
                                spacing="sm",
                                mt="md",
                                children=[
                                    dmc.Button(
                                        "CSV / Excel",
                                        id={"type": "btn-export", "index": f"csv-{chart_id}"},
                                        variant="outline",
                                        leftSection=DashIconify(icon="mdi:file-excel"),
                                    ),
                                    dmc.Button(
                                        "PDF Report",
                                        id={"type": "btn-export", "index": f"pdf-{chart_id}"},
                                        variant="outline",
                                        leftSection=DashIconify(icon="mdi:file-pdf-box"),
                                    ),
                                    dmc.Button(
                                        "Power BI Link",
                                        id={"type": "btn-export", "index": f"pbi-{chart_id}"},
                                        variant="outline",
                                        leftSection=DashIconify(icon="mdi:microsoft-power-bi"),
                                    ),
                                    dmc.Button(
                                        "PNG Image",
                                        id={"type": "btn-export", "index": f"png-{chart_id}"},
                                        variant="outline",
                                        leftSection=DashIconify(icon="mdi:file-image"),
                                    ),
                                    dmc.Button(
                                        "JPEG Image",
                                        id={"type": "btn-export", "index": f"jpg-{chart_id}"},
                                        variant="outline",
                                        leftSection=DashIconify(icon="mdi:file-image-outline"),
                                    ),
                                    dmc.Button(
                                        "Markdown",
                                        id={"type": "btn-export", "index": f"md-{chart_id}"},
                                        variant="outline",
                                        leftSection=DashIconify(icon="mdi:markdown"),
                                    ),
                                    dmc.Button(
                                        "Python Snippet",
                                        id={"type": "btn-export", "index": f"py-{chart_id}"},
                                        variant="light",
                                        color="indigo",
                                        leftSection=DashIconify(icon="mdi:language-python"),
                                    ),
                                    dmc.Button(
                                        "R Script",
                                        id={"type": "btn-export", "index": f"r-{chart_id}"},
                                        variant="light",
                                        color="blue",
                                        leftSection=DashIconify(icon="mdi:language-r"),
                                    ),
                                    dmc.Button(
                                        "Copy to Clipboard",
                                        id={"type": "btn-copy", "index": chart_id},
                                        variant="filled",
                                        color="dark",
                                        leftSection=DashIconify(icon="mdi:clipboard-text"),
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
                value="visual",
                variant="pills",
                radius="md",
                mt="md",
            ),
        ],
    )


# ==========================================
# --- LAYOUTS ---
# ==========================================


def render_header():
    return dmc.AppShellHeader(
        **{"aria-label": "NYC DOT Socrata Toolkit Header"},
        children=[
            dmc.Stack(
                [
                    dmc.Group(
                        children=[
                            dmc.Group(
                                [
                                    dmc.Text(
                                        "NYC DOT SOCRATA TOOLKIT v8.0-ALPHA",
                                        size="xl",
                                        fw=900,
                                        c="black",
                                        id="toolkit-brand",
                                    ),
                                    # Mantine v7 computes --badge-color as a literal hex at render time
                                    # (not a CSS var), so JS token overrides don't reach badge text.
                                    # Explicit inline style forces WCAG-safe colors directly.
                                    # orange #b85500 on white = 4.84:1 ✓; cyan #0b7285 on white = 5.15:1 ✓
                                    dmc.Badge("TURBO-STREAM", color="orange", variant="outline",
                                              style={"color": "#b85500"}),
                                    dmc.Badge("FASTAPI ENABLED", color="cyan", variant="outline",
                                              style={"color": "#0b7285"}),
                                ]
                            ),
                            # Global Command Bar
                            dmc.Group(
                                [
                                    dmc.Select(
                                        id="global-tier-filter",
                                        placeholder="Relevance Tier",
                                        data=[
                                            {"value": "ALL", "label": "ALL TIERS"},
                                            {"value": "1", "label": "Tier 1: Core SIM"},
                                            {"value": "2", "label": "Tier 2: SIM-Adjacent"},
                                        ],
                                        value="ALL",
                                        w=160,
                                        size="xs",
                                    ),
                                    dmc.Select(
                                        id="global-boro-filter",
                                        placeholder="Borough",
                                        data=[
                                            "ALL",
                                            "MANHATTAN",
                                            "BROOKLYN",
                                            "QUEENS",
                                            "BRONX",
                                            "STATEN ISLAND",
                                        ],
                                        value="ALL",
                                        w=140,
                                        size="xs",
                                    ),
                                    dmc.ActionIcon(
                                        DashIconify(icon="mdi:theme-light-dark"),
                                        variant="outline",
                                        id="btn-toggle-theme",
                                        color="dark",
                                        size="sm",
                                        **{"aria-label": "Toggle light/dark theme"},
                                    ),
                                    dmc.Button(
                                        "JUPYTER",
                                        id="btn-jupyter-export",
                                        variant="light",
                                        color="indigo",
                                        size="xs",
                                        # WCAG AA: indigo-9 on light-indigo bg ≈ 15:1
                                        c="#1c2047",
                                        leftSection=DashIconify(icon="mdi:notebook"),
                                    ),
                                ],
                                gap="xs",
                            ),
                        ],
                        justify="space-between",
                        px="md",
                        pt="xs",
                    ),
                ],
                gap=0,
            )
        ],
        style={"borderBottom": "3px solid #000000", "height": "90px"},
    )


def render_sidebar():
    return dmc.AppShellNavbar(
        **{"aria-label": "Mission Control Navigation"},
        children=[
            dmc.ScrollArea(
                children=[
                    dmc.Stack(
                        p="md",
                        children=[
                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="mdi:city-variant-outline", width=30, color="black"
                                    ),
                                    dmc.Text("NYC DOT Analytics", size="lg", fw=800, c="black"),
                                ]
                            ),
                            dmc.Divider(),
                            dmc.NavLink(
                                id="nav-dash",
                                label="Dashboard",
                                leftSection=DashIconify(icon="mdi:view-dashboard"),
                                href="/",
                            ),
                            dmc.NavLink(
                                id="nav-const",
                                label="Construction Planner",
                                leftSection=DashIconify(icon="mdi:crane"),
                                href="/const",
                            ),
                            dmc.NavLink(
                                id="nav-labor",
                                label="Labor & Lifecycle",
                                leftSection=DashIconify(icon="mdi:account-hard-hat"),
                                href="/labor",
                            ),
                            dmc.NavLink(
                                id="nav-reports",
                                label="Reports",
                                leftSection=DashIconify(icon="mdi:file-chart"),
                                href="/reports",
                            ),
                            dmc.NavLink(
                                id="nav-stats",
                                label="Statistics",
                                leftSection=DashIconify(icon="mdi:math-log"),
                                href="/stats",
                            ),
                            dmc.NavLink(
                                id="nav-geo",
                                label="GIS & Maps",
                                leftSection=DashIconify(icon="mdi:map-marker-radius"),
                                href="/geo",
                            ),
                            dmc.NavLink(
                                id="nav-eng",
                                label="Engineering",
                                leftSection=DashIconify(icon="mdi:hard-hat"),
                                href="/eng",
                            ),
                            dmc.NavLink(
                                id="nav-sql",
                                label="SQL Studio",
                                leftSection=DashIconify(icon="mdi:database-search"),
                                href="/sql",
                            ),
                            dmc.NavLink(
                                id="nav-nlp",
                                label="Natural Language Query",
                                leftSection=DashIconify(icon="mdi:robot-happy"),
                                href="/nlp",
                            ),
                            dmc.NavLink(
                                id="nav-tutorials",
                                label="Tutorials",
                                leftSection=DashIconify(icon="mdi:book-open-page-variant"),
                                href="/tutorials",
                            ),
                            dmc.NavLink(
                                id="nav-settings",
                                label="Settings",
                                leftSection=DashIconify(icon="mdi:cog"),
                                href="/settings",
                            ),
                            dmc.NavLink(
                                id="nav-toolbox",
                                label="Toolbox",
                                leftSection=DashIconify(icon="mdi:toolbox-outline"),
                                href="/toolbox",
                            ),
                            dmc.NavLink(
                                id="nav-copilot",
                                label="AI Assistant",
                                leftSection=DashIconify(icon="mdi:robot-happy"),
                                href="/copilot",
                            ),
                            dmc.Divider(label="Worker Queue", labelPosition="center", mt="md"),
                            dmc.Paper(
                                p="sm",
                                withBorder=True,
                                bg="rgba(0,0,0,0.02)",
                                children=[
                                    dmc.Group(
                                        [
                                            dmc.Text("JID SCRAPER", size="xs", fw=700),
                                            dmc.Badge(
                                                "IDLE",
                                                size="xs",
                                                color="gray",
                                                id="worker-jid-status",
                                            ),
                                        ],
                                        justify="space-between",
                                    ),
                                    dmc.Progress(
                                        value=0,
                                        size="xs",
                                        mt="xs",
                                        animated=True,
                                        id="worker-jid-progress",
                                    ),
                                    dmc.Group(
                                        [
                                            dmc.Text("SODA INGEST", size="xs", fw=700, mt="sm"),
                                            html.Div(
                                                className="status-glow",
                                                style={
                                                    "width": "8px",
                                                    "height": "8px",
                                                    "borderRadius": "50%",
                                                    "backgroundColor": "#10B981",
                                                },
                                            ),
                                        ],
                                        justify="space-between",
                                    ),
                                ],
                            ),
                            dmc.Divider(label="Forensic Audit", labelPosition="center", mt="md"),
                            dmc.ScrollArea(
                                h=100,
                                children=[
                                    html.Div(id="audit-log-terminal", style={"padding": "4px"})
                                ],
                            ),
                            dmc.Divider(label="Engine Status", labelPosition="center", mt="md"),
                            dmc.ScrollArea(
                                h=100,
                                children=[
                                    html.Div(
                                        id="debug-terminal",
                                        style={
                                            "padding": "4px",
                                            "fontFamily": "monospace",
                                            "fontSize": "10px",
                                        },
                                    )
                                ],
                            ),
                        ],
                    )
                ]
            )
        ],
        style={"borderRight": "1px solid #E2E8F0"},
    )


def create_metric_card(label, value, color="black", delta=None):
    delta_html = (
        dmc.Text(delta, size="xs", c="green" if "+" in str(delta) else "red") if delta else None
    )
    return dmc.Paper(
        children=[
            dmc.Text(label, size="xs", fw=700, c="gray"),
            dmc.Group(
                [dmc.Text(value, size="xl", fw=900, c=color), delta_html],
                justify="space-between",
                align="flex-end",
            ),
        ],
        withBorder=True,
        p="md",
        radius="md",
        bg="#FFFFFF",
        shadow="sm",
    )


# --- VIEW: DASHBOARD ---
def layout_dashboard():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Group(
                [
                    dmc.Text("EXECUTIVE TELEMETRICS", fw=900, size="xl", c="black"),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Export Complete PDF",
                                id="btn-global-export-pdf",
                                variant="filled",
                                # WCAG AA: use darker red so white text ≈ 6.4:1
                                style={"backgroundColor": "#c0392b", "border": "none"},
                                leftSection=DashIconify(icon="mdi:file-pdf-box"),
                            ),
                            dmc.Button(
                                "Export Complete Excel",
                                id="btn-global-export-excel",
                                variant="outline",
                                color="green",
                                # WCAG AA: dark green on white ≈ 9.4:1
                                c="#155724",
                                leftSection=DashIconify(icon="mdi:file-excel"),
                            ),
                            dmc.Button(
                                "Export Complete PPTX",
                                id="btn-global-export-pptx",
                                variant="outline",
                                color="orange",
                                # WCAG AA: dark amber on white ≈ 5.8:1
                                c="#7d4e00",
                                leftSection=DashIconify(icon="mdi:file-powerpoint"),
                            ),
                        ],
                        gap="sm"
                    ),
                ],
                justify="space-between",
                mb="lg"
            ),
            render_filter_bar(),
            render_metric_dashboard(),
            dmc.Space(h="xl"),
            visualization_asset(
                "viz-velocity",
                "Administrative Velocity (Ensemble Consensus)",
                "Item 16: Consensus mean of Prophet, ARIMA, and Linear Trend forecasting.",
                "Ensemble forecast of inspection/processing throughput across the selected window.",
            ),
            visualization_asset(
                "viz-inspections",
                "Inspections by Borough",
                "Real SIM inspection volume aggregated per borough from the warehouse.",
                "Borough-level distribution of sidewalk inspection activity.",
            ),
        ],
    )


# --- VIEW: CONSTRUCTION ---
def layout_construction():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("CONSTRUCTION PLANNER & WORKFLOW", fw=900, size="xl", mb="lg", c="black"),
            dmc.Paper(
                withBorder=True,
                p="lg",
                radius="md",
                children=[
                    dmc.Text("PRIORITIZED WORK ORDERS", fw=700, mb="md"),
                    dmc.Table(id="table-const-list"),
                    dmc.Button(
                        "GENERATE OFFICIAL LIST", fullWidth=True, mt="xl", color="blue", size="lg"
                    ),
                ],
            ),
            dmc.Space(h="xl"),
            visualization_asset(
                "viz-weekly-heat",
                "Weekly Construction Schedule Density",
                "Spatio-temporal analysis of scheduled work.",
                "Manhattan exhibits 40% higher work density on Tuesday/Wednesday cycles.",
            ),
        ],
    )


# --- VIEW: LABOR ---
def layout_labor():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("LABOR & PERSONNEL SERVICES ANALYTICS", fw=900, size="xl", mb="lg", c="black"),
            visualization_asset(
                "viz-ps-burn",
                "PS Budget Code Burn Rate",
                "Financial tracking of personnel services.",
                "Budget code SIM-101 is burning at 92% of its quarterly target.",
            ),
            visualization_asset(
                "viz-lifecycle",
                "Complaint-to-Repair Lifecycle Funnel",
                "Visualizing friction points in the pipeline.",
                "Violation-to-Notice phase accounts for 40% of latency.",
            ),
            visualization_asset(
                "viz-contractor-radar",
                "Contractor Performance Radar",
                "Multi-metric performance scorecards.",
                "Contractor A leads in productivity, Contractor B leads in quality.",
            ),
        ],
    )


# --- VIEW: REPORTS ---
def layout_reports():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("AUTOMATED REPORTING HUB", fw=900, size="xl", mb="lg", c="black"),
            dmc.SimpleGrid(
                cols=3,
                spacing="lg",
                children=[
                    dmc.Card(
                        withBorder=True,
                        p="lg",
                        children=[
                            dmc.Text("Contract Status", fw=700),
                            dmc.Button("Generate PDF", mt="md"),
                        ],
                    ),
                    dmc.Card(
                        withBorder=True,
                        p="lg",
                        children=[
                            dmc.Text("Program Metric", fw=700),
                            dmc.Button("Generate MD", mt="md"),
                        ],
                    ),
                    dmc.Card(
                        withBorder=True,
                        p="lg",
                        children=[
                            dmc.Text("Inquiry Response", fw=700),
                            dmc.Button("Draft Template", mt="md"),
                        ],
                    ),
                ],
            ),
            dmc.Space(h="xl"),
            visualization_asset(
                "viz-hiqa-outcomes",
                "HIQA Inspection Outcomes",
                "Quality audit pass/fail metrics.",
                "92% Pass rate in last 30 days.",
            ),
            visualization_asset(
                "viz-hiqa-trends",
                "Weekly HIQA Volume",
                "Workload trend analysis.",
                "Surge detected in Staten Island inspections.",
            ),
        ],
    )


# --- VIEW: STATS ---
def layout_stats():
    # Real Phase B–F analytics (Moran's I, distribution, anomalies, decomposition,
    # bootstrap CI) computed by the pipeline and rendered from app_queries.v_phase_*.
    from app.dash_layouts_analytics_integration import render_analytics_integration_tabs
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("EMPIRICAL STATISTICS & DATA QUALITY", fw=900, size="xl", mb="lg", c="black"),
            dmc.Paper(
                withBorder=True, radius="lg", p="md", mb="xl", shadow="xs",
                children=[
                    dmc.Text("Advanced Statistical Analytics", fw=800, size="lg", mb="sm", c="black"),
                    render_analytics_integration_tabs(),
                ],
            ),
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    visualization_asset(
                        "viz-feature-importance",
                        "Feature Importance Ranking",
                        "Item 23: RandomForest ranking of variance drivers.",
                        "Top drivers: LotArea and Seasonality.",
                    ),
                    visualization_asset(
                        "moment_history",
                        "Statistical Moment History",
                        "Item 29: Tracking Skew & Kurtosis shifts.",
                        "Identifying significant distribution surges.",
                    ),
                ],
            ),
            dmc.SimpleGrid(
                cols=3,
                spacing="lg",
                children=[
                    visualization_asset(
                        "viz-freshness",
                        "SLA Freshness Matrix",
                        "Dataset age tracking.",
                        "95% SLA compliance.",
                    ),
                    visualization_asset(
                        "viz-quality-box",
                        "Data Quality Distribution",
                        "Statistical health metrics.",
                        "Median health 92/100.",
                    ),
                    visualization_asset(
                        "viz-anomalies",
                        "Daily Anomaly Flux",
                        "Outlier detection.",
                        "3 Outliers flagged in Step Streets.",
                    ),
                ],
            ),
            visualization_asset(
                "manifold_3d",
                "3D Manifold Visualizer (PCA)",
                "High-dimensional data reduction.",
                "Identifying latent clusters in property info.",
            ),
        ],
    )


# --- VIEW: GIS ---
def layout_gis():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Group(
                [
                    dmc.Text("GIS & SPATIAL INTELLIGENCE", fw=900, size="xl", c="black"),
                    dmc.Group(
                        [
                            dmc.Button(
                                "DRAW GEOFENCE",
                                id="btn-draw-polygon",
                                leftSection=DashIconify(icon="mdi:vector-polygon"),
                                variant="outline",
                                color="dark",
                            ),
                            dmc.Switch(
                                label="3D Buildings",
                                id="toggle-3d-buildings",
                                color="blue",
                                size="sm",
                                checked=False,
                            ),
                            dmc.Switch(
                                label="Isochrone Overlay",
                                id="toggle-isochrones",
                                color="indigo",
                                size="sm",
                                checked=False,
                            ),
                        ],
                        gap="xl",
                    ),
                ],
                justify="space-between",
                mb="lg",
            ),
            dmc.Grid(
                [
                    dmc.GridCol(
                        span=9,
                        children=[
                            visualization_asset(
                                "viz-ramp-heatmap",
                                "3D Pedestrian Ramp Density",
                                "Accessibility infrastructure clusters.",
                                "Brooklyn high-density ADA ramp hotspots.",
                                tier="2",
                            )
                        ],
                    ),
                    dmc.GridCol(
                        span=3,
                        children=[
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                children=[
                                    dmc.Text("STREET VIEW PREVIEW", fw=700, mb="sm"),
                                    dmc.Text(
                                        "Item 32: Split-pane Physical Audit",
                                        size="xs",
                                        c="gray",
                                        mb="md",
                                    ),
                                    dmc.Paper(
                                        h=400,
                                        bg="rgba(0,0,0,0.05)",
                                        children=[
                                            dmc.Center(
                                                dmc.Text(
                                                    "Street View Container (Edge Security Bypass Mode)",
                                                    size="xs",
                                                    c="gray",
                                                )
                                            )
                                        ],
                                        style={"borderRadius": "8px"},
                                    ),
                                ],
                            )
                        ],
                    ),
                ]
            ),
            visualization_asset(
                "isochrone",
                "Pedestrian Catchment Isochrones",
                "Item 33: Walkability distance analysis for accessibility.",
                "5/10/15 minute pedestrian accessibility envelopes.",
                tier="2",
            ),
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    visualization_asset(
                        "viz-curb-metal",
                        "Protruding Curb Metal",
                        "Specific steel defect tracking.",
                        "High severity clusters in Lower Manhattan.",
                        tier="2",
                    ),
                    visualization_asset(
                        "viz-planimetric",
                        "Planimetric Sidewalk Density",
                        "Physical area distribution.",
                        "Normative area size peaks at 400 sqft.",
                        tier="2",
                    ),
                ],
            ),
        ],
    )


# --- VIEW: ENGINEERING ---
def layout_engineering():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text(
                "CIVIL ENGINEERING & STRUCTURAL MANDATE", fw=900, size="xl", mb="lg", c="black"
            ),
            dmc.Grid(
                [
                    dmc.GridCol(
                        span=7,
                        children=[
                            visualization_asset(
                                "viz-pavement-decay",
                                "Predictive Pavement Decay",
                                "Item 27: Regression model for IRI progression.",
                                "Forecasted IRI breach in Year 12.",
                            )
                        ],
                    ),
                    dmc.GridCol(
                        span=5,
                        children=[
                            dmc.Paper(
                                p="lg",
                                withBorder=True,
                                children=[
                                    dmc.Text("MARKOV TRANSITION EDITOR", fw=700, mb="sm"),
                                    dmc.Table(
                                        id="markov-transition-matrix",
                                        data={
                                            "head": [
                                                "State",
                                                "Excellent",
                                                "Good",
                                                "Fair",
                                                "Poor",
                                                "Failed",
                                            ],
                                            "body": [
                                                [
                                                    "Excellent",
                                                    "0.85",
                                                    "0.15",
                                                    "0.00",
                                                    "0.00",
                                                    "0.00",
                                                ],
                                                ["Good", "0.00", "0.80", "0.20", "0.00", "0.00"],
                                                ["Fair", "0.00", "0.00", "0.75", "0.25", "0.00"],
                                                ["Poor", "0.00", "0.00", "0.00", "0.60", "0.40"],
                                                ["Failed", "0.00", "0.00", "0.00", "0.00", "1.00"],
                                            ],
                                        },
                                    ),
                                    dmc.Button(
                                        "RE-SIMULATE ASSET LIFE",
                                        fullWidth=True,
                                        mt="md",
                                        color="dark",
                                        variant="outline",
                                    ),
                                ],
                            )
                        ],
                    ),
                ]
            ),
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    visualization_asset(
                        "equity",
                        "Socio-Economic Equity Multipliers",
                        "Item 68: Prioritization boost map.",
                        "Areas with 2.0x equity weight application.",
                        tier="2",
                    ),
                    visualization_asset(
                        "budget_mc",
                        "Monte Carlo Budget Risk",
                        "Item 19/62: Probabilistic project cost outcomes.",
                        "95% confidence interval for construction variance.",
                    ),
                ],
            ),
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    visualization_asset(
                        "viz-stipulations",
                        "Permit Stipulation Radar",
                        "Work-permit compliance metrics.",
                        "Traffic compliance at 88%.",
                    ),
                    visualization_asset(
                        "viz-resurfacing-gantt",
                        "Street Resurfacing Timeline",
                        "Project management Gantt view.",
                        "In-house paving schedule is 95% on-target.",
                    ),
                ],
            ),
        ],
    )


def layout_sql_tools():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("SQL STUDIO & DATA WORKBENCH", fw=900, size="xl", mb="lg", c="black"),
            visualization_asset(
                "viz-mappluto-far",
                "MapPLUTO Built FAR Analysis",
                "Property density vs condition.",
                "Zoning impact study results.",
            ),
            dmc.Paper(
                withBorder=True,
                p="lg",
                children=[
                    dmc.Text("DuckDB SQL QUERY EXECUTOR", fw=700, mb="sm"),
                    dmc.Text(
                        "Execute SQL against the local 5.7 GB warehouse (118 raw tables). "
                        "Use schema prefix: SELECT * FROM raw.inspection LIMIT 100",
                        size="sm", c="dimmed", mb="sm",
                    ),
                    dmc.Textarea(
                        id="sql-query-input",
                        label="SQL Query",
                        placeholder="SELECT * FROM raw.inspection LIMIT 100",
                        mb="md",
                        minRows=4,
                        autosize=True,
                    ),
                    dmc.Group([
                        dmc.Button("▶ Run Query", id="btn-run-sql", color="blue"),
                        dmc.Button("Clear", id="btn-clear-sql", variant="outline", color="gray"),
                    ], mb="md"),
                    dmc.LoadingOverlay(
                        id="sql-loading-overlay",
                        visible=False,
                        children=html.Div(id="sql-results-output"),
                    ),
                ],
            ),
        ],
    )


def layout_nlp():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("NLP & CITIZEN SENTIMENT ANALYTICS", fw=900, size="xl", mb="lg", c="black"),
            dmc.Paper(
                withBorder=True,
                p="lg",
                mb="lg",
                children=[
                    dmc.Text("VOICE NOTE TRANSCRIPTION (ITEM 50)", fw=700, mb="sm"),
                    dcc.Upload(
                        id="audio-upload",
                        children=dmc.Button(
                            "Select Audio File (.wav/mp3)", variant="outline", w=300,
                            style={"color": "#1864ab"},  # WCAG: 5.65:1 on white
                        ),
                        multiple=False,
                    ),
                    dmc.Button("TRANSCRIBE & TRIAGE", mt="md", variant="light",
                               style={"color": "#1864ab"}),  # WCAG: 5.43:1 on light-blue bg
                ],
            ),
            visualization_asset(
                "viz-nlp-sentiment-heat",
                "Citizen Frustration Heatmap",
                "Spatial sentiment analysis.",
                "Heatmap of negative 311 sentiment.",
            ),
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    dmc.Paper(
                        withBorder=True,
                        p="lg",
                        children=[
                            dmc.Text("311 COMPLAINT PARSER", fw=700, mb="md"),
                            dmc.Textarea(id="nlp-parser-input", label="Raw Transcript", h=200),
                            dmc.Button(
                                "ANNOTATE & TRIAGE", id="btn-nlp-run", mt="md", color="blue"
                            ),
                        ],
                    ),
                    visualization_asset(
                        "viz-nlp-sentiment",
                        "Sentiment Polarization",
                        "NLP score distribution.",
                        "Distribution of sentiment across 311 calls.",
                    ),
                ],
            ),
            visualization_asset(
                "viz-311-treemap",
                "311 Complaint Hierarchy",
                "Taxonomy of citizen concerns.",
                "Top level: Sidewalk Condition.",
            ),
        ],
    )


def layout_settings():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("ENGINE CONFIGURATION", fw=900, size="xl", mb="lg", c="black"),
            dmc.Paper(
                withBorder=True,
                p="xl",
                radius="lg",
                children=[
                    dmc.Stack(
                        [
                            dmc.Text("SODA VERSIONING", fw=700, size="sm"),
                            dmc.SegmentedControl(
                                id={"type": "config-input", "index": "version"},
                                value="3.0",
                                data=[
                                    {"value": "2.1", "label": "SODA 2.1"},
                                    {"value": "3.0", "label": "SODA 3.0"},
                                ],
                                fullWidth=True,
                            ),
                            dmc.TextInput(
                                id={"type": "config-input", "index": "token"},
                                label="Socrata Token",
                                placeholder="***set***",
                            ),
                            dmc.NumberInput(
                                id={"type": "config-input", "index": "limit"},
                                label="Record Limit",
                                value=0,
                                description="Enter 0 for 'Total Recall' Unlimited Streaming mode.",
                            ),
                            dmc.TextInput(
                                id="set-slack-webhook",
                                label="Slack Notification Webhook (Item 99)",
                                placeholder="https://hooks.slack.com/services/...",
                            ),
                            dmc.Button(
                                "INITIALIZE & LOAD ALL DATASETS",
                                id={"type": "init-btn", "index": "main"},
                                fullWidth=True,
                                mt="xl",
                                color="blue",
                                size="lg",
                            ),
                        ]
                    )
                ],
            ),
        ],
    )


def layout_tutorials():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("KNOWLEDGE CENTER", fw=900, size="xl", mb="lg", c="black"),
            dmc.Accordion(
                children=[
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl("NYC DOT SIM Mandate Overview"),
                            dmc.AccordionPanel("Vision Zero compliance."),
                        ],
                        value="1",
                    ),
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl("Automated Reporting Workflows"),
                            dmc.AccordionPanel("Generating Pack docs."),
                        ],
                        value="2",
                    ),
                ]
            ),
        ],
    )


def layout_copilot():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Group(
                [
                    dmc.Text("AI ANALYST COPILOT", fw=900, size="xl", c="black"),
                    dmc.Select(
                        id="llm-model-select",
                        label="AI Model",
                        data=[
                            {"value": "gemini-1.5-pro", "label": "Gemini 1.5 Pro (Consensus)"},
                            {"value": "gpt-4o", "label": "GPT-4o (Reasoning)"},
                            {"value": "claude-3-5-sonnet", "label": "Claude 3.5 Sonnet (Coding)"},
                        ],
                        value="gemini-1.5-pro",
                        w=250,
                        size="xs",
                    ),
                ],
                justify="space-between",
                mb="lg",
            ),
            dmc.Paper(
                p="lg",
                withBorder=True,
                children=[
                    dmc.Text("Multi-Model Intelligence Hub", fw=700, mb="md"),
                    dmc.ScrollArea(h=400, children=[html.Div(id="copilot-history")]),
                    dmc.Group(
                        [
                            dmc.TextInput(
                                id="copilot-input",
                                aria_label="Ask the AI Copilot",
                                style={"flex": 1},
                            ),
                            dmc.Button("SEND", id="btn-copilot-send"),
                        ],
                        mt="md",
                    ),
                ],
            ),
        ],
    )


def layout_toolbox():
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            dmc.Text("ANALYTICAL TOOLBOX", fw=900, size="xl", mb="lg", c="black"),
            dmc.SimpleGrid(
                cols=2,
                spacing="lg",
                children=[
                    # Interactive Quality Audit Wizard
                    dmc.Paper(
                        withBorder=True,
                        p="lg",
                        radius="md",
                        shadow="sm",
                        children=[
                            dmc.Group(
                                [
                                    DashIconify(icon="mdi:shield-check", width=30, color="green"),
                                    dmc.Text("Quality Audit Wizard", fw=700, size="lg"),
                                ],
                                mb="md",
                            ),
                            dmc.Select(
                                id="audit-dataset-select",
                                label="Select Dataset for Audit",
                                data=["built", "inspection", "violations", "lot_info"],
                                value="built",
                                mb="md",
                            ),
                            dmc.Button(
                                "RUN EMPIRICAL AUDIT",
                                id="btn-run-audit",
                                fullWidth=True,
                                color="green",
                            ),
                            dmc.Divider(my="lg"),
                            html.Div(id="audit-results-container"),
                        ],
                    ),
                    # Executive Summary Generator
                    dmc.Paper(
                        withBorder=True,
                        p="lg",
                        radius="md",
                        shadow="sm",
                        children=[
                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="mdi:file-document-edit", width=30, color="blue"
                                    ),
                                    dmc.Text("Executive Summary Hub", fw=700, size="lg"),
                                ],
                                mb="md",
                            ),
                            dmc.Textarea(
                                id="summary-input",
                                label="Input Analysis Findings",
                                placeholder="Paste your raw analytical data here...",
                                h=150,
                                mb="md",
                            ),
                            dmc.Button(
                                "SYNTHESIZE EXECUTIVE BRIEF", id="btn-gen-summary", fullWidth=True
                            ),
                            dmc.Divider(my="lg"),
                            dmc.ScrollArea(
                                h=200, children=[html.Div(id="summary-output-container")]
                            ),
                        ],
                    ),
                ],
            ),
            dmc.Space(h="xl"),
            # Analysis History View
            dmc.Paper(
                withBorder=True,
                p="lg",
                radius="md",
                shadow="sm",
                children=[
                    dmc.Group(
                        [
                            DashIconify(icon="mdi:history", width=30, color="indigo"),
                            dmc.Text("Analysis Forensic History", fw=700, size="lg"),
                        ],
                        mb="md",
                    ),
                    dmc.Table(id="analysis-history-table"),
                ],
            ),
        ],
    )
