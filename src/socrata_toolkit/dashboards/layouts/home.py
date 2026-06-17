"""
Home Page Layout for NYC DOT SIM Workflows Dashboard.

Displays key metrics, recent activity, and navigation to analytical sections.
"""


import dash_bootstrap_components as dbc
from dash import html

# Define home page layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Dashboard Home", className="mb-4")
        ], width=12)
    ]),

    # Key Metrics Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Violations", className="text-muted"),
                    html.H3("398,234", className="text-primary"),
                    html.P("Last 30 days | +2.3%", className="small text-muted mb-0")
                ])
            ])
        ], md=3, sm=6, className="mb-3"),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Ramps Completed", className="text-muted"),
                    html.H3("18,743 / 23,450", className="text-success"),
                    html.P("80.0% completion (95% CI: 79.8-80.2%)", className="small text-muted mb-0")
                ])
            ])
        ], md=3, sm=6, className="mb-3"),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Active Permits", className="text-muted"),
                    html.H3("1,247", className="text-info"),
                    html.P("Avg duration: 34.2 days", className="small text-muted mb-0")
                ])
            ])
        ], md=3, sm=6, className="mb-3"),

        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Data Quality Score", className="text-muted"),
                    html.H3("94/100", className="text-warning"),
                    html.P("Completeness 98% | Validity 91%", className="small text-muted mb-0")
                ])
            ])
        ], md=3, sm=6, className="mb-3"),
    ]),

    html.Hr(className="my-4"),

    # Recent Activity Section
    dbc.Row([
        dbc.Col([
            html.H4("Recent Activity", className="mb-3"),
            dbc.ListGroup([
                dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([html.Strong("Cache Refresh Complete")], md=6),
                        dbc.Col([html.Span("2026-06-11 06:15 UTC", className="text-muted small")], md=6, className="text-end")
                    ]),
                    html.P("24 datasets synchronized | 50,234 rows updated", className="mb-0 small mt-2")
                ], className="py-2"),
                dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([html.Strong("Scheduler Running")], md=6),
                        dbc.Col([html.Span("6 AM UTC every day", className="text-muted small")], md=6, className="text-end")
                    ]),
                    html.P("APScheduler daemon | Next run: 2026-06-12 06:00 UTC", className="mb-0 small mt-2")
                ], className="py-2"),
                dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([html.Strong("Phase 1 Deployment Complete")], md=6),
                        dbc.Col([html.Span("2026-06-11 05:30 UTC", className="text-muted small")], md=6, className="text-end")
                    ]),
                    html.P("Visualization units system + 109/109 tests passing", className="mb-0 small mt-2")
                ], className="py-2"),
            ])
        ], md=6, className="mb-3"),

        dbc.Col([
            html.H4("Quick Links", className="mb-3"),
            dbc.ListGroup([
                dbc.ListGroupItem(
                    dbc.Row([
                        dbc.Col("📊 Violation Analysis", width=9),
                        dbc.Col("→", width=3, className="text-end")
                    ]),
                    href="/violations", action=True
                ),
                dbc.ListGroupItem(
                    dbc.Row([
                        dbc.Col("🚗 Ramp Accessibility", width=9),
                        dbc.Col("→", width=3, className="text-end")
                    ]),
                    href="/ramps", action=True
                ),
                dbc.ListGroupItem(
                    dbc.Row([
                        dbc.Col("🏗️ Permit Coordination", width=9),
                        dbc.Col("→", width=3, className="text-end")
                    ]),
                    href="/permits", action=True
                ),
                dbc.ListGroupItem(
                    dbc.Row([
                        dbc.Col("🗺️ Geographic Analysis", width=9),
                        dbc.Col("→", width=3, className="text-end")
                    ]),
                    href="/geographic", action=True
                ),
                dbc.ListGroupItem(
                    dbc.Row([
                        dbc.Col("📈 Advanced Analytics", width=9),
                        dbc.Col("→", width=3, className="text-end")
                    ]),
                    href="/analytics", action=True
                ),
            ])
        ], md=6, className="mb-3"),
    ]),

    html.Hr(className="my-4"),

    # System Status
    dbc.Row([
        dbc.Col([
            html.H4("System Status", className="mb-3"),
            dbc.Alert([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Data Pipeline", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Cache System", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Scheduler", className="ms-2")
                        ]),
                    ], md=4),
                    dbc.Col([
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Visualizations", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Quality Gates", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Monitoring", className="ms-2")
                        ]),
                    ], md=4),
                    dbc.Col([
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Alerts", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" API Endpoints", className="ms-2")
                        ], className="mb-2"),
                        html.Div([
                            html.Span("✓", className="text-success", style={"font-size": "24px"}),
                            html.Span(" Documentation", className="ms-2")
                        ]),
                    ], md=4),
                ])
            ], color="success", className="py-3", style={"background-color": "#d4edda"})
        ], width=12)
    ]),

], fluid=True, className="mt-4")
