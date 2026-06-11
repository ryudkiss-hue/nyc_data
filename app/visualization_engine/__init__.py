"""Visualization rendering engine for all 73 MotherDuck visualizations.

PHASE 2: VISUALIZATION RENDERING

Implements interactive Plotly charts for all 73 visualizations across 6 analytical phases:
- Phase B: Spatial Clustering & Moran's I (12 charts)
- Phase C: Distribution Analysis & Histograms (13 charts)
- Phase D: Geographic Anomalies & Maps (15 charts)
- Phase E: Time Series Decomposition (16 charts)
- Phase F: Bootstrap CI & SLA Gauges (17 charts)
- KPI Cards: Dashboard metrics (18 cards)
- Universal Stats: Reusable statistics display component

All data comes from MotherDuck (app_queries schema).
Each visualization includes summary statistics below the chart.

TOTAL VISUALIZATIONS: 73
- Phase B: 12 charts
- Phase C: 13 charts
- Phase D: 15 charts
- Phase E: 16 charts
- Phase F: 17 charts

TOTAL KPI CARDS: 18
- 18 KPIs × 5 boroughs = 90 total card instances

Example usage:
    from app.visualization_engine import PhaseBVisualizations, StatisticsPanel
    from socrata_toolkit.motherduck.connector import MotherDuckConnection

    conn = MotherDuckConnection(token="your_token")
    phase_b = PhaseBVisualizations(conn)

    # Render all Phase B charts
    charts = phase_b.render_all_phase_b_charts()

    # Each chart is a tuple of (figure, statistics)
    for name, (fig, stats) in charts.items():
        html_stats = stats.to_html()
        # Display fig.to_html() + html_stats in Dash callback
"""

from .phase_b import PhaseBVisualizations
from .phase_c import PhaseCVisualizations
from .phase_d import PhaseDVisualizations
from .phase_e import PhaseEVisualizations
from .phase_f import PhaseFVisualizations
from .kpi_cards import KPICards
from .statistics_display import StatisticsPanel

__all__ = [
    "PhaseBVisualizations",
    "PhaseCVisualizations",
    "PhaseDVisualizations",
    "PhaseEVisualizations",
    "PhaseFVisualizations",
    "KPICards",
    "StatisticsPanel",
]

__version__ = "0.1.0"
__author__ = "NYC DOT Analytics Team"
