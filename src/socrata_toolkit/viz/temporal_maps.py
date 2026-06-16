"""Geospatial Heatmap with Temporal Animation — Month-over-Month Trends.

Visualizes where sidewalk deterioration is accelerating using animated choropleth maps,
hot-block timelines, and month-over-month change heatmaps. Supports 12-24 month trends
by community board.

Example::

    from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer
    import pandas as pd

    df = pd.DataFrame({
        'date': pd.date_range('2025-01', periods=12, freq='MS'),
        'community_board': [201] * 12,
        'borough': ['MANHATTAN'] * 12,
        'violation_count': range(10, 22),
        'latitude': [40.715] * 12,
        'longitude': [-73.980] * 12,
    })

    viz = TemporalGeospatialVisualizer(df)
    fig = viz.plot_hot_blocks_timeline(top_k=10)
    fig.show()
"""

from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = [
    "TemporalGeospatialVisualizer",
    "bucket_temporal_data",
    "compute_month_over_month_change",
]

def _get_plotly():
    """Lazy import plotly."""
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        return go, px
    except ImportError as exc:
        raise ImportError("Install plotly: pip install plotly") from exc

def bucket_temporal_data(
    df: pd.DataFrame,
    period: str = "month",
    cb_area_km2: float = 15.0,
) -> pd.DataFrame:
    """Aggregate violations/inspections by community_board and time period.

    Args:
        df: DataFrame with columns:
            - date, community_board, borough, violation_count (or violations)
            - latitude, longitude (optional)
        period: Aggregation period ("month", "week", "quarter")
        cb_area_km2: Average community board area in km² (default 15 for NYC)

    Returns:
        Aggregated DataFrame with:
        - year_month, community_board, borough, violation_count, violation_density
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Create period column
    if period == "month":
        df["period"] = df["date"].dt.to_period("M")
    elif period == "week":
        df["period"] = df["date"].dt.to_period("W")
    elif period == "quarter":
        df["period"] = df["date"].dt.to_period("Q")
    else:
        df["period"] = df["date"].dt.to_period("M")

    # Aggregate
    agg_dict = {
        "violation_count": "sum",
    }

    # Add optional columns if they exist
    if "latitude" in df.columns:
        agg_dict["latitude"] = "mean"
    if "longitude" in df.columns:
        agg_dict["longitude"] = "mean"
    if "repair_cost" in df.columns:
        agg_dict["repair_cost"] = "sum"
    if "inspections" in df.columns:
        agg_dict["inspections"] = "sum"

    df_agg = df.groupby(["period", "community_board", "borough"]).agg(agg_dict).reset_index()

    # Compute density
    df_agg["violation_density"] = df_agg["violation_count"] / cb_area_km2

    # Convert period to string for serialization
    df_agg["year_month"] = df_agg["period"].astype(str)

    return df_agg[
        ["year_month", "community_board", "borough", "violation_count", "violation_density"]
        + [col for col in ["latitude", "longitude", "repair_cost", "inspections"] if col in df_agg.columns]
    ]

def compute_month_over_month_change(df_agg: pd.DataFrame) -> pd.DataFrame:
    """Calculate percentage change in violation_density from month N-1 to N.

    Args:
        df_agg: Aggregated DataFrame (output of bucket_temporal_data)

    Returns:
        DataFrame with additional column:
        - density_pct_change: Percent change from prior month
    """
    df_agg = df_agg.sort_values(["community_board", "year_month"]).copy()
    df_agg["density_pct_change"] = (
        df_agg.groupby("community_board")["violation_density"].pct_change() * 100
    )

    return df_agg

def identify_hot_blocks(
    df_agg: pd.DataFrame,
    top_k: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    """Identify top-k most problematic community boards per month.

    Args:
        df_agg: Aggregated DataFrame
        top_k: Number of top blocks to identify per month

    Returns:
        Dict mapping month (YYYY-MM) to list of top-k dicts:
        {month: [{"community_board": 201, "violation_density": 8.5, "borough": "MANHATTAN"}, ...]}
    """
    hot_blocks = {}

    for month in sorted(df_agg["year_month"].unique()):
        month_data = (
            df_agg[df_agg["year_month"] == month]
            .nlargest(top_k, "violation_density")
            .reset_index(drop=True)
        )

        hot_blocks[month] = [
            {
                "community_board": row["community_board"],
                "violation_density": float(row["violation_density"]),
                "violation_count": int(row["violation_count"]),
                "borough": row["borough"],
            }
            for _, row in month_data.iterrows()
        ]

    return hot_blocks

class TemporalGeospatialVisualizer:
    """Create temporal geospatial visualizations.

    Attributes:
        df: Input DataFrame with temporal and geospatial data
        df_agg: Aggregated data by period
        hot_blocks: Top-k problematic areas per month
    """

    def __init__(
        self,
        df: pd.DataFrame,
        period: str = "month",
        cb_area_km2: float = 15.0,
    ):
        """Initialize visualizer with data.

        Args:
            df: DataFrame with date, community_board, borough, violation_count
            period: Aggregation period ("month", "week", "quarter")
            cb_area_km2: Community board area for density computation
        """
        self.df = df.copy()
        self.period = period
        self.cb_area_km2 = cb_area_km2

        # Aggregate and compute metrics
        self.df_agg = bucket_temporal_data(df, period=period, cb_area_km2=cb_area_km2)
        self.df_agg = compute_month_over_month_change(self.df_agg)
        self.hot_blocks = identify_hot_blocks(self.df_agg)

    def plot_hot_blocks_timeline(self, top_k: int = 10) -> Any:
        """Create animated bar chart of top-k hot blocks over time.

        Args:
            top_k: Number of top blocks to show per month

        Returns:
            Plotly Figure (animated bar chart)
        """
        go, px = _get_plotly()

        # Prepare data for animation
        frames_data = []
        months = sorted(self.df_agg["year_month"].unique())

        for month in months:
            month_data = (
                self.df_agg[self.df_agg["year_month"] == month]
                .nlargest(top_k, "violation_density")
                .sort_values("violation_density", ascending=True)
            )

            frames_data.append({
                "month": month,
                "data": month_data.copy(),
            })

        # Create initial figure (first month)
        if frames_data:
            initial_data = frames_data[0]["data"]
            fig = go.Figure(
                data=[
                    go.Bar(
                        y=[f"CB {int(cb)}" for cb in initial_data["community_board"]],
                        x=initial_data["violation_density"],
                        orientation="h",
                        marker=dict(
                            color=initial_data["violation_density"],
                            colorscale="Reds",
                        ),
                        hovertemplate=(
                            "<b>Community Board %{y}</b><br>"
                            "Violation Density: %{x:.2f}/km²<extra></extra>"
                        ),
                    )
                ]
            )

            # Add frames for animation
            frames = []
            for frame_data in frames_data:
                month_df = frame_data["data"]
                frames.append(
                    go.Frame(
                        data=[
                            go.Bar(
                                y=[f"CB {int(cb)}" for cb in month_df["community_board"]],
                                x=month_df["violation_density"],
                                orientation="h",
                                marker=dict(
                                    color=month_df["violation_density"],
                                    colorscale="Reds",
                                ),
                            )
                        ],
                        name=frame_data["month"],
                    )
                )

            fig.frames = frames

            # Update layout with animation controls
            fig.update_layout(
                title=f"Top {top_k} Hot Blocks Over Time",
                xaxis_title="Violation Density (per km²)",
                yaxis_title="Community Board",
                height=600,
                hovermode="closest",
                updatemenus=[
                    {
                        "type": "buttons",
                        "showactive": False,
                        "buttons": [
                            {
                                "label": "Play",
                                "method": "animate",
                                "args": [None, {"frame": {"duration": 500, "redraw": True}}],
                            },
                            {
                                "label": "Pause",
                                "method": "animate",
                                "args": [
                                    [None],
                                    {
                                        "frame": {"duration": 0, "redraw": True},
                                        "mode": "immediate",
                                        "transition": {"duration": 0},
                                    },
                                ],
                            },
                        ],
                    }
                ],
                sliders=[
                    {
                        "active": 0,
                        "steps": [
                            {
                                "args": [[f.name], {"frame": {"duration": 300, "redraw": True}}],
                                "label": f.name,
                                "method": "animate",
                            }
                            for f in frames
                        ],
                    }
                ],
            )

        else:
            fig = go.Figure()
            fig.add_annotation(text="No data available")

        return fig

    def plot_month_over_month_heatmap(self) -> Any:
        """Create heatmap of month-over-month percent change in violation density.

        Returns:
            Plotly Figure (heatmap)
        """
        go, _ = _get_plotly()

        # Pivot: rows=CB, cols=month, values=pct_change
        pivot_data = self.df_agg.pivot_table(
            index="community_board",
            columns="year_month",
            values="density_pct_change",
            aggfunc="mean",
        )

        # Sort by max change
        pivot_data = pivot_data.loc[pivot_data.max(axis=1).sort_values(ascending=False).index]

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=[f"CB {int(cb)}" for cb in pivot_data.index],
                colorscale="RdBu",
                zmid=0,
                hovertemplate=(
                    "<b>Community Board %{y}</b><br>"
                    "Month: %{x}<br>"
                    "Percent Change: %{z:.1f}%<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            title="Month-over-Month Change in Violation Density (%)",
            xaxis_title="Month",
            yaxis_title="Community Board",
            height=600,
        )

        return fig

    def plot_borough_summary(self) -> Any:
        """Create small multiples borough-level summary (violin plots by month).

        Returns:
            Plotly Figure (small multiples)
        """
        go, px = _get_plotly()

        boroughs = sorted(self.df_agg["borough"].unique())
        months = sorted(self.df_agg["year_month"].unique())

        if len(months) > 12:
            # Sample months if too many
            months = months[::len(months) // 12]

        # Create subplots
        from plotly.subplots import make_subplots

        n_rows = (len(boroughs) + 1) // 2
        fig = make_subplots(
            rows=n_rows,
            cols=2,
            subplot_titles=boroughs,
            specs=[[{"type": "box"} for _ in range(2)] for _ in range(n_rows)],
        )

        for idx, borough in enumerate(boroughs):
            row = (idx // 2) + 1
            col = (idx % 2) + 1

            borough_data = self.df_agg[self.df_agg["borough"] == borough]

            for month in months:
                month_data = borough_data[borough_data["year_month"] == month]
                if len(month_data) > 0:
                    fig.add_trace(
                        go.Box(
                            y=month_data["violation_density"],
                            name=month,
                            boxmean="sd",
                        ),
                        row=row,
                        col=col,
                    )

        fig.update_layout(height=400 * n_rows, title_text="Violation Density Distribution by Borough and Month")

        return fig

    def get_hot_blocks_data(self) -> dict[str, list[dict[str, Any]]]:
        """Get hot blocks data for downstream use.

        Returns:
            Dict mapping month to list of top problematic areas
        """
        return self.hot_blocks

    def get_aggregated_data(self) -> pd.DataFrame:
        """Get aggregated time-series data.

        Returns:
            DataFrame with temporal aggregates
        """
        return self.df_agg
