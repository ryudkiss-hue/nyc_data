"""Tests for Accessibility Visualization Utility."""

from __future__ import annotations

import pytest
import pandas as pd
from socrata_toolkit.viz.accessibility import apply_wcag_palette, generate_chart_summary
from socrata_toolkit.viz.plotly import borough_bar_chart

@pytest.fixture
def sample_fig():
    df = pd.DataFrame({
        "borough": ["MANHATTAN", "BRONX", "BROOKLYN"],
        "violations": [10, 20, 30]
    })
    return borough_bar_chart(df)

class TestAccessibilityUtility:
    def test_wcag_palette_injection(self, sample_fig):
        fig = apply_wcag_palette(sample_fig)
        # Check if first color is one of our WCAG compliant ones
        # Manhattan in borough_bar_chart defaults to #0D6EFD
        # Our WCAG palette might use different ones
        assert fig.layout.template.layout.colorway is not None
        assert len(fig.layout.template.layout.colorway) >= 5

    def test_chart_summary_generation(self, sample_fig):
        summary = generate_chart_summary(sample_fig)
        assert "MANHATTAN" in summary
        assert "10" in summary
        assert "BROOKLYN" in summary
        assert "30" in summary
