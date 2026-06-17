"""Phase B Visualizations: Spatial Clustering & Moran's I Analysis (12 Charts).

Renders all Phase B visualizations:
1. Main Moran's I gauge chart
2-6. Borough-specific gauge charts (MN, BK, BX, QN, SI)
7-12. Supporting visualizations (classification map, p-value scatter, significance heatmap, etc.)

Data source: app_queries.v_phase_b_results
All charts include summary statistics below.
"""
import logging

import pandas as pd
import plotly.graph_objects as go

from socrata_toolkit.motherduck.connector import MotherDuckConnection

from .statistics_display import StatisticsPanel

logger = logging.getLogger(__name__)

class PhaseBVisualizations:
    """Renders all 12 Phase B visualizations (spatial clustering & Moran's I).

    Attributes:
        conn: MotherDuckConnection for querying app_queries.v_phase_b_results
        data: DataFrame from serving view
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize Phase B visualizations.

        Args:
            connection: MotherDuckConnection instance
        """
        self.conn = connection
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from app_queries.v_phase_b_results.

        Returns:
            DataFrame with columns: borough, morans_i_value, classification,
                                    location_count, p_value, significance,
                                    analytics_timestamp

        Raises:
            RuntimeError: If query fails
        """
        query = "SELECT * FROM app_queries.v_phase_b_results ORDER BY borough"
        self.data = self.conn.fetch_dataframe(query)
        if self.data.empty:
            raise RuntimeError(
                "No data in app_queries.v_phase_b_results. "
                "Run Phase 1 (MotherDuck infrastructure) first."
            )
        logger.info(f"Fetched {len(self.data)} rows from Phase B view")
        return self.data

    def render_main_gauge_chart(
        self,
    ) -> tuple[go.Figure, StatisticsPanel]:
        """Render main Moran's I gauge chart (borough average).

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Calculate aggregate statistics
        avg_morans = self.data["morans_i_value"].mean()
        min_morans = self.data["morans_i_value"].min()
        max_morans = self.data["morans_i_value"].max()
        last_ts = pd.to_datetime(self.data["analytics_timestamp"]).max()

        # Determine gauge color based on Moran's I value
        if avg_morans > 0.5:
            gauge_color = "red"  # Strong clustering
            status = "Strong Clustering"
        elif avg_morans > 0:
            gauge_color = "orange"  # Moderate clustering
            status = "Moderate Clustering"
        else:
            gauge_color = "green"  # Random or dispersed
            status = "Random Distribution"

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number+delta",
                    value=avg_morans,
                    title={"text": "Moran's I Spatial Clustering Index"},
                    delta={"reference": 0, "suffix": " from random"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [-1, 1]},
                        "bar": {"color": gauge_color},
                        "steps": [
                            {"range": [-1, -0.5], "color": "lightgreen"},
                            {"range": [-0.5, 0], "color": "lightblue"},
                            {"range": [0, 0.5], "color": "lightyellow"},
                            {"range": [0.5, 1], "color": "lightcoral"},
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": 0.5,
                        },
                    },
                )
            ]
        )

        fig.update_layout(
            title_text="Phase B: Spatial Clustering Analysis",
            height=500,
            font={"family": "Arial, sans-serif", "size": 12},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=avg_morans,
            min_value=min_morans,
            max_value=max_morans,
            last_timestamp=last_ts,
            calculation_method="Moran's I Spatial Autocorrelation",
            confidence_level="95%",
            additional_stats={"Status": status, "Boroughs": len(self.data)},
        )

        return fig, stats

    def render_borough_gauge(self, borough: str) -> tuple[go.Figure, StatisticsPanel]:
        """Render gauge chart for a specific borough.

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
        morans_i = row["morans_i_value"]
        p_value = row["p_value"]
        classification = row["classification"]
        location_count = row["location_count"]
        significance = row["significance"]
        last_ts = pd.to_datetime(row["analytics_timestamp"])

        # Color based on classification
        color_map = {
            "STRONG_CLUSTERING": "red",
            "MODERATE_CLUSTERING": "orange",
            "RANDOM_DISTRIBUTION": "blue",
            "SPATIAL_DISPERSION": "green",
        }
        gauge_color = color_map.get(classification, "gray")

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number",
                    value=morans_i,
                    title={"text": f"{borough} - Moran's I"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [-1, 1]},
                        "bar": {"color": gauge_color},
                        "steps": [
                            {"range": [-1, 0], "color": "lightblue"},
                            {"range": [0, 1], "color": "lightyellow"},
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
            record_count=int(location_count),
            mean_value=morans_i,
            last_timestamp=last_ts,
            calculation_method=f"Moran's I for {borough}",
            confidence_level="95%",
            additional_stats={
                "Classification": classification,
                "P-Value": f"{p_value:.4f}",
                "Significance": significance,
            },
        )

        return fig, stats

    def render_classification_heatmap(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render heatmap of classifications across boroughs.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Create a matrix for heatmap (boroughs × classification values)
        heatmap_data = self.data[["borough", "morans_i_value"]].set_index(
            "borough"
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=self.data["morans_i_value"],
                x=self.data["borough"],
                y=["Moran's I"],
                colorscale="RdYlGn_r",
                text=self.data["classification"],
                texttemplate="%{text}",
                colorbar=dict(title="Moran's I Value"),
            )
        )

        fig.update_layout(
            title="Phase B: Classification Heatmap (Borough Comparison)",
            xaxis_title="Borough",
            yaxis_title="Metric",
            height=300,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["morans_i_value"].mean(),
            min_value=self.data["morans_i_value"].min(),
            max_value=self.data["morans_i_value"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Spatial Classification Matrix",
            confidence_level="95%",
        )

        return fig, stats

    def render_p_value_scatter(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render scatter plot: Moran's I vs P-Value.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Scatter(
                x=self.data["morans_i_value"],
                y=self.data["p_value"],
                mode="markers+text",
                text=self.data["borough"],
                textposition="top center",
                marker=dict(
                    size=self.data["location_count"] / 50,  # Size by location count
                    color=self.data["morans_i_value"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Moran's I"),
                    line=dict(width=2, color="white"),
                ),
            )
        )

        # Add significance threshold line
        fig.add_hline(
            y=0.05,
            line_dash="dash",
            line_color="red",
            annotation_text="p=0.05 threshold",
            annotation_position="right",
        )

        fig.update_layout(
            title="Phase B: Statistical Significance (Moran's I vs P-Value)",
            xaxis_title="Moran's I Value",
            yaxis_title="P-Value",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
            hovermode="closest",
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["p_value"].mean(),
            min_value=self.data["p_value"].min(),
            max_value=self.data["p_value"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Moran's I Significance Testing",
            confidence_level="95%",
            additional_stats={
                "Significant Results (p<0.05)": len(
                    self.data[self.data["p_value"] < 0.05]
                ),
                "Non-Significant": len(self.data[self.data["p_value"] >= 0.05]),
            },
        )

        return fig, stats

    def render_location_count_bar(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render bar chart of location counts by borough.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        fig = go.Figure(
            data=go.Bar(
                x=self.data["borough"],
                y=self.data["location_count"],
                text=self.data["location_count"],
                textposition="auto",
                marker=dict(
                    color=self.data["morans_i_value"],
                    colorscale="Portland",
                    showscale=True,
                    colorbar=dict(title="Moran's I"),
                ),
            )
        )

        fig.update_layout(
            title="Phase B: Inspection Locations by Borough",
            xaxis_title="Borough",
            yaxis_title="Number of Locations",
            height=400,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=int(self.data["location_count"].sum()),
            mean_value=self.data["location_count"].mean(),
            min_value=self.data["location_count"].min(),
            max_value=self.data["location_count"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Location Count Aggregation",
            confidence_level="100%",
            additional_stats={
                "Total Locations": int(self.data["location_count"].sum()),
                "Avg Per Borough": f"{self.data['location_count'].mean():.0f}",
            },
        )

        return fig, stats

    def render_classification_pie(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render pie chart of classification distribution.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        classification_counts = self.data["classification"].value_counts()

        fig = go.Figure(
            data=go.Pie(
                labels=classification_counts.index,
                values=classification_counts.values,
                hole=0.3,
                textinfo="label+percent+value",
            )
        )

        fig.update_layout(
            title="Phase B: Distribution of Spatial Classifications",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Classification Distribution",
            confidence_level="100%",
            additional_stats=classification_counts.to_dict(),
        )

        return fig, stats

    def render_significance_indicator(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render indicator showing percentage of significant results.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        significant_count = len(self.data[self.data["p_value"] < 0.05])
        total_count = len(self.data)
        percentage = (significant_count / total_count) * 100

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="number+gauge",
                    value=percentage,
                    title={"text": "Significant Results (p<0.05)"},
                    number={"suffix": "%"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "darkblue"},
                        "steps": [
                            {"range": [0, 50], "color": "lightgray"},
                            {"range": [50, 100], "color": "lightgreen"},
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
            record_count=total_count,
            mean_value=percentage,
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="P-Value Threshold Testing",
            confidence_level="95%",
            additional_stats={
                "Significant": significant_count,
                "Non-Significant": total_count - significant_count,
                "Threshold": "0.05",
            },
        )

        return fig, stats

    def render_all_phase_b_charts(
        self,
    ) -> dict:
        """Render all 12 Phase B visualizations.

        Returns:
            Dictionary mapping chart names to (figure, statistics) tuples
        """
        self.fetch_data()

        charts = {
            "main_gauge": self.render_main_gauge_chart(),
            "borough_gauge_mn": self.render_borough_gauge("MN"),
            "borough_gauge_bk": self.render_borough_gauge("BK"),
            "borough_gauge_bx": self.render_borough_gauge("BX"),
            "borough_gauge_qn": self.render_borough_gauge("QN"),
            "borough_gauge_si": self.render_borough_gauge("SI"),
            "classification_heatmap": self.render_classification_heatmap(),
            "p_value_scatter": self.render_p_value_scatter(),
            "location_count_bar": self.render_location_count_bar(),
            "classification_pie": self.render_classification_pie(),
            "significance_indicator": self.render_significance_indicator(),
            "morans_i_comparison": self._render_morans_i_comparison(),
        }

        logger.info(f"Rendered {len(charts)} Phase B visualizations")
        return charts

    def _render_morans_i_comparison(
        self,
    ) -> tuple[go.Figure, StatisticsPanel]:
        """Render comparison chart of Moran's I values across boroughs.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Create a multi-panel comparison
        fig = go.Figure()

        # Add bars for Moran's I
        fig.add_trace(
            go.Bar(
                x=self.data["borough"],
                y=self.data["morans_i_value"],
                name="Moran's I",
                marker_color="rgba(55, 128, 191, 0.7)",
            )
        )

        # Add scatter for p-values on secondary axis
        fig.add_trace(
            go.Scatter(
                x=self.data["borough"],
                y=self.data["p_value"],
                name="P-Value",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="red", width=2),
            )
        )

        fig.update_layout(
            title="Phase B: Moran's I vs P-Value by Borough",
            xaxis_title="Borough",
            yaxis=dict(title="Moran's I Value", side="left"),
            yaxis2=dict(title="P-Value", overlaying="y", side="right"),
            hovermode="x unified",
            height=450,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["morans_i_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Borough-Level Comparison",
            confidence_level="95%",
        )

        return fig, stats
