"""
App Components: Reusable Dash components for analytics dashboard.

Includes:
- filter_system: Borough, date range, metric type selectors
- kpi_cards: 18 dynamic KPI card dashboard
- main_navigation: 4-view sidebar navigation (Executive, Operations, Analyst, Data)
"""

from app.components.filter_system import register_filter_callbacks, render_filter_bar
from app.components.kpi_cards import register_kpi_callbacks, render_kpi_dashboard
from app.components.main_navigation import (
    get_navigation_items,
    render_main_navigation,
    render_mobile_navigation_trigger,
    render_navigation_store,
    register_navigation_callbacks,
    get_navigation_css,
)

__all__ = [
    "render_filter_bar",
    "register_filter_callbacks",
    "render_kpi_dashboard",
    "register_kpi_callbacks",
    "get_navigation_items",
    "render_main_navigation",
    "render_mobile_navigation_trigger",
    "render_navigation_store",
    "register_navigation_callbacks",
    "get_navigation_css",
]
