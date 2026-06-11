"""Phase E Visualizations: Time Series Decomposition (16 Charts).

Renders all Phase E visualizations:
1. 4-panel time series decomposition (observed, trend, seasonal, residual)
2-6. Borough-specific 4-panel decompositions
7-16. Supporting visualizations (forecasting, seasonal strength, trend analysis, etc.)

Data source: app_queries.v_phase_e_decomposition
All charts include summary statistics below.
"""
import logging
from typing import Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from socrata_toolkit.motherduck.connector import MotherDuckConnection

from .statistics_display import StatisticsPanel

logger = logging.getLogger(__name__)


class PhaseEVisualizations:
    """Renders all 16 Phase E visualizations (time series decomposition).

    Attributes:
        conn: MotherDuckConnection for querying app_queries.v_phase_e_decomposition
        data: DataFrame from serving view
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize Phase E visualizations.

        Args:
            connection: MotherDuckConnection instance
        """
        self.conn = connection
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from app_queries.v_phase_e_decomposition.

        Returns:
            DataFrame with columns: date, borough, violation_count, trend_value,
                                    seasonal_value, residual_value, forecast_next_period,
                                    analytics_timestamp

        Raises:
            RuntimeError: If query fails
        """
        query = "SELECT * FROM app_queries.v_phase_e_decomposition ORDER BY date DESC, borough"
        self.data = self.conn.fetch_dataframe(query)
        if self.data.empty:
            raise RuntimeError(
                "No data in app_queries.v_phase_e_decomposition. "
                "Run Phase 1 (MotherDuck infrastructure) first."
            )
        self.data["date"] = pd.to_datetime(self.data["date"])
        logger.info(f"Fetched {len(self.data)} rows from Phase E view")
        return self.data

    def render_main_4panel_decomposition(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render main 4-panel time series decomposition (all boroughs aggregated).

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Aggregate across all boroughs
        agg_data = (
            self.data.groupby("date")
            .agg({
                "violation_count": "sum",
                "trend_value": "mean",
                "seasonal_value": "mean",
                "residual_value": "mean",
            })
            .reset_index()
            .sort_values("date")
        )

        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            subplot_titles=(
                "Observed Violations",
                "Trend Component",
                "Seasonal Component",
                "Residual Component",
            ),
            vertical_spacing=0.08,
        )

        # Observed
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["violation_count"],
                name="Observed",
                line=dict(color="blue", width=2),
                hovertemplate="Date: %{x}<br>Violations: %{y:.0f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Trend
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["trend_value"],
                name="Trend",
                line=dict(color="red", width=2),
                hovertemplate="Date: %{x}<br>Trend: %{y:.2f}<extra></extra>",
            ),
            row=2,
            col=1,
        )

        # Seasonal
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["seasonal_value"],
                name="Seasonal",
                line=dict(color="green", width=2),
                fill="tozeroy",
                hovertemplate="Date: %{x}<br>Seasonal: %{y:.2f}<extra></extra>",
            ),
            row=3,
            col=1,
        )

        # Residual
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["residual_value"],
                name="Residual",
                line=dict(color="purple", width=1),
                mode="markers",
                hovertemplate="Date: %{x}<br>Residual: %{y:.2f}<extra></extra>",
            ),
            row=4,
            col=1,
        )

        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_yaxes(title_text="Trend", row=2, col=1)
        fig.update_yaxes(title_text="Seasonal", row=3, col=1)
        fig.update_yaxes(title_text="Residual", row=4, col=1)
        fig.update_xaxes(title_text="Date", row=4, col=1)

        fig.update_layout(
            title_text="Phase E: Time Series Decomposition",
            height=800,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="x unified",
            showlegend=True,
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=agg_data["violation_count"].mean(),
            min_value=agg_data["violation_count"].min(),
            max_value=agg_data["violation_count"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="STL Decomposition (Seasonal-Trend)",
            confidence_level="95%",
            additional_stats={
                "Date Range": f"{agg_data['date'].min().date()} to {agg_data['date'].max().date()}",
                "Trend Slope": f"{(agg_data['trend_value'].iloc[-1] - agg_data['trend_value'].iloc[0]):.2f}",
                "Avg Seasonal": f"{agg_data['seasonal_value'].mean():.2f}",
            },
        )

        return fig, stats

    def render_borough_4panel_decomposition(self, borough: str) -> Tuple[go.Figure, StatisticsPanel]:
        """Render 4-panel decomposition for a specific borough.

        Args:
            borough: Borough code (MN, BK, BX, QN, SI)

        Returns:
            Tuple of (figure, statistics)

        Raises:
            ValueError: If borough not found in data
        """
        if self.data is None:
            self.fetch_data()

        borough_data = self.data[self.data["borough"] == borough].sort_values("date")
        if borough_data.empty:
            raise ValueError(f"Borough {borough} not found in data")

        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            subplot_titles=(
                "Observed",
                "Trend",
                "Seasonal",
                "Residual",
            ),
            vertical_spacing=0.08,
        )

        fig.add_trace(
            go.Scatter(
                x=borough_data["date"],
                y=borough_data["violation_count"],
                name="Observed",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=borough_data["date"],
                y=borough_data["trend_value"],
                name="Trend",
                line=dict(color="red", width=2),
            ),
            row=2,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=borough_data["date"],
                y=borough_data["seasonal_value"],
                name="Seasonal",
                line=dict(color="green", width=2),
                fill="tozeroy",
            ),
            row=3,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=borough_data["date"],
                y=borough_data["residual_value"],
                name="Residual",
                line=dict(color="purple", width=1),
                mode="markers",
            ),
            row=4,
            col=1,
        )

        fig.update_layout(
            title_text=f"Phase E: {borough} Time Series Decomposition",
            height=700,
            font={"family": "Arial, sans-serif", "size": 10},
        )

        stats = StatisticsPanel(
            record_count=len(borough_data),
            mean_value=borough_data["violation_count"].mean(),
            min_value=borough_data["violation_count"].min(),
            max_value=borough_data["violation_count"].max(),
            last_timestamp=pd.to_datetime(borough_data["analytics_timestamp"].iloc[0]),
            calculation_method=f"STL Decomposition for {borough}",
            confidence_level="95%",
        )

        return fig, stats

    def render_forecast_chart(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render forecast chart with confidence bands.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Aggregate across boroughs
        agg_data = (
            self.data.groupby("date")
            .agg({
                "violation_count": "sum",
                "forecast_next_period": "mean",
            })
            .reset_index()
            .sort_values("date")
        )

        # Calculate confidence bands
        rolling_std = agg_data["violation_count"].rolling(window=7).std()
        agg_data["ci_upper"] = agg_data["forecast_next_period"] + (1.96 * rolling_std.fillna(rolling_std.mean()))
        agg_data["ci_lower"] = agg_data["forecast_next_period"] - (1.96 * rolling_std.fillna(rolling_std.mean()))

        fig = go.Figure()

        # Add observed data
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["violation_count"],
                name="Observed",
                line=dict(color="blue", width=2),
            )
        )

        # Add forecast
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["forecast_next_period"],
                name="Forecast",
                line=dict(color="red", dash="dash", width=2),
            )
        )

        # Add confidence bands
        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["ci_upper"],
                fill=None,
                mode="lines",
                name="Upper CI",
                line=dict(width=0),
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["ci_lower"],
                fill="tonexty",
                mode="lines",
                name="95% CI",
                line=dict(width=0),
                fillcolor="rgba(255, 0, 0, 0.2)",
            )
        )

        fig.update_layout(
            title="Phase E: Violation Forecast with 95% Confidence Interval",
            xaxis_title="Date",
            yaxis_title="Violation Count",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="x unified",
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=agg_data["forecast_next_period"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Time Series Forecasting (ARIMA-like)",
            confidence_level="95%",
        )

        return fig, stats

    def render_seasonal_strength_gauge(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render gauge showing seasonal strength.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Calculate seasonal strength (variance of seasonal / variance of observed)
        seasonal_var = self.data["seasonal_value"].var()
        observed_var = self.data["violation_count"].var()

        seasonal_strength = min(
            100 * (seasonal_var / (seasonal_var + self.data["residual_value"].var()))
            if (seasonal_var + self.data["residual_value"].var()) > 0
            else 0,
            100
        )

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number",
                    value=seasonal_strength,
                    title={"text": "Seasonal Strength"},
                    number={"suffix": "%"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "darkblue"},
                        "steps": [
                            {"range": [0, 33], "color": "lightgreen"},
                            {"range": [33, 66], "color": "lightyellow"},
                            {"range": [66, 100], "color": "lightcoral"},
                        ],
                    },
                )
            ]
        )

        fig.update_layout(
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=seasonal_strength,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Seasonal Strength (STL)",
            confidence_level="95%",
        )

        return fig, stats

    def render_trend_analysis(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render trend analysis chart.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        agg_data = (
            self.data.groupby("date")
            .agg({"trend_value": "mean"})
            .reset_index()
            .sort_values("date")
        )

        # Calculate trend slope
        x = range(len(agg_data))
        y = agg_data["trend_value"].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        trend_line = p(x)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["trend_value"],
                name="Trend Component",
                line=dict(color="blue", width=2),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=trend_line,
                name="Linear Fit",
                line=dict(color="red", dash="dash", width=2),
            )
        )

        fig.update_layout(
            title="Phase E: Trend Analysis",
            xaxis_title="Date",
            yaxis_title="Trend Value",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="x unified",
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=agg_data["trend_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Linear Trend Estimation",
            confidence_level="95%",
            additional_stats={
                "Slope": f"{z[0]:.4f}",
                "Intercept": f"{z[1]:.2f}",
            },
        )

        return fig, stats

    def render_all_phase_e_charts(self) -> dict:
        """Render all 16 Phase E visualizations.

        Returns:
            Dictionary mapping chart names to (figure, statistics) tuples
        """
        self.fetch_data()

        charts = {
            "main_4panel_decomposition": self.render_main_4panel_decomposition(),
            "borough_decomposition_mn": self.render_borough_4panel_decomposition("MN"),
            "borough_decomposition_bk": self.render_borough_4panel_decomposition("BK"),
            "borough_decomposition_bx": self.render_borough_4panel_decomposition("BX"),
            "borough_decomposition_qn": self.render_borough_4panel_decomposition("QN"),
            "borough_decomposition_si": self.render_borough_4panel_decomposition("SI"),
            "forecast_chart": self.render_forecast_chart(),
            "seasonal_strength_gauge": self.render_seasonal_strength_gauge(),
            "trend_analysis": self.render_trend_analysis(),
            "residual_acf": self._render_residual_acf(),
            "seasonal_subseries": self._render_seasonal_subseries(),
            "forecast_accuracy": self._render_forecast_accuracy(),
            "borough_trend_comparison": self._render_borough_trend_comparison(),
            "violation_volatility": self._render_violation_volatility(),
            "forecast_vs_actual": self._render_forecast_vs_actual(),
            "seasonal_pattern_heatmap": self._render_seasonal_pattern_heatmap(),
        }

        logger.info(f"Rendered {len(charts)} Phase E visualizations")
        return charts

    def _render_residual_acf(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render residual autocorrelation function.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        agg_data = (
            self.data.groupby("date")
            .agg({"residual_value": "mean"})
            .reset_index()
            .sort_values("date")
        )

        # Simple ACF calculation (lag 1-15)
        acf_values = [
            agg_data["residual_value"].autocorr(lag=i)
            for i in range(1, 16)
        ]

        fig = go.Figure(
            data=go.Bar(
                x=list(range(1, 16)),
                y=acf_values,
                marker_color=[
                    "red" if abs(v) > 0.196 else "blue"
                    for v in acf_values
                ],
            )
        )

        fig.add_hline(y=0.196, line_dash="dash", line_color="red", annotation_text="95% CI")
        fig.add_hline(y=-0.196, line_dash="dash", line_color="red")

        fig.update_layout(
            title="Phase E: Residual Autocorrelation Function",
            xaxis_title="Lag",
            yaxis_title="ACF",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=self.data["residual_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Autocorrelation Function (ACF)",
            confidence_level="95%",
        )

        return fig, stats

    def _render_seasonal_subseries(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render seasonal subseries plot.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Extract day of week or month patterns
        self.data["period"] = self.data["date"].dt.dayofweek

        fig = go.Figure()
        for period in sorted(self.data["period"].unique()):
            period_data = self.data[self.data["period"] == period]
            fig.add_trace(
                go.Box(
                    y=period_data["seasonal_value"],
                    name=f"Period {period}",
                    boxmean="sd",
                )
            )

        fig.update_layout(
            title="Phase E: Seasonal Subseries by Period",
            yaxis_title="Seasonal Component",
            xaxis_title="Period",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["seasonal_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Seasonal Subseries Analysis",
            confidence_level="95%",
        )

        return fig, stats

    def _render_forecast_accuracy(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render forecast accuracy metrics.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        agg_data = (
            self.data.groupby("date")
            .agg({
                "violation_count": "sum",
                "forecast_next_period": "mean",
            })
            .reset_index()
            .sort_values("date")
        )

        # Calculate MAPE
        agg_data["error"] = (
            (agg_data["violation_count"] - agg_data["forecast_next_period"]).abs()
            / agg_data["violation_count"]
        ).fillna(0)

        fig = go.Figure(
            data=go.Bar(
                x=agg_data["date"],
                y=agg_data["error"] * 100,
                marker_color=[
                    "green" if e < 0.1 else "orange" if e < 0.2 else "red"
                    for e in agg_data["error"]
                ],
            )
        )

        fig.update_layout(
            title="Phase E: Forecast Error (MAPE %)",
            xaxis_title="Date",
            yaxis_title="Mean Absolute Percentage Error",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=(agg_data["error"] * 100).mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="MAPE Calculation",
            confidence_level="95%",
        )

        return fig, stats

    def _render_borough_trend_comparison(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render comparison of trends across boroughs.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure()
        for borough in self.data["borough"].unique():
            borough_data = self.data[self.data["borough"] == borough].sort_values("date")
            fig.add_trace(
                go.Scatter(
                    x=borough_data["date"],
                    y=borough_data["trend_value"],
                    name=borough,
                    mode="lines",
                )
            )

        fig.update_layout(
            title="Phase E: Trend Comparison Across Boroughs",
            xaxis_title="Date",
            yaxis_title="Trend Value",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="x unified",
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["trend_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Borough-Level Trend Comparison",
            confidence_level="95%",
        )

        return fig, stats

    def _render_violation_volatility(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render violation volatility over time.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        agg_data = (
            self.data.groupby("date")
            .agg({"violation_count": "sum"})
            .reset_index()
            .sort_values("date")
        )

        agg_data["volatility"] = agg_data["violation_count"].rolling(window=7).std()

        fig = go.Figure(
            data=go.Scatter(
                x=agg_data["date"],
                y=agg_data["volatility"],
                fill="tozeroy",
                name="Rolling Std Dev",
                line=dict(color="red"),
            )
        )

        fig.update_layout(
            title="Phase E: Violation Count Volatility (7-day rolling)",
            xaxis_title="Date",
            yaxis_title="Standard Deviation",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=agg_data["volatility"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Rolling Standard Deviation",
            confidence_level="95%",
        )

        return fig, stats

    def _render_forecast_vs_actual(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render forecast vs actual comparison.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        agg_data = (
            self.data.groupby("date")
            .agg({
                "violation_count": "sum",
                "forecast_next_period": "mean",
            })
            .reset_index()
            .sort_values("date")
            .tail(60)  # Last 60 days
        )

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=agg_data["date"],
                y=agg_data["violation_count"],
                name="Actual",
                marker_color="blue",
                opacity=0.7,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=agg_data["date"],
                y=agg_data["forecast_next_period"],
                name="Forecast",
                line=dict(color="red", width=2, dash="dash"),
            )
        )

        fig.update_layout(
            title="Phase E: Forecast vs Actual (Last 60 Days)",
            xaxis_title="Date",
            yaxis_title="Violation Count",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="x unified",
            barmode="overlay",
        )

        stats = StatisticsPanel(
            record_count=len(agg_data),
            mean_value=agg_data["violation_count"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Forecast Comparison",
            confidence_level="95%",
        )

        return fig, stats

    def _render_seasonal_pattern_heatmap(self) -> Tuple[go.Figure, StatisticsPanel]:
        """Render heatmap of seasonal patterns (day of week × week).

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        self.data["day_of_week"] = self.data["date"].dt.dayofweek
        self.data["week_of_year"] = self.data["date"].dt.isocalendar().week

        heatmap_data = (
            self.data.pivot_table(
                values="seasonal_value",
                index="day_of_week",
                columns="week_of_year",
                aggfunc="mean",
            )
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                colorscale="RdBu",
                colorbar=dict(title="Seasonal"),
            )
        )

        fig.update_layout(
            title="Phase E: Seasonal Pattern Heatmap (Day of Week × Week)",
            xaxis_title="Week of Year",
            yaxis_title="Day of Week",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["seasonal_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Seasonal Pattern Heatmap",
            confidence_level="95%",
        )

        return fig, stats


import numpy as np
