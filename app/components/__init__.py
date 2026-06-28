"""
App Components: Reusable Dash components for analytics dashboard.

Includes:
- filter_system: Borough, date range, metric type selectors
- metric_cards: 18 dynamic Metric card dashboard
- main_navigation: 4-view sidebar navigation (Executive, Operations, Analyst, Data)
"""

from app.components.filter_system import register_filter_callbacks, render_filter_bar
from app.components.main_navigation import (
    get_navigation_css,
    get_navigation_items,
    register_navigation_callbacks,
    render_main_navigation,
    render_mobile_navigation_trigger,
    render_navigation_store,
)
from app.components.metric_cards import register_metric_callbacks, render_metric_dashboard

__all__ = [
    "render_filter_bar",
    "register_filter_callbacks",
    "render_metric_dashboard",
    "register_metric_callbacks",
    "get_navigation_items",
    "render_main_navigation",
    "render_mobile_navigation_trigger",
    "render_navigation_store",
    "register_navigation_callbacks",
    "get_navigation_css",
]
