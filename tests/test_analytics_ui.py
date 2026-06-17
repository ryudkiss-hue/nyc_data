"""Tests for Dash UI & Toolbox."""

from __future__ import annotations


def test_toolbox_layout_exists():
    from app.dash_layouts import layout_toolbox

    layout = layout_toolbox()
    assert layout is not None
    # Check for key components
    assert "ANALYTICAL TOOLBOX" in str(layout)
    assert "audit-dataset-select" in str(layout)
    assert "analysis-history-table" in str(layout)


def test_toolbox_routing():
    from app.dash_app import render_page_content

    layout = render_page_content("/toolbox")
    assert "ANALYTICAL TOOLBOX" in str(layout)
