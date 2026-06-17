"""Multi-dimensional and crossfilter-ready visualizations for NYC DOT SIM Division.

Covers charts that are absent from the existing library:
- Parallel coordinates  (multi-variate inspection profiling)
- Scatter plot matrix / SPLOM  (pairwise relationships across all numeric fields)
- Clustermap with hierarchical dendrograms  (community board / material similarity)
- Sankey / alluvial diagrams  (work-item state transitions, permit→inspection→violation flows)
- Radar / spider charts  (multi-metric borough comparison)
- Crossfilter-ready linked brush layout  (returns dict of figures bound by a shared filter col)

All functions return Plotly Figure objects unless noted otherwise.

Example::

    from socrata_toolkit.viz.advanced_multidim import (
        parallel_coordinates,
        scatter_plot_matrix,
        clustermap,
        sankey_flow,
        radar_chart,
        crossfilter_layout,
    )

    import pandas as pd
    df = pd.read_csv("inspections.csv")

    fig_pc = parallel_coordinates(df,
        dimensions=["condition_score", "violation_count", "repair_cost", "age_years"],
        color_col="borough")
    fig_pc.write_html("parallel_coords.html")
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .units import get_unit_label


def _go():
    try:
        import plotly.graph_objects as go
        return go
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc


def _px():
    try:
        import plotly.express as px
        return px
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc


# ---------------------------------------------------------------------------
# Parallel Coordinates
# ---------------------------------------------------------------------------

def parallel_coordinates(
    df: pd.DataFrame,
    dimensions: list[str],
    color_col: str | None = None,
    color_continuous_scale: str = "Plasma",
    title: str | None = None,
) -> Any:
    """Parallel coordinates plot for multi-variate inspection profiling.

    Each vertical axis is one metric; each line is one row. Brushing each axis
    filters to the intersection — ideal for identifying high-violation, low-score
    blocks that are also high-cost.

    Args:
        df: Source DataFrame.
        dimensions: Numeric column names to display as axes.
        color_col: Column used to color lines (numeric or mapped to numeric).
        color_continuous_scale: Plotly colorscale name.
        title: Chart title.

    Returns:
        Plotly Figure with ``go.Parcoords``.
    """
    go = _go()
    tmp = df.copy()

    # Build dimension specs
    dim_specs = []
    for col in dimensions:
        if col not in tmp.columns:
            continue
        col_series = pd.to_numeric(tmp[col], errors="coerce")
        dim_specs.append(
            dict(
                label=get_unit_label(col),
                values=col_series.fillna(col_series.median()),
                range=[col_series.min(), col_series.max()],
            )
        )

    # Encode color
    if color_col and color_col in tmp.columns:
        if tmp[color_col].dtype == object:
            cats = tmp[color_col].astype("category")
            color_vals = cats.cat.codes.astype(float)
            colorscale = [
                [i / max(len(cats.cat.categories) - 1, 1), c]
                for i, c in enumerate(
                    ["#003366", "#D63384", "#198754", "#FD7E14", "#6610F2"]
                )
            ]
        else:
            color_vals = pd.to_numeric(tmp[color_col], errors="coerce").fillna(0)
            colorscale = color_continuous_scale
        line_dict = dict(color=color_vals, colorscale=colorscale, showscale=True)
    else:
        line_dict = dict(color="#003366")

    fig = go.Figure(
        go.Parcoords(dimensions=dim_specs, line=line_dict)
    )
    fig.update_layout(
        title=title or "Parallel Coordinates — Multi-Variate Inspection Profile",
        template="plotly_white",
        height=550,
    )
    return fig


# ---------------------------------------------------------------------------
# Scatter Plot Matrix (SPLOM)
# ---------------------------------------------------------------------------

def scatter_plot_matrix(
    df: pd.DataFrame,
    dimensions: list[str],
    color_col: str | None = None,
    sample_n: int = 2000,
    title: str | None = None,
) -> Any:
    """Scatter plot matrix (SPLOM) of all pairwise numeric relationships.

    Each off-diagonal cell is a scatter; diagonal cells show distributions.
    Useful for quickly spotting collinear metrics and outlier clusters.

    Args:
        df: Source DataFrame.
        dimensions: Numeric columns to cross-plot.
        color_col: Grouping column for color (e.g. borough).
        sample_n: Row cap to keep rendering fast.
        title: Chart title.

    Returns:
        Plotly Figure with ``px.scatter_matrix``.
    """
    px = _px()
    tmp = df[dimensions + ([color_col] if color_col and color_col in df.columns else [])].copy()
    tmp = tmp.sample(min(sample_n, len(tmp)), random_state=42)

    fig = px.scatter_matrix(
        tmp,
        dimensions=dimensions,
        color=color_col,
        labels={col: get_unit_label(col) for col in dimensions},
        title=title or "Scatter Plot Matrix — Pairwise Inspection Metrics",
        opacity=0.55,
    )
    fig.update_traces(diagonal_visible=True, showupperhalf=False)
    fig.update_layout(template="plotly_white", height=700)
    return fig


# ---------------------------------------------------------------------------
# Clustermap (hierarchical heatmap with dendrograms)
# ---------------------------------------------------------------------------

def clustermap(
    df: pd.DataFrame,
    row_key: str,
    value_cols: list[str],
    agg: str = "mean",
    colorscale: str = "RdYlGn",
    title: str | None = None,
) -> Any:
    """Hierarchical clustered heatmap (clustermap) with dendrograms.

    Aggregates ``value_cols`` per ``row_key``, then clusters both rows and
    columns via Ward linkage, surfacing groupings invisible in a flat heatmap.

    Args:
        df: Source DataFrame.
        row_key: Column whose distinct values become heatmap rows (e.g. "community_board").
        value_cols: Numeric columns to use as heatmap columns.
        agg: Aggregation function ("mean", "sum", "median").
        colorscale: Plotly colorscale name.
        title: Chart title.

    Returns:
        Plotly Figure (annotated Heatmap with Ward-ordered rows/cols).
    """
    from scipy.cluster.hierarchy import dendrogram, linkage
    from scipy.spatial.distance import pdist

    go = _go()

    # Aggregate
    pivot = (
        df.groupby(row_key)[value_cols]
        .agg(agg)
        .dropna(how="all")
    )

    # Standardise columns (z-score per column)
    pivot_z = (pivot - pivot.mean()) / (pivot.std().replace(0, 1))

    # Hierarchical clustering: rows
    row_link = linkage(pdist(pivot_z.fillna(0), metric="euclidean"), method="ward")
    row_order = dendrogram(row_link, no_plot=True)["leaves"]

    # Hierarchical clustering: columns
    col_link = linkage(pdist(pivot_z.fillna(0).T, metric="euclidean"), method="ward")
    col_order = dendrogram(col_link, no_plot=True)["leaves"]

    sorted_z = pivot_z.iloc[row_order, col_order]

    fig = go.Figure(
        go.Heatmap(
            z=sorted_z.values,
            x=[get_unit_label(c) for c in sorted_z.columns],
            y=sorted_z.index.astype(str).tolist(),
            colorscale=colorscale,
            colorbar=dict(title="Z-Score"),
            hovertemplate=(
                "<b>%{y}</b><br>%{x}<br>Z-score: %{z:.2f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=title or f"Clustermap — {row_key.replace('_', ' ').title()} × Metrics",
        xaxis_title="Metric",
        yaxis_title=row_key.replace("_", " ").title(),
        template="plotly_white",
        height=max(400, 20 * len(sorted_z)),
    )
    return fig


# ---------------------------------------------------------------------------
# Sankey / Alluvial — work-item state transitions
# ---------------------------------------------------------------------------

def sankey_flow(
    df: pd.DataFrame,
    source_col: str,
    target_col: str,
    value_col: str | None = None,
    top_n: int = 20,
    title: str | None = None,
) -> Any:
    """Sankey diagram for state transition or category-flow analysis.

    Visualises how units flow from ``source_col`` categories to ``target_col``
    categories (e.g. borough → inspection_status, material → violation_type).

    Args:
        df: Source DataFrame.
        source_col: Column for left-side nodes.
        target_col: Column for right-side nodes.
        value_col: Optional count column; if None, each row is counted once.
        top_n: Limit to top-N source→target pairs by flow volume.
        title: Chart title.

    Returns:
        Plotly Figure with ``go.Sankey``.
    """
    go = _go()

    if value_col and value_col in df.columns:
        flows = df.groupby([source_col, target_col])[value_col].sum().reset_index()
        flows.columns = ["source", "target", "value"]
    else:
        flows = df.groupby([source_col, target_col]).size().reset_index(name="value")
        flows.columns = ["source", "target", "value"]

    flows = flows.nlargest(top_n, "value")

    # Build node list (all unique labels)
    all_labels = pd.concat([flows["source"], flows["target"]]).unique().tolist()
    label_idx = {lbl: i for i, lbl in enumerate(all_labels)}

    colors = [
        "#003366", "#D63384", "#198754", "#FD7E14", "#6610F2",
        "#0D6EFD", "#20C997", "#FFC107", "#DC3545", "#17A2B8",
    ]
    node_colors = [colors[i % len(colors)] for i in range(len(all_labels))]

    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="#333", width=0.5),
                label=all_labels,
                color=node_colors,
            ),
            link=dict(
                source=[label_idx[s] for s in flows["source"]],
                target=[label_idx[t] for t in flows["target"]],
                value=flows["value"].tolist(),
                hovertemplate=(
                    "%{source.label} → %{target.label}<br>"
                    "Count: %{value:,.0f}<extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(
        title=title or f"Flow: {source_col.replace('_', ' ').title()} → {target_col.replace('_', ' ').title()}",
        template="plotly_white",
        height=500,
    )
    return fig


# ---------------------------------------------------------------------------
# Radar / Spider — multi-metric borough comparison
# ---------------------------------------------------------------------------

def radar_chart(
    df: pd.DataFrame,
    group_col: str,
    metric_cols: list[str],
    agg: str = "mean",
    normalize: bool = True,
    title: str | None = None,
) -> Any:
    """Radar (spider) chart for multi-metric comparison across groups.

    Each spoke is one metric; each polygon is one group (e.g. borough).
    Normalization scales all metrics to [0, 1] so different units compare fairly.

    Args:
        df: Source DataFrame.
        group_col: Column to define groups (e.g. "borough").
        metric_cols: Numeric metric columns as spokes.
        agg: Aggregation per group ("mean", "median", "sum").
        normalize: Scale each metric to [0, 1] across groups.
        title: Chart title.

    Returns:
        Plotly Figure with ``go.Scatterpolar`` traces.
    """
    go = _go()

    grouped = df.groupby(group_col)[metric_cols].agg(agg)

    if normalize:
        col_min = grouped.min()
        col_max = grouped.max()
        grouped = (grouped - col_min) / (col_max - col_min + 1e-9)

    BOROUGH_COLORS = {
        "MANHATTAN": "#0D6EFD",
        "BRONX": "#6610F2",
        "BROOKLYN": "#D63384",
        "QUEENS": "#198754",
        "STATEN ISLAND": "#FD7E14",
    }

    fig = go.Figure()
    spoke_labels = [get_unit_label(c) for c in metric_cols]

    for group, row in grouped.iterrows():
        values = row.tolist() + [row.iloc[0]]  # close the polygon
        labels = spoke_labels + [spoke_labels[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=labels,
                fill="toself",
                name=str(group),
                line_color=BOROUGH_COLORS.get(str(group).upper(), "#6C757D"),
                opacity=0.7,
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1] if normalize else None)),
        showlegend=True,
        title=title or f"Radar: {group_col.replace('_', ' ').title()} Multi-Metric Comparison",
        template="plotly_white",
        height=550,
    )
    return fig


# ---------------------------------------------------------------------------
# Crossfilter Layout — linked multi-chart panel
# ---------------------------------------------------------------------------

def crossfilter_layout(
    df: pd.DataFrame,
    filter_col: str,
    charts: list[dict],
) -> list[Any]:
    """Return a list of Plotly figures pre-filtered by ``filter_col`` categories.

    Each entry in ``charts`` is a dict with keys:
      - ``type``: one of "bar", "scatter", "histogram", "box", "violin"
      - ``x``, ``y``: column names
      - ``title`` (optional)

    In a Dash app, wire these figures to a single ``dcc.Dropdown`` that feeds
    a ``filter_col`` value; re-render by filtering df client-side via
    ``Patch()`` or a standard callback. For static export, returns one figure
    per (chart × filter_value) combination so every slice is pre-rendered.

    Returns:
        List of Plotly Figure objects in the order: [chart0_val0, chart0_val1, ...,
        chart1_val0, ...].
    """
    px = _px()

    filter_values = sorted(df[filter_col].dropna().unique())
    figs = []

    for fv in filter_values:
        subset = df[df[filter_col] == fv]
        for chart_spec in charts:
            ctype = chart_spec.get("type", "bar")
            x, y = chart_spec.get("x"), chart_spec.get("y")
            chart_title = chart_spec.get("title", f"{ctype.title()} — {filter_col}={fv}")

            if ctype == "bar":
                fig = px.bar(subset, x=x, y=y, title=chart_title, template="plotly_white")
            elif ctype == "scatter":
                fig = px.scatter(subset, x=x, y=y, title=chart_title, template="plotly_white")
            elif ctype == "histogram":
                fig = px.histogram(subset, x=x, title=chart_title, template="plotly_white")
            elif ctype == "box":
                fig = px.box(subset, x=x, y=y, title=chart_title, template="plotly_white")
            elif ctype == "violin":
                fig = px.violin(subset, x=x, y=y, box=True, title=chart_title, template="plotly_white")
            else:
                fig = px.bar(subset, x=x, y=y, title=chart_title, template="plotly_white")

            figs.append(fig)

    return figs


# ---------------------------------------------------------------------------
# Funnel Chart — inspection → violation → dismissal pipeline
# ---------------------------------------------------------------------------

def inspection_funnel(
    stage_labels: list[str],
    stage_counts: list[int],
    title: str | None = None,
) -> Any:
    """Funnel chart for the SIM inspection pipeline stages.

    Args:
        stage_labels: Ordered stage names (wide-to-narrow), e.g.
            ["Inspections", "Violations Issued", "Reinspected", "Dismissed"].
        stage_counts: Corresponding counts per stage.
        title: Chart title.

    Returns:
        Plotly Figure with ``go.Funnel``.
    """
    go = _go()

    fig = go.Figure(
        go.Funnel(
            y=stage_labels,
            x=stage_counts,
            textinfo="value+percent initial",
            marker=dict(
                color=["#003366", "#0D6EFD", "#FD7E14", "#D63384"],
                line=dict(width=2, color="#fff"),
            ),
        )
    )
    fig.update_layout(
        title=title or "SIM Inspection Pipeline Funnel",
        template="plotly_white",
        height=450,
    )
    return fig


# ---------------------------------------------------------------------------
# Bubble Chart — 3-variable + size encoding
# ---------------------------------------------------------------------------

def bubble_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    size_col: str,
    color_col: str | None = None,
    hover_name_col: str | None = None,
    log_x: bool = False,
    log_y: bool = False,
    title: str | None = None,
) -> Any:
    """Bubble chart encoding four dimensions: x, y, size, color.

    Args:
        df: Source DataFrame.
        x_col, y_col: Axis columns.
        size_col: Numeric column for bubble size.
        color_col: Column for color encoding.
        hover_name_col: Column shown in hover tooltip header.
        log_x, log_y: Log-scale axes (useful for skewed cost distributions).
        title: Chart title.

    Returns:
        Plotly Figure.
    """
    px = _px()
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        size=size_col,
        color=color_col,
        hover_name=hover_name_col,
        size_max=60,
        log_x=log_x,
        log_y=log_y,
        labels={
            x_col: get_unit_label(x_col),
            y_col: get_unit_label(y_col),
            size_col: get_unit_label(size_col),
        },
        title=title or f"Bubble: {get_unit_label(x_col)} vs {get_unit_label(y_col)}",
        template="plotly_white",
    )
    fig.update_layout(height=550)
    return fig
