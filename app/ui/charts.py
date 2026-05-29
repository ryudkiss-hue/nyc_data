"""Reusable Plotly chart factory for Manhattan Mission Control.

Centralizes the dark agency theme, color-blind-safe palettes, accessible
hover templates, time-series range selectors, faceted small multiples, and
a chart→data-table accessibility fallback. Every public helper returns a
``plotly.graph_objects.Figure`` (or None when data is insufficient) so callers
keep full control over ``st.plotly_chart``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:  # pragma: no cover
    px = None  # type: ignore
    go = None  # type: ignore
    _HAS_PLOTLY = False

try:
    import streamlit as st
    _HAS_ST = True
except ImportError:  # pragma: no cover
    st = None  # type: ignore
    _HAS_ST = False

from app.ui.palettes import AGENCY_CATEGORICAL, VIRIDIS, categorical

# ---------------------------------------------------------------------------
# Shared layout
# ---------------------------------------------------------------------------
_PAPER = "#0a1628"
_PLOT = "#0d1b2a"
_GRID = "#1e3050"
_FONT = "#c5d4e3"
_TITLE = "#e8eef4"

_BASE_LAYOUT: dict[str, Any] = {
    "template": "plotly_dark",
    "paper_bgcolor": _PAPER,
    "plot_bgcolor": _PLOT,
    "font": {"color": _FONT, "size": 13},
    "title": {"font": {"color": _TITLE, "size": 16}},
    "margin": {"l": 10, "r": 10, "t": 40, "b": 10},
    "legend": {
        "bgcolor": "rgba(0,0,0,0)",
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "right",
        "x": 1,
    },
    "xaxis": {"gridcolor": _GRID, "zerolinecolor": _GRID},
    "yaxis": {"gridcolor": _GRID, "zerolinecolor": _GRID},
    "hoverlabel": {"bgcolor": "#152238", "font_size": 13, "font_family": "monospace"},
}


def available() -> bool:
    """True when Plotly is importable."""
    return _HAS_PLOTLY


def apply_theme(fig: go.Figure, *, height: int | None = None) -> go.Figure:
    """Apply the agency dark theme to any Plotly figure."""
    fig.update_layout(**_BASE_LAYOUT)
    if height:
        fig.update_layout(height=height)
    return fig


# ---------------------------------------------------------------------------
# Time-series with range selector
# ---------------------------------------------------------------------------
def time_series(
    df: pd.DataFrame,
    *,
    x: str,
    y: str | list[str],
    title: str = "",
    height: int = 360,
    range_selector: bool = True,
) -> go.Figure | None:
    """Line chart with 1M/3M/6M/YTD/1Y/All range buttons and a range slider."""
    if not _HAS_PLOTLY or df.empty or x not in df.columns:
        return None
    ys = [y] if isinstance(y, str) else y
    ys = [c for c in ys if c in df.columns]
    if not ys:
        return None

    colors = categorical(len(ys))
    fig = go.Figure()
    for col, color in zip(ys, colors, strict=False):
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[col],
                mode="lines",
                name=col.replace("_", " ").title(),
                line={"color": color, "width": 2},
                hovertemplate=f"<b>{col}</b><br>%{{x}}<br>%{{y:,.0f}}<extra></extra>",
            )
        )
    apply_theme(fig, height=height)
    if title:
        fig.update_layout(title=title)
    if range_selector:
        fig.update_xaxes(
            rangeslider_visible=True,
            rangeselector={
                "bgcolor": "#152238",
                "activecolor": "#3B82F6",
                "font": {"color": _FONT},
                "buttons": [
                    {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                    {"count": 3, "label": "3M", "step": "month", "stepmode": "backward"},
                    {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
                    {"count": 1, "label": "YTD", "step": "year", "stepmode": "todate"},
                    {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "All"},
                ],
            },
        )
    return fig


# ---------------------------------------------------------------------------
# Bar chart
# ---------------------------------------------------------------------------
def bar(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    title: str = "",
    height: int = 320,
    color: str | None = None,
    orientation: str = "v",
) -> go.Figure | None:
    """Themed bar chart (vertical or horizontal)."""
    if not _HAS_PLOTLY or df.empty or x not in df.columns or y not in df.columns:
        return None
    fig = px.bar(
        df,
        x=x if orientation == "v" else y,
        y=y if orientation == "v" else x,
        color=color if color and color in df.columns else None,
        color_discrete_sequence=AGENCY_CATEGORICAL,
        orientation=orientation,
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"
        if orientation == "v"
        else "<b>%{y}</b><br>%{x:,.0f}<extra></extra>"
    )
    apply_theme(fig, height=height)
    if title:
        fig.update_layout(title=title)
    return fig


# ---------------------------------------------------------------------------
# Faceted small multiples
# ---------------------------------------------------------------------------
def small_multiples(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    facet: str,
    title: str = "",
    facet_col_wrap: int = 3,
    height: int = 420,
) -> go.Figure | None:
    """Faceted line/area small multiples with shared axes for comparison."""
    if not _HAS_PLOTLY or df.empty:
        return None
    needed = {x, y, facet}
    if not needed.issubset(df.columns):
        return None
    fig = px.line(
        df,
        x=x,
        y=y,
        facet_col=facet,
        facet_col_wrap=facet_col_wrap,
        color_discrete_sequence=AGENCY_CATEGORICAL,
    )
    fig.update_yaxes(matches=None)  # let each panel scale, but label clearly
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    apply_theme(fig, height=height)
    if title:
        fig.update_layout(title=title)
    return fig


# ---------------------------------------------------------------------------
# Distribution — box plot
# ---------------------------------------------------------------------------
def box_plot(
    df: pd.DataFrame,
    *,
    y: str,
    group: str | None = None,
    title: str = "",
    height: int = 340,
) -> go.Figure | None:
    """Box plot of a numeric column, optionally split by a categorical group."""
    if not _HAS_PLOTLY or df.empty or y not in df.columns:
        return None
    if not pd.api.types.is_numeric_dtype(df[y]):
        return None
    fig = px.box(
        df,
        x=group if group and group in df.columns else None,
        y=y,
        color=group if group and group in df.columns else None,
        color_discrete_sequence=AGENCY_CATEGORICAL,
        points="outliers",
    )
    apply_theme(fig, height=height)
    if title:
        fig.update_layout(title=title)
    return fig


# ---------------------------------------------------------------------------
# Correlation heatmap (diverging)
# ---------------------------------------------------------------------------
def correlation_heatmap(
    df: pd.DataFrame,
    *,
    title: str = "",
    height: int = 420,
    max_cols: int = 15,
) -> go.Figure | None:
    """Correlation matrix heatmap over numeric columns (RdBu diverging)."""
    if not _HAS_PLOTLY or df.empty:
        return None
    num = df.select_dtypes(include="number")
    if num.shape[1] < 2:
        return None
    if num.shape[1] > max_cols:
        num = num.iloc[:, :max_cols]
    corr = num.corr().round(2)
    fig = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=list(corr.columns),
            y=list(corr.index),
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr.values,
            texttemplate="%{text}",
            textfont={"size": 10},
            hovertemplate="%{x} × %{y}: %{z}<extra></extra>",
        )
    )
    apply_theme(fig, height=height)
    if title:
        fig.update_layout(title=title)
    return fig


# ---------------------------------------------------------------------------
# Treemap (hierarchical proportions)
# ---------------------------------------------------------------------------
def treemap(
    df: pd.DataFrame,
    *,
    path: list[str],
    values: str,
    title: str = "",
    height: int = 420,
) -> go.Figure | None:
    """Treemap for hierarchical category → value proportions."""
    if not _HAS_PLOTLY or df.empty or values not in df.columns:
        return None
    valid_path = [c for c in path if c in df.columns]
    if not valid_path:
        return None
    fig = px.treemap(
        df,
        path=valid_path,
        values=values,
        color_discrete_sequence=AGENCY_CATEGORICAL,
    )
    fig.update_traces(hovertemplate="<b>%{label}</b><br>%{value:,.0f}<extra></extra>")
    apply_theme(fig, height=height)
    if title:
        fig.update_layout(title=title)
    return fig


# ---------------------------------------------------------------------------
# Pareto (sorted bars + cumulative % line)
# ---------------------------------------------------------------------------
def pareto(
    df: pd.DataFrame,
    *,
    category: str,
    value: str,
    title: str = "",
    height: int = 360,
    top_n: int = 15,
) -> go.Figure | None:
    """Pareto chart: descending bars with a cumulative-percentage line."""
    if not _HAS_PLOTLY or df.empty:
        return None
    if category not in df.columns or value not in df.columns:
        return None
    agg = (
        df.groupby(category, dropna=False)[value]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    if agg.empty:
        return None
    total = agg[value].sum() or 1
    agg["cum_pct"] = 100 * agg[value].cumsum() / total
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=agg[category].astype(str),
            y=agg[value],
            name=value.replace("_", " ").title(),
            marker_color="#3B82F6",
            hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=agg[category].astype(str),
            y=agg["cum_pct"],
            name="Cumulative %",
            yaxis="y2",
            mode="lines+markers",
            line={"color": "#F4C430", "width": 2},
            hovertemplate="%{y:.1f}%<extra></extra>",
        )
    )
    apply_theme(fig, height=height)
    fig.update_layout(
        title=title or None,
        yaxis2={"overlaying": "y", "side": "right", "range": [0, 105],
                "ticksuffix": "%", "gridcolor": "rgba(0,0,0,0)"},
    )
    return fig


# ---------------------------------------------------------------------------
# Density heatmap (sequential viridis)
# ---------------------------------------------------------------------------
def density_map(
    df: pd.DataFrame,
    *,
    lat: str,
    lon: str,
    title: str = "",
    height: int = 420,
    zoom: int = 10,
) -> go.Figure | None:
    """Mapbox density heatmap using a perceptually-uniform scale."""
    if not _HAS_PLOTLY or df.empty or lat not in df.columns or lon not in df.columns:
        return None
    sample = df.dropna(subset=[lat, lon])
    if sample.empty:
        return None
    if len(sample) > 5000:
        sample = sample.sample(5000, random_state=42)
    fig = go.Figure(
        go.Densitymapbox(
            lat=sample[lat],
            lon=sample[lon],
            radius=12,
            colorscale="Viridis",
            hovertemplate="(%{lat:.4f}, %{lon:.4f})<extra></extra>",
        )
    )
    fig.update_layout(
        mapbox={"style": "carto-darkmatter",
                "center": {"lat": float(sample[lat].mean()), "lon": float(sample[lon].mean())},
                "zoom": zoom},
        height=height,
        margin={"l": 0, "r": 0, "t": 30 if title else 0, "b": 0},
        paper_bgcolor=_PAPER,
        font={"color": _FONT},
    )
    if title:
        fig.update_layout(title=title)
    return fig


# ---------------------------------------------------------------------------
# Sparkline (tiny inline trend)
# ---------------------------------------------------------------------------
def sparkline(values: list[float] | pd.Series, *, color: str = "#3B82F6", height: int = 60) -> go.Figure | None:
    """Minimal axis-free sparkline for KPI cards."""
    if not _HAS_PLOTLY:
        return None
    series = list(values)
    if len(series) < 2:
        return None
    fig = go.Figure(
        go.Scatter(
            y=series,
            mode="lines",
            line={"color": color, "width": 2},
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.12)").replace("rgb", "rgba")
            if color.startswith("rgb")
            else "rgba(59,130,246,0.12)",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=height,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Accessibility: chart → data-table fallback
# ---------------------------------------------------------------------------
def render_with_table(
    fig: go.Figure | None,
    table_df: pd.DataFrame,
    *,
    caption: str = "",
    table_label: str = "View data table",
    key: str | None = None,
) -> None:
    """Render a chart plus an expandable data-table fallback for screen readers.

    Satisfies WCAG: every chart has a real (non-image) table of its values.
    """
    if not _HAS_ST:
        return
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=key)
    else:
        st.info("Not enough data to render this chart.", icon="📊")
    if caption:
        st.caption(caption)
    if not table_df.empty:
        with st.expander(f"♿ {table_label}", expanded=False):
            st.dataframe(table_df, use_container_width=True, hide_index=True)
