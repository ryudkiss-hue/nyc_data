"""Visualization Components for Clustering Diagnostics.

Interactive Plotly visualizations: elbow curve, silhouette plot, quality metrics heatmap,
and cluster profiles table.

Example::

    from socrata_toolkit.viz.clustering_viz import plot_elbow_curve, plot_silhouette
    from socrata_toolkit.analysis.clustering_diagnostics import ClusteringDiagnostics
    import pandas as pd

    df = pd.DataFrame({
        'violation_count': [5, 12, 3, 8],
        'repair_cost': [1000, 4500, 800, 2200],
    })

    diag = ClusteringDiagnostics(df)
    results = diag.diagnose(max_k=8)

    fig_elbow = plot_elbow_curve(results)
    fig_elbow.show()
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = [
    "plot_elbow_curve",
    "plot_silhouette",
    "plot_quality_metrics_heatmap",
    "plot_cluster_profiles",
]


def _get_plotly():
    """Lazy import plotly."""
    try:
        import plotly.graph_objects as go

        return go
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc


def plot_elbow_curve(results: dict[str, Any]) -> Any:
    """Plot elbow curve with optimal k annotation.

    Args:
        results: Output dict from ClusteringDiagnostics.diagnose()
                Expected keys: elbow_curve_data, optimal_k

    Returns:
        Plotly Figure (elbow curve)
    """
    go = _get_plotly()

    elbow_data = results.get("elbow_curve_data", [])
    optimal_k = results.get("optimal_k", 3)

    if not elbow_data:
        fig = go.Figure()
        fig.add_annotation(text="No elbow data available")
        return fig

    k_values = [d["k"] for d in elbow_data]
    inertias = [d["inertia"] for d in elbow_data]

    fig = go.Figure()

    # Main curve
    fig.add_trace(
        go.Scatter(
            x=k_values,
            y=inertias,
            mode="lines+markers",
            name="Inertia",
            line=dict(color="#0D6EFD", width=3),
            marker=dict(size=8),
            hovertemplate="<b>k=%{x}</b><br>Inertia=%{y:.2f}<extra></extra>",
        )
    )

    # Mark optimal k
    optimal_inertia = next((d["inertia"] for d in elbow_data if d["k"] == optimal_k), None)
    if optimal_inertia is not None:
        fig.add_trace(
            go.Scatter(
                x=[optimal_k],
                y=[optimal_inertia],
                mode="markers",
                name="Optimal k",
                marker=dict(size=15, color="red", symbol="star"),
                hovertemplate=f"<b>Optimal k={optimal_k}</b><br>Inertia={optimal_inertia:.2f}<extra></extra>",
            )
        )

        # Add vertical line at optimal k
        fig.add_vline(
            x=optimal_k,
            line_dash="dash",
            line_color="red",
            annotation_text=f"k={optimal_k}",
            annotation_position="top right",
        )

    fig.update_layout(
        title="Elbow Curve - Optimal Cluster Count Detection",
        xaxis_title="Number of Clusters (k)",
        yaxis_title="Inertia",
        hovermode="closest",
        template="plotly_white",
        height=500,
    )

    return fig


def plot_silhouette(results: dict[str, Any], k: int | None = None) -> Any:
    """Plot silhouette coefficients as horizontal bars.

    Args:
        results: Output dict from ClusteringDiagnostics.diagnose()
                Expected keys: labels, k_range, silhouette_scores (mean scores per k)
        k: Specific k to visualize (default uses optimal_k)

    Returns:
        Plotly Figure (silhouette plot)
    """
    import numpy as np

    go = _get_plotly()

    # Get k values and their mean silhouette scores
    k_range = results.get("k_range", [])
    mean_silhouette_scores = results.get("silhouette_scores", [])

    if not k_range or not mean_silhouette_scores:
        fig = go.Figure()
        fig.add_annotation(text="No silhouette data available")
        return fig

    # Create bar chart of mean silhouette score per k
    fig = go.Figure()

    colors = [
        "#0D6EFD",
        "#6610F2",
        "#D63384",
        "#198754",
        "#FD7E14",
        "#0DCAF0",
        "#6C757D",
    ]

    marker_colors = [colors[i % len(colors)] for i in range(len(k_range))]

    fig.add_trace(
        go.Bar(
            x=k_range,
            y=mean_silhouette_scores,
            marker=dict(
                color=marker_colors,
            ),
            hovertemplate="<b>k=%{x}</b><br>Mean Silhouette Score: %{y:.3f}<extra></extra>",
        )
    )

    # Mark optimal k
    optimal_k = results.get("optimal_k", k_range[0])
    if optimal_k in k_range:
        optimal_score = mean_silhouette_scores[k_range.index(optimal_k)]
        fig.add_vline(
            x=optimal_k,
            line_dash="dash",
            line_color="red",
            annotation_text=f"k={optimal_k}",
            annotation_position="top right",
        )

    fig.update_layout(
        title="Silhouette Analysis - Mean Silhouette Score by k",
        xaxis_title="Number of Clusters (k)",
        yaxis_title="Mean Silhouette Coefficient",
        height=500,
        hovermode="closest",
        template="plotly_white",
    )

    return fig


def plot_quality_metrics_heatmap(results: dict[str, Any]) -> Any:
    """Plot quality metrics (Davies-Bouldin, Calinski-Harabasz) as heatmap.

    Args:
        results: Output dict from ClusteringDiagnostics.diagnose()
                Expected keys: quality_metrics_by_k, k_range

    Returns:
        Plotly Figure (heatmap)
    """
    import numpy as np

    go = _get_plotly()

    quality_by_k = results.get("quality_metrics_by_k", {})
    k_range = results.get("k_range", [])

    if not quality_by_k or not k_range:
        fig = go.Figure()
        fig.add_annotation(text="No quality metrics data available")
        return fig

    # Build matrix: rows = metrics, cols = k values
    metrics = ["davies_bouldin", "calinski_harabasz"]
    data_matrix = []

    for metric in metrics:
        row = []
        for k in k_range:
            val = quality_by_k.get(k, {}).get(metric, np.nan)
            row.append(float(val) if not np.isnan(val) else 0)
        data_matrix.append(row)

    # Normalize for visualization (0-1 scale)
    data_normalized = []
    for row in data_matrix:
        row_arr = np.array(row)
        if metric == "davies_bouldin":
            # Lower is better, so invert
            normalized = 1 - (row_arr - np.min(row_arr)) / (np.max(row_arr) - np.min(row_arr) + 1e-6)
        else:
            # Higher is better
            normalized = (row_arr - np.min(row_arr)) / (np.max(row_arr) - np.min(row_arr) + 1e-6)
        data_normalized.append(normalized.tolist())

    fig = go.Figure(
        data=go.Heatmap(
            z=data_normalized,
            x=[f"k={k}" for k in k_range],
            y=["Davies-Bouldin Index", "Calinski-Harabasz Index"],
            colorscale="Viridis",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "k=%{x}<br>"
                "Normalized Score: %{z:.3f}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="Cluster Quality Metrics by k",
        xaxis_title="Number of Clusters",
        yaxis_title="Quality Metric",
        height=300,
    )

    return fig


def plot_cluster_profiles(results: dict[str, Any]) -> Any:
    """Create table of cluster mean feature values.

    Args:
        results: Output dict from ClusteringDiagnostics.diagnose()
                Expected keys: cluster_profiles (DataFrame)

    Returns:
        Plotly Figure (table)
    """
    go = _get_plotly()

    cluster_profiles = results.get("cluster_profiles")

    if cluster_profiles is None or cluster_profiles.empty:
        fig = go.Figure()
        fig.add_annotation(text="No cluster profiles available")
        return fig

    # Round for display
    display_df = cluster_profiles.round(2)

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["Feature"] + list(display_df.columns),
                    fill_color="paleturquoise",
                    align="left",
                    font=dict(size=12),
                ),
                cells=dict(
                    values=[display_df.index] + [display_df[col] for col in display_df.columns],
                    fill_color="lavender",
                    align="left",
                    font=dict(size=11),
                ),
            )
        ]
    )

    fig.update_layout(
        title="Cluster Profiles (Mean Feature Values)",
        height=300 + len(display_df) * 20,
    )

    return fig
