"""
Executive Dashboard — Refined Data Luxury
Dark luxury aesthetic with gold accents, minimalist brutalism for C-suite.
Real-time KPI monitoring with elegant metric cards and trend indicators.
"""

import random
from datetime import datetime

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

# ============================================================================
# THEME & STYLING
# ============================================================================

DARK_BG = "#0f1419"
CARD_BG = "#1a1f2e"
TEXT_PRIMARY = "#f5f7fa"
TEXT_SECONDARY = "#a0a8b8"
ACCENT_GOLD = "#d4af37"
ACCENT_SECONDARY = "#8e7cc3"
POSITIVE = "#10b981"
NEGATIVE = "#ef4444"

EXECUTIVE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+Pro:wght@300;400;600&display=swap');

body {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'Source Sans Pro', sans-serif;
    margin: 0;
    padding: 0;
}}

.executive-header {{
    background: linear-gradient(135deg, {CARD_BG} 0%, rgba(212, 175, 55, 0.05) 100%);
    border-bottom: 2px solid {ACCENT_GOLD};
    padding: 2rem 3rem;
    margin-bottom: 2rem;
}}

.executive-header h1 {{
    font-family: 'Playfair Display', serif;
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    color: {TEXT_PRIMARY};
    letter-spacing: -0.5px;
}}

.executive-header .subtitle {{
    font-size: 0.95rem;
    color: {TEXT_SECONDARY};
    margin-top: 0.5rem;
}}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
    padding: 0 3rem;
    margin-bottom: 2rem;
}}

.kpi-card {{
    background: {CARD_BG};
    border: 1px solid rgba(212, 175, 55, 0.2);
    border-radius: 8px;
    padding: 1.5rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}}

.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, {ACCENT_GOLD}, transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
}}

.kpi-card:hover {{
    border-color: {ACCENT_GOLD};
    box-shadow: 0 8px 24px rgba(212, 175, 55, 0.1);
}}

.kpi-card:hover::before {{
    opacity: 1;
}}

.kpi-label {{
    font-size: 0.85rem;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.75rem;
    font-weight: 600;
}}

.kpi-value {{
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    margin-bottom: 0.5rem;
    letter-spacing: -1px;
}}

.kpi-trend {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
}}

.kpi-trend.positive {{
    color: {POSITIVE};
}}

.kpi-trend.negative {{
    color: {NEGATIVE};
}}

.dashboard-section {{
    padding: 0 3rem;
    margin-bottom: 2rem;
}}

.section-title {{
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    margin-bottom: 1rem;
    letter-spacing: -0.5px;
}}

.chart-container {{
    background: {CARD_BG};
    border: 1px solid rgba(212, 175, 55, 0.15);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}}

.chart-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
}}

.status-indicator {{
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 0.5rem;
    animation: pulse 2s infinite;
}}

.status-indicator.active {{
    background-color: {POSITIVE};
}}

.status-indicator.warning {{
    background-color: #f59e0b;
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.6; }}
}}
"""

def generate_time_series(start_value=85, days=30, volatility=2):
    """Generate realistic KPI time series."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    values = [start_value]
    for _ in range(days - 1):
        change = values[-1] * (volatility / 100) * (1 if random.random() > 0.5 else -1)
        values.append(max(0, values[-1] + change))
    return dates, values

def create_kpi_card(label, value, unit, trend, trend_value, is_positive=True):
    """Create KPI card component."""
    trend_color = "positive" if (trend_value > 0 and is_positive) or (trend_value < 0 and not is_positive) else "negative"
    trend_arrow = "↑" if trend_value > 0 else "↓"

    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(f"{value}{unit}", className="kpi-value"),
        html.Div([
            html.Span(f"{trend_arrow} {abs(trend_value):.1f}%", style={"marginRight": "0.5rem"}),
            html.Span(trend)
        ], className=f"kpi-trend {trend_color}")
    ], className="kpi-card")

def create_executive_dashboard():
    """Create executive dashboard layout."""
    dates_30d, values_30d = generate_time_series(85, 30, 1.5)

    fig_velocity = go.Figure()
    fig_velocity.add_trace(go.Scatter(
        x=dates_30d, y=values_30d,
        name='Completion Velocity',
        mode='lines+markers',
        line=dict(color=ACCENT_GOLD, width=3),
        marker=dict(size=6, color=ACCENT_GOLD),
        fill='tozeroy',
        fillcolor='rgba(212, 175, 55, 0.1)',
    ))
    fig_velocity.update_layout(
        template='plotly_dark',
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        hovermode='x unified',
        margin=dict(l=40, r=20, t=20, b=40),
        height=300,
        font=dict(family='Source Sans Pro', color=TEXT_SECONDARY),
        showlegend=False,
    )
    fig_velocity.update_xaxes(showgrid=False, zeroline=False)
    fig_velocity.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(212, 175, 55, 0.1)')

    fig_borough = go.Figure()
    boroughs = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
    completion_rates = [87, 79, 74, 68, 61]
    colors = [ACCENT_GOLD if rate >= 80 else ACCENT_SECONDARY for rate in completion_rates]

    fig_borough.add_trace(go.Bar(
        x=boroughs,
        y=completion_rates,
        marker=dict(color=colors),
        text=[f'{rate}%' for rate in completion_rates],
        textposition='outside',
    ))
    fig_borough.update_layout(
        template='plotly_dark',
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        margin=dict(l=40, r=20, t=20, b=40),
        height=300,
        font=dict(family='Source Sans Pro', color=TEXT_SECONDARY),
        showlegend=False,
    )
    fig_borough.update_xaxes(showgrid=False)
    fig_borough.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(212, 175, 55, 0.1)')

    return html.Div([
        dcc.Style(children=EXECUTIVE_CSS),

        # Header
        html.Div([
            html.H1("Executive Dashboard"),
            html.Div("NYC DOT Sidewalk Inspection & Management — Real-time KPI Monitoring",
                    className="subtitle")
        ], className="executive-header"),

        # KPI Grid
        html.Div([
            create_kpi_card("Completion Rate", "87.4", "%", "vs. last 30d", 2.1, is_positive=True),
            create_kpi_card("Avg Response Time", "2.3", " days", "vs. target", -0.8, is_positive=False),
            create_kpi_card("Quality Score", "92", "/100", "vs. baseline", 4.2, is_positive=True),
            create_kpi_card("SLA Compliance", "94.1", "%", "vs. target", 1.5, is_positive=True),
        ], className="kpi-grid"),

        # System Status
        html.Div([
            html.H2("System Status", className="section-title"),
            html.Div([
                html.Div([
                    html.Span("●", className="status-indicator active"),
                    html.Span("Data Pipeline", style={"marginRight": "auto"}),
                    html.Span("Operational", style={"color": POSITIVE})
                ], style={"display": "flex", "alignItems": "center", "padding": "0.75rem",
                         "background": "rgba(16, 185, 129, 0.05)", "borderRadius": "4px",
                         "marginBottom": "0.75rem"}),
                html.Div([
                    html.Span("●", className="status-indicator active"),
                    html.Span("API Gateway", style={"marginRight": "auto"}),
                    html.Span("Operational", style={"color": POSITIVE})
                ], style={"display": "flex", "alignItems": "center", "padding": "0.75rem",
                         "background": "rgba(16, 185, 129, 0.05)", "borderRadius": "4px"}),
            ], className="chart-container")
        ], className="dashboard-section"),

        # Charts
        html.Div([
            html.H2("Performance Trends", className="section-title"),
            html.Div([
                html.Div([
                    html.Div("30-Day Completion Velocity", style={"marginBottom": "1rem", "color": TEXT_SECONDARY}),
                    dcc.Graph(figure=fig_velocity, config={'displayModeBar': False})
                ], className="chart-container"),
                html.Div([
                    html.Div("Completion Rate by Borough", style={"marginBottom": "1rem", "color": TEXT_SECONDARY}),
                    dcc.Graph(figure=fig_borough, config={'displayModeBar': False})
                ], className="chart-container"),
            ], className="chart-grid"),
        ], className="dashboard-section"),

        # Footer
        html.Div(
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            style={"textAlign": "center", "color": TEXT_SECONDARY, "padding": "2rem 3rem",
                   "fontSize": "0.85rem", "borderTop": "1px solid rgba(212, 175, 55, 0.1)"}
        ),
    ], style={"backgroundColor": DARK_BG, "minHeight": "100vh"})

if __name__ == "__main__":
    app = dash.Dash(__name__)
    app.layout = create_executive_dashboard()
    app.run_server(debug=True, port=8051)
