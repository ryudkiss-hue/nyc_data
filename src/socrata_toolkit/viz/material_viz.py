"""Visualization Components for Material Degradation Analysis.

Kaplan-Meier survival curves, cumulative hazard, material economics scatter, and log-rank test results.

Example::

    from socrata_toolkit.viz.material_viz import plot_km_curves, plot_material_economics
    from socrata_toolkit.analysis.material_analysis import MaterialDegradationAnalysis
    import pandas as pd

    df = pd.DataFrame({
        'material_type': ['concrete', 'asphalt'],
        'time_in_months': [156, 108],
        'event': [1, 1],
    })

    analysis = MaterialDegradationAnalysis(df)
    results = analysis.fit()

    fig_km = plot_km_curves(results['km_curves'])
    fig_km.show()
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = [
    "plot_km_curves",
    "plot_cumulative_hazard",
    "plot_material_economics",
    "plot_log_rank_results",
]


def _get_plotly():
    """Lazy import plotly."""
    try:
        import plotly.graph_objects as go

        return go
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc


def plot_km_curves(km_results: dict[str, dict[str, Any]]) -> Any:
    """Plot Kaplan-Meier survival curves with confidence bands.

    Args:
        km_results: Dict from MaterialDegradationAnalysis.fit()['km_curves']
                   Expected keys per material:
                   - time_points: list of time values
                   - survival_prob: list of survival probabilities
                   - ci_lower, ci_upper: confidence interval bounds
                   - median_survival_months: scalar
                   - n_at_risk, n_events: counts

    Returns:
        Plotly Figure (KM survival curves)
    """
    go = _get_plotly()

    color_palette = {
        "concrete": "#0D6EFD",
        "asphalt": "#FD7E14",
        "stone": "#198754",
        "other": "#6C757D",
    }

    fig = go.Figure()

    for material, km_data in km_results.items():
        time_points = km_data.get("time_points", [])
        survival_prob = km_data.get("survival_prob", [])
        ci_lower = km_data.get("ci_lower", [])
        ci_upper = km_data.get("ci_upper", [])
        median_time = km_data.get("median_survival_months", None)
        n_events = km_data.get("n_events", 0)

        color = color_palette.get(material, "#6C757D")

        # Add confidence band (filled area)
        if ci_upper and ci_lower:
            fig.add_trace(
                go.Scatter(
                    x=time_points + time_points[::-1],
                    y=ci_upper + ci_lower[::-1],
                    fill="toself",
                    fillcolor=color,
                    opacity=0.15,
                    line=dict(color="rgba(0,0,0,0)"),
                    hoverinfo="skip",
                    showlegend=False,
                    name=f"{material} (95% CI)",
                )
            )

        # Add main curve
        hover_text = [
            f"<b>{material.capitalize()}</b><br>"
            f"Time: {t:.0f} months<br>"
            f"Survival Prob: {s:.3f}<br>"
            f"95% CI: [{l:.3f}, {u:.3f}]<extra></extra>"
            for t, s, l, u in zip(time_points, survival_prob, ci_lower, ci_upper)
        ]

        fig.add_trace(
            go.Scatter(
                x=time_points,
                y=survival_prob,
                mode="lines",
                name=material.capitalize(),
                line=dict(color=color, width=3),
                hovertext=hover_text,
                hoverinfo="text",
            )
        )

        # Add median survival line
        if median_time and not pd.isna(median_time):
            fig.add_vline(
                x=median_time,
                line_dash="dot",
                line_color=color,
                annotation_text=f"{material}: {median_time:.0f} mo",
                annotation_position="top right",
            )

    # Add horizontal line at 50% survival
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title="Kaplan-Meier Survival Curves by Material Type",
        xaxis_title="Time (months)",
        yaxis_title="Survival Probability",
        yaxis=dict(range=[0, 1.05]),
        hovermode="x unified",
        template="plotly_white",
        height=500,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def plot_cumulative_hazard(cumulative_hazard: dict[str, dict[str, Any]]) -> Any:
    """Plot cumulative hazard function (Nelson-Aalen) by material.

    Args:
        cumulative_hazard: Dict from MaterialDegradationAnalysis.get_cumulative_hazard()
                          Keys: material names
                          Values: {"time_points": [...], "hazard": [...]}

    Returns:
        Plotly Figure (cumulative hazard curves)
    """
    go = _get_plotly()

    color_palette = {
        "concrete": "#0D6EFD",
        "asphalt": "#FD7E14",
        "stone": "#198754",
        "other": "#6C757D",
    }

    fig = go.Figure()

    for material, hazard_data in cumulative_hazard.items():
        time_points = hazard_data.get("time_points", [])
        hazard = hazard_data.get("hazard", [])

        color = color_palette.get(material, "#6C757D")

        fig.add_trace(
            go.Scatter(
                x=time_points,
                y=hazard,
                mode="lines",
                name=material.capitalize(),
                line=dict(color=color, width=3),
                hovertemplate=(
                    f"<b>{material.capitalize()}</b><br>"
                    "Time: %{x:.0f} months<br>"
                    "Cumulative Hazard: %{y:.3f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Cumulative Hazard Function by Material Type",
        xaxis_title="Time (months)",
        yaxis_title="Cumulative Hazard",
        hovermode="x unified",
        template="plotly_white",
        height=500,
    )

    return fig


def plot_material_economics(economics_df: pd.DataFrame) -> Any:
    """Create bubble chart of material cost vs lifespan.

    Args:
        economics_df: Output from MaterialDegradationAnalysis._compute_material_economics()
                      Index: material names
                      Columns: median_lifespan_years, 20_year_total_cost, etc.

    Returns:
        Plotly Figure (bubble chart)
    """
    go = _get_plotly()

    color_palette = {
        "concrete": "#0D6EFD",
        "asphalt": "#FD7E14",
        "stone": "#198754",
        "other": "#6C757D",
    }

    # Prepare data
    materials = economics_df.index.tolist()
    lifespan = economics_df["median_lifespan_years"].values
    cost_20yr = economics_df["20_year_total_cost"].values
    cost_per_year = economics_df["cost_per_year"].values

    colors = [color_palette.get(m, "#6C757D") for m in materials]

    fig = go.Figure(
        data=go.Scatter(
            x=lifespan,
            y=cost_20yr,
            mode="markers",
            marker=dict(
                size=[c / 5 for c in cost_per_year],  # Size = cost per year
                color=colors,
                line=dict(width=2, color="white"),
                opacity=0.7,
            ),
            text=[
                f"<b>{m.capitalize()}</b><br>"
                f"Median Lifespan: {l:.1f} years<br>"
                f"20-Year Total Cost: ${c:,.0f}<br>"
                f"Cost per Year: ${cp:,.0f}"
                for m, l, c, cp in zip(materials, lifespan, cost_20yr, cost_per_year)
            ],
            hovertemplate="%{text}<extra></extra>",
        )
    )

    # Add quadrant lines
    median_lifespan = lifespan.mean()
    median_cost = cost_20yr.mean()

    fig.add_vline(x=median_lifespan, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_hline(y=median_cost, line_dash="dash", line_color="gray", opacity=0.5)

    # Add quadrant labels
    fig.add_annotation(
        x=median_lifespan * 1.3,
        y=median_cost * 1.3,
        text="<b>High Cost<br>Long Lifespan</b>",
        showarrow=False,
        opacity=0.5,
        font=dict(size=10),
    )
    fig.add_annotation(
        x=median_lifespan * 0.7,
        y=median_cost * 1.3,
        text="<b>High Cost<br>Short Lifespan</b>",
        showarrow=False,
        opacity=0.5,
        font=dict(size=10),
    )
    fig.add_annotation(
        x=median_lifespan * 1.3,
        y=median_cost * 0.7,
        text="<b>Low Cost<br>Long Lifespan</b>",
        showarrow=False,
        opacity=0.5,
        font=dict(size=10),
    )
    fig.add_annotation(
        x=median_lifespan * 0.7,
        y=median_cost * 0.7,
        text="<b>Low Cost<br>Short Lifespan</b>",
        showarrow=False,
        opacity=0.5,
        font=dict(size=10),
    )

    fig.update_layout(
        title="Material Cost-Benefit Analysis: Lifespan vs Total Cost",
        xaxis_title="Median Lifespan (years)",
        yaxis_title="20-Year Total Cost ($)",
        hovermode="closest",
        template="plotly_white",
        height=500,
    )

    return fig


def plot_log_rank_results(log_rank_tests: dict[tuple[str, str], dict[str, Any]]) -> Any:
    """Create table of log-rank test results.

    Args:
        log_rank_tests: Output from MaterialDegradationAnalysis.fit()['log_rank_tests']
                       Keys: (material1, material2) tuples
                       Values: {p_value, significant, test_statistic}

    Returns:
        Plotly Figure (table)
    """
    go = _get_plotly()

    if not log_rank_tests:
        fig = go.Figure()
        fig.add_annotation(text="No log-rank test data available")
        return fig

    # Build table data
    comparisons = []
    p_values = []
    significance = []

    for (mat1, mat2), results in log_rank_tests.items():
        comparisons.append(f"{mat1} vs {mat2}")
        p_values.append(f"{results.get('p_value', 'N/A'):.4f}")
        sig = "Yes" if results.get("significant", False) else "No"
        significance.append(sig)

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["<b>Material Comparison</b>", "<b>P-Value</b>", "<b>Significant (α=0.05)</b>"],
                    fill_color="paleturquoise",
                    align="left",
                    font=dict(size=12),
                ),
                cells=dict(
                    values=[comparisons, p_values, significance],
                    fill_color=[
                        ["lavender"] * len(comparisons),
                        ["lavender"] * len(p_values),
                        [
                            "lightgreen" if s == "Yes" else "lightcoral"
                            for s in significance
                        ],
                    ],
                    align="left",
                    font=dict(size=11),
                ),
            )
        ]
    )

    fig.update_layout(
        title="Log-Rank Test Results: Material Survival Comparisons",
        height=200 + len(comparisons) * 30,
    )

    return fig
