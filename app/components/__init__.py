"""
App Components: Reusable Dash components for analytics dashboard.

Includes:
- filter_system: Borough, date range, metric type selectors
- kpi_cards: 18 dynamic KPI card dashboard
"""

from app.components.filter_system import register_filter_callbacks, render_filter_bar
from app.components.kpi_cards import register_kpi_callbacks, render_kpi_dashboard

__all__ = [
    "render_filter_bar",
    "register_filter_callbacks",
    "render_kpi_dashboard",
    "register_kpi_callbacks",
]
