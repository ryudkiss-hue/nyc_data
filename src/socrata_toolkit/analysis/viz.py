from __future__ import annotations

from typing import Any

from .metrics import compute_borough_metrics, compute_sla_trends
from .profiling import profile_dataframe

_PLOTLY_THEME = "plotly_dark"
_FONT_FAMILY = "Inter, sans-serif"

def _apply_modern_layout(fig: Any, title: str | None = None) -> Any:
    """Standardize the look and feel of all Plotly charts."""
    import plotly.express as px

    fig.update_layout(
        title=(
            {
                "text": title,
                "font": {"size": 22, "family": _FONT_FAMILY, "weight": "bold"},
                "x": 0.02,
                "xanchor": "left",
            }
            if title
            else None
        ),
        font_family=_FONT_FAMILY,
        template=_PLOTLY_THEME,
        colorway=px.colors.qualitative.Safe,
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.8)",
            font_size=13,
            font_family=_FONT_FAMILY,
        ),
        margin=dict(t=80 if title else 40, l=40, r=40, b=60),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def histogram(df: pd.DataFrame, column: str, title: str | None = None) -> Any:
    import plotly.express as px
    fig = px.histogram(df, x=column, marginal="box", opacity=0.75)
    return _apply_modern_layout(fig, title or f"Distribution: {column}")

def bar_chart(df: pd.DataFrame, column: str, title: str | None = None) -> Any:
    import plotly.express as px
    counts = df[column].value_counts().head(15).reset_index()
    counts.columns = [column, "Count"]
    fig = px.bar(counts, x=column, y="Count", color="Count", color_continuous_scale="Blues")
    return _apply_modern_layout(fig, title or f"Top Categories: {column}")
