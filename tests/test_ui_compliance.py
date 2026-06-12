import json

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
import pytest

from app.dash_layouts import render_header, render_sidebar
from app.viz_engine import VisualizationEngine


def _find_values_in_component(comp, key_to_find=None, val_to_find=None):
    """Recursively search Dash component tree for specific prop keys or values."""
    found = False

    if not hasattr(comp, "to_plotly_json"):
        return False

    data = comp.to_plotly_json()
    props = data.get("props", {})

    # Check current node
    if key_to_find and key_to_find in props:
        found = True
    if val_to_find and any(val_to_find in str(v) for v in props.values() if isinstance(v, str)):
        found = True

    if found:
        return True

    # Check children
    children = props.get("children", [])
    if not isinstance(children, list):
        children = [children]

    for child in children:
        if _find_values_in_component(child, key_to_find, val_to_find):
            return True

    return False


def test_header_accessibility_markup():
    """Verify that the header contains appropriate accessible labels."""
    header = render_header()
    assert _find_values_in_component(header, key_to_find="aria-label")
    assert _find_values_in_component(header, val_to_find="NYC DOT Socrata Toolkit Header")
    assert _find_values_in_component(header, val_to_find="toolkit-brand")


def test_sidebar_navigation_labels():
    """Verify that navigation links have distinct labels."""
    sidebar = render_sidebar()
    assert _find_values_in_component(sidebar, val_to_find="MISSION COMMAND")
    assert _find_values_in_component(sidebar, val_to_find="Structural Mandate")


def test_visualization_summary_generation():
    """Verify that the engine generates textual summaries for screen readers."""
    # Create a figure with known data
    fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[10, 20])])
    fig.update_layout(title="Test Chart")

    # Generate summary (Using the logic from socrata_toolkit if available)
    # or verifying the one in VisualizationEngine
    from socrata_toolkit.viz.accessibility import generate_chart_summary

    summary = generate_chart_summary(fig)
    assert "Test Chart" in summary
    assert "A" in summary
    assert "10" in summary
    assert "B" in summary
    assert "20" in summary


def test_dmc_component_semantic_integrity():
    """Ensure heavy UI components use correct Mantine 8.0 alpha semantic props."""
    # Example: AppShell should have appropriate structure
    from app.dash_app import app

    layout = app.layout

    # Provider should be at the root
    assert isinstance(layout, dmc.MantineProvider)

    # AppShell should be a descendant
    def find_component(comp, target_type):
        if isinstance(comp, target_type):
            return True
        if hasattr(comp, "children") and comp.children:
            children = comp.children if isinstance(comp.children, list) else [comp.children]
            return any(find_component(c, target_type) for c in children)
        return False

    assert find_component(layout, dmc.AppShell)
