"""Phase F Visualizations: Bootstrap CI & SLA Gauges (17 Charts).

Renders all Phase F visualizations:
1. Main SLA gauge with confidence bands
2-6. Borough-specific SLA gauges
7-17. Supporting visualizations (CI width, risk scoring, probability distribution, etc.)

Data source: app_queries.v_phase_f_bootstrap_ci
All charts include summary statistics below.
"""
import logging

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from socrata_toolkit.motherduck.connector import MotherDuckConnection

from .statistics_display import StatisticsPanel

logger = logging.getLogger(__name__)

class PhaseFVisualizations:
    """Renders all 17 Phase F visualizations (bootstrap CI & SLA gauges).

    Attributes:
        conn: MotherDuckConnection for querying app_queries.v_phase_f_bootstrap_ci
        data: DataFrame from serving view
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize Phase F visualizations.

        Args:
            connection: MotherDuckConnection instance
        """
        self.conn = connection
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from app_queries.v_phase_f_bootstrap_ci.

        Returns:
            DataFrame with columns: borough, point_estimate, ci_lower_95,
                                    ci_upper_95, interval_width, prob_meets_sla,
                                    risk_level, analytics_timestamp

        Raises:
            RuntimeError: If query fails
        """
        query = "SELECT * FROM app_queries.v_phase_f_bootstrap_ci ORDER BY borough"
        self.data = self.conn.fetch_dataframe(query)
        if self.data.empty:
            raise RuntimeError(
                "No data in app_queries.v_phase_f_bootstrap_ci. "
                "Run Phase 1 (MotherDuck infrastructure) first."
            )
        logger.info(f"Fetched {len(self.data)} rows from Phase F view")
        return self.data

    def render_main_sla_gauge(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render main SLA probability gauge (borough average).

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        avg_prob = self.data["prob_meets_sla"].mean() * 100

        # Determine gauge color based on SLA probability
        if avg_prob >= 90:
            gauge_color = "green"
            status = "SLA Met"
        elif avg_prob >= 75:
            gauge_color = "orange"
            status = "At Risk"
        else:
            gauge_color = "red"
            status = "SLA At Risk"

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number+delta",
                    value=avg_prob,
                    title={"text": "SLA Probability"},
                    number={"suffix": "%"},
                    delta={"reference": 90, "suffix": " from target"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": gauge_color},
                        "steps": [
                            {"range": [0, 50], "color": "lightcoral"},
                            {"range": [50, 75], "color": "lightyellow"},
                            {"range": [75, 90], "color": "lightblue"},
                            {"range": [90, 100], "color": "lightgreen"},
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": 90,
                        },
                    },
                )
            ]
        )

        fig.update_layout(
            title_text="Phase F: Service Level Agreement (SLA) Probability",
            height=500,
            font={"family": "Arial, sans-serif", "size": 12},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=avg_prob,
            min_value=self.data["prob_meets_sla"].min() * 100,
            max_value=self.data["prob_meets_sla"].max() * 100,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Bootstrap Confidence Interval (95%)",
            confidence_level="95%",
            additional_stats={"Status": status, "Target": "90%"},
        )

        return fig, stats

    def render_borough_sla_gauge(self, borough: str) -> tuple[go.Figure, StatisticsPanel]:
        """Render SLA gauge for a specific borough.

        Args:
            borough: Borough code (MN, BK, BX, QN, SI)

        Returns:
            Tuple of (figure, statistics)

        Raises:
            ValueError: If borough not found in data
        """
        if self.data is None:
            self.fetch_data()

        borough_data = self.data[self.data["borough"] == borough]
        if borough_data.empty:
            raise ValueError(f"Borough {borough} not found in data")

        row = borough_data.iloc[0]
        prob_sla = row["prob_meets_sla"] * 100
        risk_level = row["risk_level"]
        point_estimate = row["point_estimate"]
        ci_lower = row["ci_lower_95"]
        ci_upper = row["ci_upper_95"]

        color_map = {
            "HIGH": "green",
            "MEDIUM": "orange",
            "LOW": "#ff6666",
            "CRITICAL": "red",
        }
        gauge_color = color_map.get(risk_level, "gray")

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number",
                    value=prob_sla,
                    title={"text": f"{borough} - SLA Probability"},
                    number={"suffix": "%"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": gauge_color},
                        "steps": [
                            {"range": [0, 50], "color": "lightcoral"},
                            {"range": [50, 75], "color": "lightyellow"},
                            {"range": [75, 90], "color": "lightblue"},
                            {"range": [90, 100], "color": "lightgreen"},
                        ],
                    },
                )
            ]
        )

        fig.update_layout(
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
            margin={"t": 80, "b": 50, "l": 20, "r": 20},
        )

        stats = StatisticsPanel(
            record_count=1,
            mean_value=prob_sla,
            last_timestamp=pd.to_datetime(row["analytics_timestamp"]),
            calculation_method=f"Bootstrap CI for {borough}",
            confidence_level="95%",
            additional_stats={
                "Point Estimate": f"{point_estimate:.4f}",
                "CI Lower": f"{ci_lower:.4f}",
                "CI Upper": f"{ci_upper:.4f}",
                "Risk Level": risk_level,
            },
        )

        return fig, stats

    def render_ci_visualization(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render confidence interval visualization with error bars.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure()

        # Sort by point estimate for better visualization
        sorted_data = self.data.sort_values("point_estimate")

        fig.add_trace(
            go.Scatter(
                x=sorted_data["borough"],
                y=sorted_data["point_estimate"],
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=sorted_data["ci_upper_95"] - sorted_data["point_estimate"],
                    arrayminus=sorted_data["point_estimate"] - sorted_data["ci_lower_95"],
                    color="red",
                ),
                mode="markers",
                marker=dict(size=10, color="blue"),
                name="Point Estimate",
            )
        )

        fig.update_layout(
            title="Phase F: Bootstrap Confidence Intervals (95%)",
            xaxis_title="Borough",
            yaxis_title="Proportion",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="closest",
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["point_estimate"].mean(),
            min_value=self.data["ci_lower_95"].min(),
            max_value=self.data["ci_upper_95"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Bootstrap Resampling (1000 iterations)",
            confidence_level="95%",
            additional_stats={
                "Avg CI Width": f"{self.data['interval_width'].mean():.4f}",
            },
        )

        return fig, stats

    def render_risk_level_indicator(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render indicator showing percentage at each risk level.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        risk_counts = self.data["risk_level"].value_counts()

        # Calculate critical + high risk percentage
        at_risk = (risk_counts.get("CRITICAL", 0) + risk_counts.get("LOW", 0)) / len(
            self.data
        ) * 100

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="number+gauge",
                    value=at_risk,
                    title={"text": "At-Risk Boroughs"},
                    number={"suffix": "%"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "red"},
                        "steps": [
                            {"range": [0, 20], "color": "lightgreen"},
                            {"range": [20, 50], "color": "lightyellow"},
                            {"range": [50, 100], "color": "lightcoral"},
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
            mean_value=at_risk,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Risk Level Classification",
            confidence_level="95%",
            additional_stats=risk_counts.to_dict(),
        )

        return fig, stats

    def render_ci_width_comparison(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render comparison of confidence interval widths.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Bar(
                x=self.data["borough"],
                y=self.data["interval_width"],
                text=self.data["interval_width"].round(4),
                textposition="auto",
                marker=dict(
                    color=self.data["interval_width"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="CI Width"),
                ),
            )
        )

        fig.update_layout(
            title="Phase F: Confidence Interval Width by Borough",
            xaxis_title="Borough",
            yaxis_title="CI Width (Upper - Lower)",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["interval_width"].mean(),
            min_value=self.data["interval_width"].min(),
            max_value=self.data["interval_width"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="CI Width Calculation",
            confidence_level="95%",
            additional_stats={
                "Narrowest": f"{self.data['interval_width'].min():.4f}",
                "Widest": f"{self.data['interval_width'].max():.4f}",
            },
        )

        return fig, stats

    def render_probability_distribution(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render histogram of SLA probabilities.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Histogram(
                x=self.data["prob_meets_sla"] * 100,
                nbinsx=20,
                marker_color="rgba(0, 100, 200, 0.7)",
            )
        )

        # Add 90% threshold line
        fig.add_vline(
            x=90,
            line_dash="dash",
            line_color="red",
            annotation_text="Target: 90%",
        )

        fig.update_layout(
            title="Phase F: Distribution of SLA Probabilities",
            xaxis_title="SLA Probability (%)",
            yaxis_title="Frequency",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=(self.data["prob_meets_sla"] * 100).mean(),
            min_value=(self.data["prob_meets_sla"] * 100).min(),
            max_value=(self.data["prob_meets_sla"] * 100).max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Probability Distribution",
            confidence_level="95%",
        )

        return fig, stats

    def render_point_estimate_comparison(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render comparison of point estimates across boroughs.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=self.data["borough"],
                y=self.data["point_estimate"],
                name="Point Estimate",
                marker_color="blue",
            )
        )

        fig.update_layout(
            title="Phase F: Point Estimate by Borough",
            xaxis_title="Borough",
            yaxis_title="Proportion",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["point_estimate"].mean(),
            min_value=self.data["point_estimate"].min(),
            max_value=self.data["point_estimate"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Bootstrap Point Estimation",
            confidence_level="95%",
        )

        return fig, stats

    def render_all_phase_f_charts(self) -> dict:
        """Render all 17 Phase F visualizations.

        Returns:
            Dictionary mapping chart names to (figure, statistics) tuples
        """
        self.fetch_data()

        charts = {
            "main_sla_gauge": self.render_main_sla_gauge(),
            "borough_sla_gauge_mn": self.render_borough_sla_gauge("MN"),
            "borough_sla_gauge_bk": self.render_borough_sla_gauge("BK"),
            "borough_sla_gauge_bx": self.render_borough_sla_gauge("BX"),
            "borough_sla_gauge_qn": self.render_borough_sla_gauge("QN"),
            "borough_sla_gauge_si": self.render_borough_sla_gauge("SI"),
            "ci_visualization": self.render_ci_visualization(),
            "risk_level_indicator": self.render_risk_level_indicator(),
            "ci_width_comparison": self.render_ci_width_comparison(),
            "probability_distribution": self.render_probability_distribution(),
            "point_estimate_comparison": self.render_point_estimate_comparison(),
            "risk_level_pie": self._render_risk_level_pie(),
            "sla_vs_ci_scatter": self._render_sla_vs_ci_scatter(),
            "cumulative_probability": self._render_cumulative_probability(),
            "risk_heatmap": self._render_risk_heatmap(),
            "bootstrap_summary": self._render_bootstrap_summary(),
            "investment_justification": self._render_investment_justification(),
        }

        logger.info(f"Rendered {len(charts)} Phase F visualizations")
        return charts

    def _render_risk_level_pie(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render pie chart of risk level distribution.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        risk_counts = self.data["risk_level"].value_counts()

        fig = go.Figure(
            data=go.Pie(
                labels=risk_counts.index,
                values=risk_counts.values,
                hole=0.3,
                textinfo="label+percent+value",
            )
        )

        fig.update_layout(
            title="Phase F: Risk Level Distribution",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Risk Classification",
            confidence_level="95%",
            additional_stats=risk_counts.to_dict(),
        )

        return fig, stats

    def _render_sla_vs_ci_scatter(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render scatter plot of SLA probability vs CI width.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Scatter(
                x=self.data["prob_meets_sla"] * 100,
                y=self.data["interval_width"],
                mode="markers+text",
                text=self.data["borough"],
                textposition="top center",
                marker=dict(
                    size=10,
                    color=[
                        "red" if risk == "CRITICAL"
                        else "orange" if risk == "LOW"
                        else "yellow" if risk == "MEDIUM"
                        else "green"
                        for risk in self.data["risk_level"]
                    ],
                    line=dict(width=2, color="white"),
                ),
            )
        )

        fig.update_layout(
            title="Phase F: SLA Probability vs CI Width",
            xaxis_title="SLA Probability (%)",
            yaxis_title="Confidence Interval Width",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="closest",
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["prob_meets_sla"].mean() * 100,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Scatter Analysis: SLA vs CI",
            confidence_level="95%",
        )

        return fig, stats

    def _render_cumulative_probability(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render cumulative probability curve.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        sorted_data = self.data.sort_values("prob_meets_sla")
        cumulative_prob = range(1, len(sorted_data) + 1)

        fig = go.Figure(
            data=go.Scatter(
                x=sorted_data["prob_meets_sla"] * 100,
                y=[p / len(sorted_data) * 100 for p in cumulative_prob],
                mode="lines+markers",
                fill="tozeroy",
                name="Cumulative",
                line=dict(color="blue", width=2),
            )
        )

        # Add 90% threshold
        fig.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="90% Target")

        fig.update_layout(
            title="Phase F: Cumulative Probability Distribution",
            xaxis_title="SLA Probability (%)",
            yaxis_title="Cumulative Percentage of Boroughs",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=(self.data["prob_meets_sla"] * 100).mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Empirical Cumulative Distribution",
            confidence_level="95%",
        )

        return fig, stats

    def _render_risk_heatmap(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render heatmap of risk metrics.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Create a heatmap with multiple metrics
        metrics = self.data[
            ["borough", "prob_meets_sla", "point_estimate", "interval_width"]
        ].set_index("borough")

        # Normalize to 0-1 for heatmap
        metrics_norm = (metrics - metrics.min()) / (metrics.max() - metrics.min())

        fig = go.Figure(
            data=go.Heatmap(
                z=metrics_norm.T.values,
                x=metrics_norm.index,
                y=["SLA Prob", "Point Est", "CI Width"],
                colorscale="RdYlGn",
                colorbar=dict(title="Normalized"),
            )
        )

        fig.update_layout(
            title="Phase F: Risk Metrics Heatmap",
            xaxis_title="Borough",
            yaxis_title="Metric",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["prob_meets_sla"].mean() * 100,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Normalized Risk Heatmap",
            confidence_level="95%",
        )

        return fig, stats

    def _render_bootstrap_summary(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render bootstrap summary statistics.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        summary_data = pd.DataFrame({
            "Metric": ["Mean SLA %", "Min SLA %", "Max SLA %", "Avg CI Width"],
            "Value": [
                self.data["prob_meets_sla"].mean() * 100,
                self.data["prob_meets_sla"].min() * 100,
                self.data["prob_meets_sla"].max() * 100,
                self.data["interval_width"].mean() * 100,
            ],
        })

        fig = go.Figure(
            data=go.Bar(
                x=summary_data["Metric"],
                y=summary_data["Value"],
                text=summary_data["Value"].round(2),
                textposition="auto",
                marker_color=["green", "blue", "red", "orange"],
            )
        )

        fig.update_layout(
            title="Phase F: Bootstrap Summary Statistics",
            yaxis_title="Value",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["prob_meets_sla"].mean() * 100,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Bootstrap Aggregation",
            confidence_level="95%",
        )

        return fig, stats

    def _render_investment_justification(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render investment justification chart (gap analysis).

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        self.data["sla_gap"] = 90 - (self.data["prob_meets_sla"] * 100)
        self.data["sla_gap"] = self.data["sla_gap"].clip(lower=0)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=self.data["borough"],
                y=90 - self.data["sla_gap"],
                name="Current SLA %",
                marker_color="green",
            )
        )

        fig.add_trace(
            go.Bar(
                x=self.data["borough"],
                y=self.data["sla_gap"],
                name="Gap to Target",
                marker_color="red",
            )
        )

        fig.update_layout(
            title="Phase F: SLA Gap Analysis (Investment Justification)",
            xaxis_title="Borough",
            yaxis_title="Probability (%)",
            barmode="stack",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["sla_gap"].mean(),
            max_value=self.data["sla_gap"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Gap Analysis (90% Target)",
            confidence_level="95%",
            additional_stats={
                "Max Gap": f"{self.data['sla_gap'].max():.1f}%",
                "Avg Gap": f"{self.data['sla_gap'].mean():.1f}%",
            },
        )

        return fig, stats
