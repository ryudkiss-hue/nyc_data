"""dash_app/pages/health.py — System Health & Data Quality Observability"""

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html

import socrata_toolkit.analysis as st_analysis

dash.register_page(__name__, path="/health", name="System Health", order=9)

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("🏥 System Health", className="nyc-page-title"),
                html.P(
                    "Real-time data quality, SLA compliance, and infrastructure observability.",
                    className="nyc-page-sub",
                ),
            ],
            className="nyc-page-header nyc-animate-fade-up",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        figure=st_analysis.gauge_chart(
                            98.2, target=95.0, title="City-Wide Data Quality"
                        ),
                        config={"displayModeBar": False},
                    ),
                    md=4,
                ),
                dbc.Col(
                    dcc.Graph(
                        figure=st_analysis.gauge_chart(
                            84.5, target=90.0, title="SLA Compliance Rate"
                        ),
                        config={"displayModeBar": False},
                    ),
                    md=4,
                ),
                dbc.Col(
                    dcc.Graph(
                        figure=st_analysis.gauge_chart(
                            12, target=5, title="Active Infrastructure Alerts"
                        ),
                        config={"displayModeBar": False},
                    ),
                    md=4,
                ),
            ],
            className="mb-4 nyc-animate-fade-up stagger-1",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H5("Data Quality Anomalies", className="text-accent mb-3"),
                                html.Div(id="health-anomalies-list"),
                            ],
                            className="nyc-card nyc-card-hover",
                        )
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H5("SLA Violation Drift", className="text-accent mb-3"),
                                dcc.Graph(id="health-sla-chart"),
                            ],
                            className="nyc-card nyc-card-hover",
                        )
                    ],
                    md=6,
                ),
            ],
            className="nyc-animate-fade-up stagger-2",
        ),
    ],
    fluid=True,
)


@callback(
    Output("health-anomalies-list", "children"),
    Output("health-sla-chart", "figure"),
    Input("session-store", "data"),
)
def update_health(_):
    # Simulated data for health view
    anoms = [
        {
            "id": "VIO-882",
            "type": "Schema Drift",
            "severity": "High",
            "desc": "Sidewalk Inspections: Column 'inspector_id' type changed to INT",
        },
        {
            "id": "QC-102",
            "type": "Null Spike",
            "severity": "Critical",
            "desc": "Traffic Sensors: 42% null values in 'speed' column since 06:00",
        },
        {
            "id": "ADA-404",
            "type": "Compliance Drop",
            "severity": "Medium",
            "desc": "Manhattan Dist 4: Compliance score dropped to 72%",
        },
    ]

    list_items = [
        html.Div(
            [
                html.Span(a["id"], className="fw-bold me-2"),
                html.Span(
                    a["type"],
                    className=f"nyc-pill nyc-pill-{'red' if a['severity'] == 'Critical' else 'yellow'} me-2",
                ),
                html.P(a["desc"], className="small text-muted mb-0"),
            ],
            className="nyc-status-warn mb-2",
        )
        for a in anoms
    ]

    # SLA Drift simulation
    df_sla = pd.DataFrame(
        {
            "Date": pd.date_range("2026-05-01", periods=14),
            "Compliance": [92, 91, 88, 85, 84, 82, 80, 82, 85, 88, 90, 89, 87, 84],
        }
    )
    fig = st_analysis.time_series_chart(df_sla, "Date", "Compliance")
    fig.update_layout(height=300)

    return list_items, fig
