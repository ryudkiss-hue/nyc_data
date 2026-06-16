"""
Accessibility utilities for municipal data visualizations.
Ensures WCAG 2.1 AA compliance and provides text-based chart summaries.
"""

from __future__ import annotations

import logging
from typing import Any

from .branding import DOT_BLACK, PLOTLY_LAYOUT, WCAG_PALETTE

logger = logging.getLogger(__name__)

# WCAG 2.1 AA Compliant Color Palette for NYC DOT
# Use centralized palette from branding.py
def apply_wcag_palette(fig: Any) -> Any:
    """
    Applies a WCAG compliant color palette and DOT branding to a Plotly figure.

    Args:
        fig: A Plotly Figure object.

    Returns:
        The updated figure.
    """
    fig.update_layout(
        template="plotly_white",
        **PLOTLY_LAYOUT
    )
    # Ensure redundant encoding (markers + lines) for accessibility
    fig.update_traces(marker=dict(line=dict(color=DOT_BLACK, width=1)))

    logger.debug("Applied WCAG palette and DOT branding to figure")
    return fig

def generate_chart_summary(fig: Any) -> str:
    """
    Generates a text-based summary of the data within a Plotly chart.
    Provides redundancy for screen readers.

    Args:
        fig: A Plotly Figure object.

    Returns:
        A natural language summary of the chart data.
    """
    try:
        title = fig.layout.title.text or "Untitled Chart"
        summary = [f"Summary for '{title}':"]

        for i, trace in enumerate(fig.data):
            trace_name = trace.name or f"Trace {i+1}"
            if hasattr(trace, "x") and hasattr(trace, "y"):
                x_vals = list(trace.x)
                y_vals = list(trace.y)
                data_points = [f"{x}: {y}" for x, y in zip(x_vals, y_vals)]
                summary.append(f"- {trace_name} contains data: {', '.join(data_points)}")
            elif hasattr(trace, "values") and hasattr(trace, "labels"):
                labels = list(trace.labels)
                values = list(trace.values)
                data_points = [f"{lbl}: {val}" for lbl, val in zip(labels, values)]
                summary.append(f"- {trace_name} (Pie/Donut) distribution: {', '.join(data_points)}")

        return " ".join(summary)

    except Exception as e:
        logger.error("Failed to generate chart summary: %s", e)
        return "Chart summary unavailable."
