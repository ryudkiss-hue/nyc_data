"""Metric Cards: 18 Dashboard Metrics (5 boroughs × 18 Metrics = 90 rows).

Renders all 18 Metric cards with dynamic values from MotherDuck.
Each card displays:
- Metric name
- Current value
- Borough
- Metric category
- Trend indicator (up/down/stable)

Data source: app_queries.v_metric_dashboard
"""
import logging

import pandas as pd
import plotly.graph_objects as go

from socrata_toolkit.motherduck.connector import MotherDuckConnection

from .statistics_display import StatisticsPanel

logger = logging.getLogger(__name__)

class MetricCards:
    """Renders all 18 Metric cards with dynamic values.

    Attributes:
        conn: MotherDuckConnection for querying app_queries.v_metric_dashboard
        data: DataFrame from serving view
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize Metric cards.

        Args:
            connection: MotherDuckConnection instance
        """
        self.conn = connection
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from app_queries.v_metric_dashboard.

        Returns:
            DataFrame with columns: metric_name, borough, metric_value, metric_category,
                                    analytics_timestamp

        Raises:
            RuntimeError: If query fails
        """
        query = "SELECT * FROM app_queries.v_metric_dashboard ORDER BY borough, metric_name"
        self.data = self.conn.fetch_dataframe(query)
        if self.data.empty:
            raise RuntimeError(
                "No data in app_queries.v_metric_dashboard. "
                "Run Phase 1 (MotherDuck infrastructure) first."
            )
        logger.info(f"Fetched {len(self.data)} rows from Metric dashboard view")
        return self.data

    def get_metric_names(self) -> list[str]:
        """Get list of unique Metric names.

        Returns:
            List of Metric names
        """
        if self.data is None:
            self.fetch_data()
        return sorted(self.data["metric_name"].unique().tolist())

    def get_metric_for_borough(self, metric_name: str, borough: str) -> dict:
        """Get specific Metric value for a borough.

        Args:
            metric_name: Name of the Metric
            borough: Borough code

        Returns:
            Dictionary with Metric data

        Raises:
            ValueError: If Metric or borough not found
        """
        if self.data is None:
            self.fetch_data()

        metric_data = self.data[
            (self.data["metric_name"] == metric_name) & (self.data["borough"] == borough)
        ]
        if metric_data.empty:
            raise ValueError(f"Metric {metric_name} not found for borough {borough}")

        row = metric_data.iloc[0]
        return {
            "metric_name": row["metric_name"],
            "borough": row["borough"],
            "value": row["metric_value"],
            "category": row["metric_category"],
            "timestamp": row["analytics_timestamp"],
        }

    def render_metric_card(
        self, metric_name: str, borough: str
    ) -> tuple[go.Figure, StatisticsPanel]:
        """Render a single Metric card.

        Args:
            metric_name: Name of the Metric
            borough: Borough code

        Returns:
            Tuple of (figure, statistics)

        Raises:
            ValueError: If Metric or borough not found
        """
        metric_data = self.get_metric_for_borough(metric_name, borough)

        # Format value appropriately
        value = metric_data["value"]
        if isinstance(value, float):
            formatted_value = f"{value:.2f}" if value < 1000 else f"{value:.0f}"
        else:
            formatted_value = str(value)

        # Create a simple indicator card
        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="number",
                    value=value,
                    title={"text": f"{metric_data['category']} ({borough})"},
                    domain={"x": [0, 1], "y": [0, 1]},
                    number={"suffix": " ", "font": {"size": 28}},
                )
            ]
        )

        fig.update_layout(
            height=200,
            font={"family": "Arial, sans-serif", "size": 12},
            margin={"t": 40, "b": 20, "l": 20, "r": 20},
        )

        stats = StatisticsPanel(
            record_count=1,
            mean_value=value if isinstance(value, (int, float)) else None,
            last_timestamp=pd.to_datetime(metric_data["timestamp"]),
            calculation_method=f"{metric_name} Metric",
            confidence_level="95%",
        )

        return fig, stats

    def render_all_metric_cards(self) -> dict[str, tuple[go.Figure, StatisticsPanel]]:
        """Render all 18 Metric cards (one per Metric, aggregate across boroughs).

        Returns:
            Dictionary mapping Metric names to (figure, statistics) tuples
        """
        self.fetch_data()

        metric_names = self.get_metric_names()
        cards = {}

        for metric_name in metric_names:
            metric_subset = self.data[self.data["metric_name"] == metric_name]

            fig = self._create_metric_card_figure(metric_name, metric_subset)

            stats = StatisticsPanel(
                record_count=len(metric_subset),
                mean_value=metric_subset["metric_value"].mean(),
                min_value=metric_subset["metric_value"].min(),
                max_value=metric_subset["metric_value"].max(),
                last_timestamp=pd.to_datetime(metric_subset["analytics_timestamp"]).max(),
                calculation_method=f"Metric: {metric_name}",
                confidence_level="95%",
            )

            cards[metric_name] = (fig, stats)

        logger.info(f"Rendered {len(cards)} Metric cards")
        return cards

    def _create_metric_card_figure(self, metric_name: str, metric_data: pd.DataFrame) -> go.Figure:
        """Create a figure for a single Metric aggregated across boroughs.

        Args:
            metric_name: Name of the Metric
            metric_data: DataFrame with this Metric across all boroughs

        Returns:
            Plotly figure
        """
        # Create a gauge or number indicator depending on Metric type
        avg_value = metric_data["metric_value"].mean()

        # Determine appropriate gauge range and color
        if "probability" in metric_name.lower() or "rate" in metric_name.lower():
            gauge_range = [0, 100]
            color = (
                "green"
                if avg_value >= 75
                else "orange" if avg_value >= 50
                else "red"
            )
        elif "strength" in metric_name.lower() or "score" in metric_name.lower():
            gauge_range = [0, 100]
            color = (
                "green"
                if avg_value >= 75
                else "orange" if avg_value >= 50
                else "red"
            )
        else:
            gauge_range = [metric_data["metric_value"].min() * 0.9, metric_data["metric_value"].max() * 1.1]
            color = "blue"

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number",
                    value=avg_value,
                    title={"text": metric_name.replace("_", " ").title()},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": gauge_range},
                        "bar": {"color": color},
                        "steps": [
                            {
                                "range": [gauge_range[0], gauge_range[1] / 2],
                                "color": "lightgray",
                            },
                            {
                                "range": [gauge_range[1] / 2, gauge_range[1]],
                                "color": "lightgreen",
                            },
                        ],
                    },
                )
            ]
        )

        fig.update_layout(
            height=350,
            font={"family": "Arial, sans-serif", "size": 12},
            margin={"t": 60, "b": 20, "l": 20, "r": 20},
        )

        return fig

    def render_metric_summary_table(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render summary table of all Metric values by borough.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Create pivot table: Metrics × Boroughs
        pivot_data = self.data.pivot_table(
            index="metric_name",
            columns="borough",
            values="metric_value",
            aggfunc="first",
        )

        # Round numeric values
        pivot_data = pivot_data.round(2)

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=["Metric"] + list(pivot_data.columns),
                        fill_color="paleturquoise",
                        align="left",
                        font=dict(color="black", size=12),
                    ),
                    cells=dict(
                        values=[pivot_data.index] + [pivot_data[col] for col in pivot_data.columns],
                        fill_color="lavender",
                        align="left",
                        font=dict(size=11),
                        height=25,
                    ),
                )
            ]
        )

        fig.update_layout(
            title="Metric Summary: All Metrics by Borough",
            height=600,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["metric_value"].mean(),
            min_value=self.data["metric_value"].min(),
            max_value=self.data["metric_value"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Metric Aggregation",
            confidence_level="95%",
        )

        return fig, stats

    def render_metric_comparison_chart(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render comparison chart of average Metric values.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Average each Metric across boroughs
        metric_avg = self.data.groupby("metric_name")["metric_value"].mean().sort_values()

        fig = go.Figure(
            data=go.Bar(
                x=metric_avg.values,
                y=metric_avg.index,
                orientation="h",
                marker=dict(
                    color=metric_avg.values,
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Avg Value"),
                ),
            )
        )

        fig.update_layout(
            title="Metric Comparison: Average Values Across Boroughs",
            xaxis_title="Average Value",
            yaxis_title="Metric",
            height=500,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["metric_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="Metric Average Aggregation",
            confidence_level="95%",
        )

        return fig, stats

    def render_borough_metric_radar(self, borough: str) -> tuple[go.Figure, StatisticsPanel]:
        """Render radar chart of all Metrics for a specific borough.

        Args:
            borough: Borough code (MN, BK, BX, QN, SI)

        Returns:
            Tuple of (figure, statistics)

        Raises:
            ValueError: If borough not found
        """
        if self.data is None:
            self.fetch_data()

        borough_data = self.data[self.data["borough"] == borough]
        if borough_data.empty:
            raise ValueError(f"Borough {borough} not found in data")

        # Normalize values to 0-100 scale for radar
        normalized_values = []
        for _, row in borough_data.iterrows():
            val = row["metric_value"]
            if isinstance(val, (int, float)):
                # Simple normalization
                norm_val = min(100, max(0, val))
            else:
                norm_val = 50
            normalized_values.append(norm_val)

        fig = go.Figure(
            data=go.Scatterpolar(
                r=normalized_values,
                theta=borough_data["metric_name"],
                fill="toself",
                name=borough,
                line=dict(color="blue"),
            )
        )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"Metric Radar Chart: {borough}",
            height=500,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(borough_data),
            mean_value=borough_data["metric_value"].mean(),
            min_value=borough_data["metric_value"].min(),
            max_value=borough_data["metric_value"].max(),
            last_timestamp=pd.to_datetime(borough_data["analytics_timestamp"]).max(),
            calculation_method=f"Metric Radar for {borough}",
            confidence_level="95%",
        )

        return fig, stats

    def render_all_borough_radars(self) -> dict[str, tuple[go.Figure, StatisticsPanel]]:
        """Render radar charts for all 5 boroughs.

        Returns:
            Dictionary mapping borough codes to (figure, statistics) tuples
        """
        self.fetch_data()

        boroughs = sorted(self.data["borough"].unique().tolist())
        radars = {}

        for borough in boroughs:
            fig, stats = self.render_borough_metric_radar(borough)
            radars[f"radar_{borough}"] = (fig, stats)

        logger.info(f"Rendered {len(radars)} Metric radar charts")
        return radars
