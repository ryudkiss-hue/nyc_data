"""Phase D Visualizations: Geographic Anomalies & Maps (15 Charts).

Renders all Phase D visualizations:
1. Main geographic map with anomaly clustering
2-6. Borough-specific maps
7-15. Supporting visualizations (priority ranking, outlier distribution, etc.)

Data source: app_queries.v_phase_d_results
All charts include summary statistics below.
"""
import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from socrata_toolkit.motherduck.connector import MotherDuckConnection

from .statistics_display import StatisticsPanel

logger = logging.getLogger(__name__)

class PhaseDVisualizations:
    """Renders all 15 Phase D visualizations (geographic anomalies).

    Attributes:
        conn: MotherDuckConnection for querying app_queries.v_phase_d_results
        data: DataFrame from serving view
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize Phase D visualizations.

        Args:
            connection: MotherDuckConnection instance
        """
        self.conn = connection
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from app_queries.v_phase_d_results.

        Returns:
            DataFrame with columns: location_id, borough, latitude, longitude,
                                    inspection_count, z_score_violations,
                                    outlier_class, priority_rank, analytics_timestamp

        Raises:
            RuntimeError: If query fails
        """
        query = "SELECT * FROM app_queries.v_phase_d_results ORDER BY borough, priority_rank"
        self.data = self.conn.fetch_dataframe(query)
        if self.data.empty:
            raise RuntimeError(
                "No data in app_queries.v_phase_d_results. "
                "Run Phase 1 (MotherDuck infrastructure) first."
            )
        logger.info(f"Fetched {len(self.data)} rows from Phase D view")
        return self.data

    def render_main_geographic_map(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render main geographic map with all anomalies.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Color mapping for outlier classes
        color_map = {
            "HIGH_OUTLIER": "red",
            "NORMAL": "blue",
            "LOW_OUTLIER": "green",
        }

        fig = go.Figure(
            data=go.Scattergeo(
                lon=self.data["longitude"],
                lat=self.data["latitude"],
                mode="markers+text",
                text=self.data["location_id"],
                marker=dict(
                    size=self.data["z_score_violations"].abs() * 5 + 5,
                    color=[color_map.get(c, "gray") for c in self.data["outlier_class"]],
                    opacity=0.7,
                    line=dict(width=1, color="white"),
                    colorscale=None,
                ),
                customdata=self.data[
                    ["borough", "inspection_count", "z_score_violations", "outlier_class"]
                ],
                hovertemplate="<b>%{text}</b><br>"
                "Borough: %{customdata[0]}<br>"
                "Inspections: %{customdata[1]}<br>"
                "Z-Score: %{customdata[2]:.2f}<br>"
                "Class: %{customdata[3]}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Phase D: Geographic Anomaly Clustering",
            geo=dict(
                scope="usa",
                center=dict(lon=-74.0, lat=40.7),
                projection_type="mercator",
                showland=True,
                landcolor="rgb(243, 243, 243)",
            ),
            height=600,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        high_outliers = len(self.data[self.data["outlier_class"] == "HIGH_OUTLIER"])
        low_outliers = len(self.data[self.data["outlier_class"] == "LOW_OUTLIER"])
        normal = len(self.data[self.data["outlier_class"] == "NORMAL"])

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["z_score_violations"].mean(),
            min_value=self.data["z_score_violations"].min(),
            max_value=self.data["z_score_violations"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="DBSCAN Spatial Clustering + Z-Score Anomaly Detection",
            confidence_level="95%",
            additional_stats={
                "High Outliers": high_outliers,
                "Low Outliers": low_outliers,
                "Normal Locations": normal,
            },
        )

        return fig, stats

    def render_borough_map(self, borough: str) -> tuple[go.Figure, StatisticsPanel]:
        """Render map for a specific borough.

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

        color_map = {
            "HIGH_OUTLIER": "red",
            "NORMAL": "blue",
            "LOW_OUTLIER": "green",
        }

        fig = go.Figure(
            data=go.Scattergeo(
                lon=borough_data["longitude"],
                lat=borough_data["latitude"],
                mode="markers+text",
                text=borough_data["location_id"],
                textposition="top center",
                marker=dict(
                    size=borough_data["z_score_violations"].abs() * 5 + 5,
                    color=[color_map.get(c, "gray") for c in borough_data["outlier_class"]],
                    opacity=0.7,
                    line=dict(width=1, color="white"),
                ),
                customdata=borough_data[
                    ["inspection_count", "z_score_violations", "outlier_class"]
                ],
                hovertemplate="<b>%{text}</b><br>"
                "Inspections: %{customdata[0]}<br>"
                "Z-Score: %{customdata[1]:.2f}<br>"
                "Class: %{customdata[2]}<extra></extra>",
            )
        )

        fig.update_layout(
            title=f"Phase D: {borough} Anomalies",
            geo=dict(
                scope="usa",
                center=dict(lon=-74.0, lat=40.7),
                projection_type="mercator",
            ),
            height=500,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        high_outliers = len(
            borough_data[borough_data["outlier_class"] == "HIGH_OUTLIER"]
        )
        low_outliers = len(
            borough_data[borough_data["outlier_class"] == "LOW_OUTLIER"]
        )

        stats = StatisticsPanel(
            record_count=len(borough_data),
            mean_value=borough_data["z_score_violations"].mean(),
            min_value=borough_data["z_score_violations"].min(),
            max_value=borough_data["z_score_violations"].max(),
            last_timestamp=pd.to_datetime(borough_data["analytics_timestamp"].iloc[0]),
            calculation_method=f"Z-Score Anomaly Detection for {borough}",
            confidence_level="95%",
            additional_stats={
                "High Outliers": high_outliers,
                "Low Outliers": low_outliers,
            },
        )

        return fig, stats

    def render_priority_ranking_table(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render priority ranking as table/bar chart.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Get top 10 by priority within each borough
        top_priority = (
            self.data.nlargest(10, "priority_rank")
            if len(self.data) > 0
            else self.data
        )

        fig = go.Figure(
            data=go.Bar(
                x=top_priority["location_id"],
                y=top_priority["z_score_violations"],
                text=top_priority["z_score_violations"].round(2),
                textposition="auto",
                marker=dict(
                    color=top_priority["z_score_violations"],
                    colorscale="RdYlGn_r",
                    showscale=True,
                    colorbar=dict(title="Z-Score"),
                ),
                customdata=top_priority[["borough", "outlier_class"]],
                hovertemplate="<b>%{x}</b><br>"
                "Z-Score: %{y:.2f}<br>"
                "Borough: %{customdata[0]}<br>"
                "Class: %{customdata[1]}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Phase D: Top Priority Anomalies",
            xaxis_title="Location ID",
            yaxis_title="Z-Score (Violation Intensity)",
            height=450,
            font={"family": "Arial, sans-serif", "size": 10},
            xaxis_tickangle=-45,
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["z_score_violations"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Priority Ranking by Z-Score",
            confidence_level="95%",
        )

        return fig, stats

    def render_outlier_distribution(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render distribution of outlier classes.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        outlier_counts = self.data["outlier_class"].value_counts()

        fig = go.Figure(
            data=go.Pie(
                labels=outlier_counts.index,
                values=outlier_counts.values,
                hole=0.3,
                textinfo="label+percent+value",
                marker=dict(colors=["red", "blue", "green"]),
            )
        )

        fig.update_layout(
            title="Phase D: Outlier Class Distribution",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Outlier Classification",
            confidence_level="95%",
            additional_stats=outlier_counts.to_dict(),
        )

        return fig, stats

    def render_z_score_histogram(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render histogram of z-scores.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Histogram(
                x=self.data["z_score_violations"],
                nbinsx=30,
                marker_color="rgba(0, 100, 200, 0.7)",
            )
        )

        # Add standard deviation lines
        mean_z = self.data["z_score_violations"].mean()
        std_z = self.data["z_score_violations"].std()

        fig.add_vline(x=mean_z, line_dash="dash", line_color="red",
                     annotation_text=f"Mean: {mean_z:.2f}")
        fig.add_vline(x=mean_z + (2 * std_z), line_dash="dot", line_color="orange",
                     annotation_text="2σ threshold")
        fig.add_vline(x=mean_z - (2 * std_z), line_dash="dot", line_color="orange")

        fig.update_layout(
            title="Phase D: Z-Score Distribution",
            xaxis_title="Z-Score",
            yaxis_title="Frequency",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=mean_z,
            min_value=self.data["z_score_violations"].min(),
            max_value=self.data["z_score_violations"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Z-Score Distribution Analysis",
            confidence_level="95%",
            additional_stats={
                "Std Dev": f"{std_z:.2f}",
                "High Outliers (>2σ)": len(
                    self.data[self.data["z_score_violations"] > mean_z + (2 * std_z)]
                ),
            },
        )

        return fig, stats

    def render_inspection_count_scatter(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render scatter: inspection count vs z-score.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Scatter(
                x=self.data["inspection_count"],
                y=self.data["z_score_violations"],
                mode="markers",
                text=self.data["location_id"],
                marker=dict(
                    size=8,
                    color=[
                        "red" if c == "HIGH_OUTLIER"
                        else "green" if c == "LOW_OUTLIER"
                        else "blue"
                        for c in self.data["outlier_class"]
                    ],
                    opacity=0.6,
                    line=dict(width=1, color="white"),
                ),
                customdata=self.data[["borough", "outlier_class"]],
                hovertemplate="<b>%{text}</b><br>"
                "Inspections: %{x}<br>"
                "Z-Score: %{y:.2f}<br>"
                "Borough: %{customdata[0]}<br>"
                "Class: %{customdata[1]}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Phase D: Inspection Count vs Anomaly Intensity",
            xaxis_title="Number of Inspections",
            yaxis_title="Z-Score",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="closest",
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["inspection_count"].mean(),
            min_value=self.data["inspection_count"].min(),
            max_value=self.data["inspection_count"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Scatter Analysis: Inspection Count vs Anomaly",
            confidence_level="95%",
        )

        return fig, stats

    def render_borough_anomaly_comparison(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render comparison of anomaly counts by borough.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        borough_stats = self.data.groupby("borough").agg({
            "outlier_class": lambda x: (x == "HIGH_OUTLIER").sum(),
            "z_score_violations": ["mean", "count"],
        }).reset_index()

        borough_stats.columns = ["borough", "high_outlier_count", "mean_z_score", "total_count"]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=borough_stats["borough"],
                y=borough_stats["high_outlier_count"],
                name="High Outliers",
                marker_color="red",
                opacity=0.7,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=borough_stats["borough"],
                y=borough_stats["mean_z_score"],
                name="Mean Z-Score",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="blue", width=2),
            )
        )

        fig.update_layout(
            title="Phase D: Anomaly Comparison Across Boroughs",
            xaxis_title="Borough",
            yaxis=dict(title="High Outlier Count", side="left"),
            yaxis2=dict(title="Mean Z-Score", overlaying="y", side="right"),
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="x unified",
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["z_score_violations"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Borough-Level Anomaly Comparison",
            confidence_level="95%",
        )

        return fig, stats

    def render_all_phase_d_charts(self) -> dict:
        """Render all 15 Phase D visualizations.

        Returns:
            Dictionary mapping chart names to (figure, statistics) tuples
        """
        self.fetch_data()

        charts = {
            "main_geographic_map": self.render_main_geographic_map(),
            "borough_map_mn": self.render_borough_map("MN"),
            "borough_map_bk": self.render_borough_map("BK"),
            "borough_map_bx": self.render_borough_map("BX"),
            "borough_map_qn": self.render_borough_map("QN"),
            "borough_map_si": self.render_borough_map("SI"),
            "priority_ranking_table": self.render_priority_ranking_table(),
            "outlier_distribution": self.render_outlier_distribution(),
            "z_score_histogram": self.render_z_score_histogram(),
            "inspection_count_scatter": self.render_inspection_count_scatter(),
            "borough_anomaly_comparison": self.render_borough_anomaly_comparison(),
            "z_score_by_outlier_class": self._render_z_score_by_outlier_class(),
            "inspection_count_by_borough": self._render_inspection_count_by_borough(),
            "priority_heatmap": self._render_priority_heatmap(),
            "location_density_map": self._render_location_density_map(),
        }

        logger.info(f"Rendered {len(charts)} Phase D visualizations")
        return charts

    def _render_z_score_by_outlier_class(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render box plot of z-scores grouped by outlier class.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure()

        for outlier_class in self.data["outlier_class"].unique():
            class_data = self.data[self.data["outlier_class"] == outlier_class]
            fig.add_trace(
                go.Box(
                    y=class_data["z_score_violations"],
                    name=outlier_class,
                    boxmean="sd",
                )
            )

        fig.update_layout(
            title="Phase D: Z-Score Distribution by Outlier Class",
            yaxis_title="Z-Score",
            xaxis_title="Outlier Class",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["z_score_violations"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Box Plot Analysis by Class",
            confidence_level="95%",
        )

        return fig, stats

    def _render_inspection_count_by_borough(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render bar chart of total inspection counts by borough.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        borough_totals = self.data.groupby("borough")["inspection_count"].sum()

        fig = go.Figure(
            data=go.Bar(
                x=borough_totals.index,
                y=borough_totals.values,
                text=borough_totals.values,
                textposition="auto",
                marker=dict(
                    color=borough_totals.values,
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Total Inspections"),
                ),
            )
        )

        fig.update_layout(
            title="Phase D: Total Inspections by Borough",
            xaxis_title="Borough",
            yaxis_title="Total Inspections",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=int(self.data["inspection_count"].sum()),
            mean_value=self.data["inspection_count"].mean(),
            min_value=self.data["inspection_count"].min(),
            max_value=self.data["inspection_count"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Inspection Count Aggregation by Borough",
            confidence_level="100%",
        )

        return fig, stats

    def _render_priority_heatmap(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render heatmap of priority ranks by borough.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Sample top 10 locations for heatmap
        top_data = self.data.nlargest(10, "priority_rank")

        fig = go.Figure(
            data=go.Heatmap(
                z=top_data["z_score_violations"],
                x=top_data["borough"],
                y=top_data["location_id"],
                colorscale="RdYlGn_r",
                colorbar=dict(title="Z-Score"),
            )
        )

        fig.update_layout(
            title="Phase D: Priority Heatmap (Top 10 Anomalies)",
            xaxis_title="Borough",
            yaxis_title="Location ID",
            height=450,
            font={"family": "Arial, sans-serif", "size": 10},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["z_score_violations"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Priority Ranking Heatmap",
            confidence_level="95%",
        )

        return fig, stats

    def _render_location_density_map(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render 2D density map of anomalies.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Histogram2d(
                x=self.data["longitude"],
                y=self.data["latitude"],
                colorscale="YlOrRd",
                nbinsx=20,
                nbinsy=20,
            )
        )

        fig.update_layout(
            title="Phase D: Spatial Density of Anomalies",
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            height=500,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["z_score_violations"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="2D Spatial Density Estimation",
            confidence_level="95%",
        )

        return fig, stats
