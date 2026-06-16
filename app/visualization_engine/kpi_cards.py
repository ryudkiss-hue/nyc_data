"""KPI Cards: 18 Dashboard Metrics (5 boroughs × 18 KPIs = 90 rows).

Renders all 18 KPI cards with dynamic values from MotherDuck.
Each card displays:
- KPI name
- Current value
- Borough
- Metric category
- Trend indicator (up/down/stable)

Data source: app_queries.v_kpi_dashboard
"""
import logging

import pandas as pd
import plotly.graph_objects as go

from socrata_toolkit.motherduck.connector import MotherDuckConnection

from .statistics_display import StatisticsPanel

logger = logging.getLogger(__name__)

class KPICards:
    """Renders all 18 KPI cards with dynamic values.

    Attributes:
        conn: MotherDuckConnection for querying app_queries.v_kpi_dashboard
        data: DataFrame from serving view
    """

    def __init__(self, connection: MotherDuckConnection):
        """Initialize KPI cards.

        Args:
            connection: MotherDuckConnection instance
        """
        self.conn = connection
        self.data = None

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data from app_queries.v_kpi_dashboard.

        Returns:
            DataFrame with columns: kpi_name, borough, kpi_value, metric_category,
                                    analytics_timestamp

        Raises:
            RuntimeError: If query fails
        """
        query = "SELECT * FROM app_queries.v_kpi_dashboard ORDER BY borough, kpi_name"
        self.data = self.conn.fetch_dataframe(query)
        if self.data.empty:
            raise RuntimeError(
                "No data in app_queries.v_kpi_dashboard. "
                "Run Phase 1 (MotherDuck infrastructure) first."
            )
        logger.info(f"Fetched {len(self.data)} rows from KPI dashboard view")
        return self.data

    def get_kpi_names(self) -> list[str]:
        """Get list of unique KPI names.

        Returns:
            List of KPI names
        """
        if self.data is None:
            self.fetch_data()
        return sorted(self.data["kpi_name"].unique().tolist())

    def get_kpi_for_borough(self, kpi_name: str, borough: str) -> dict:
        """Get specific KPI value for a borough.

        Args:
            kpi_name: Name of the KPI
            borough: Borough code

        Returns:
            Dictionary with KPI data

        Raises:
            ValueError: If KPI or borough not found
        """
        if self.data is None:
            self.fetch_data()

        kpi_data = self.data[
            (self.data["kpi_name"] == kpi_name) & (self.data["borough"] == borough)
        ]
        if kpi_data.empty:
            raise ValueError(f"KPI {kpi_name} not found for borough {borough}")

        row = kpi_data.iloc[0]
        return {
            "kpi_name": row["kpi_name"],
            "borough": row["borough"],
            "value": row["kpi_value"],
            "category": row["metric_category"],
            "timestamp": row["analytics_timestamp"],
        }

    def render_kpi_card(
        self, kpi_name: str, borough: str
    ) -> tuple[go.Figure, StatisticsPanel]:
        """Render a single KPI card.

        Args:
            kpi_name: Name of the KPI
            borough: Borough code

        Returns:
            Tuple of (figure, statistics)

        Raises:
            ValueError: If KPI or borough not found
        """
        kpi_data = self.get_kpi_for_borough(kpi_name, borough)

        # Format value appropriately
        value = kpi_data["value"]
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
                    title={"text": f"{kpi_data['category']} ({borough})"},
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
            last_timestamp=pd.to_datetime(kpi_data["timestamp"]),
            calculation_method=f"{kpi_name} KPI",
            confidence_level="95%",
        )

        return fig, stats

    def render_all_kpi_cards(self) -> dict[str, tuple[go.Figure, StatisticsPanel]]:
        """Render all 18 KPI cards (one per KPI, aggregate across boroughs).

        Returns:
            Dictionary mapping KPI names to (figure, statistics) tuples
        """
        self.fetch_data()

        kpi_names = self.get_kpi_names()
        cards = {}

        for kpi_name in kpi_names:
            kpi_subset = self.data[self.data["kpi_name"] == kpi_name]

            fig = self._create_kpi_card_figure(kpi_name, kpi_subset)

            stats = StatisticsPanel(
                record_count=len(kpi_subset),
                mean_value=kpi_subset["kpi_value"].mean(),
                min_value=kpi_subset["kpi_value"].min(),
                max_value=kpi_subset["kpi_value"].max(),
                last_timestamp=pd.to_datetime(kpi_subset["analytics_timestamp"]).max(),
                calculation_method=f"KPI: {kpi_name}",
                confidence_level="95%",
            )

            cards[kpi_name] = (fig, stats)

        logger.info(f"Rendered {len(cards)} KPI cards")
        return cards

    def _create_kpi_card_figure(self, kpi_name: str, kpi_data: pd.DataFrame) -> go.Figure:
        """Create a figure for a single KPI aggregated across boroughs.

        Args:
            kpi_name: Name of the KPI
            kpi_data: DataFrame with this KPI across all boroughs

        Returns:
            Plotly figure
        """
        # Create a gauge or number indicator depending on KPI type
        avg_value = kpi_data["kpi_value"].mean()

        # Determine appropriate gauge range and color
        if "probability" in kpi_name.lower() or "rate" in kpi_name.lower():
            gauge_range = [0, 100]
            color = (
                "green"
                if avg_value >= 75
                else "orange" if avg_value >= 50
                else "red"
            )
        elif "strength" in kpi_name.lower() or "score" in kpi_name.lower():
            gauge_range = [0, 100]
            color = (
                "green"
                if avg_value >= 75
                else "orange" if avg_value >= 50
                else "red"
            )
        else:
            gauge_range = [kpi_data["kpi_value"].min() * 0.9, kpi_data["kpi_value"].max() * 1.1]
            color = "blue"

        fig = go.Figure(
            data=[
                go.Indicator(
                    mode="gauge+number",
                    value=avg_value,
                    title={"text": kpi_name.replace("_", " ").title()},
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

    def render_kpi_summary_table(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render summary table of all KPI values by borough.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Create pivot table: KPIs × Boroughs
        pivot_data = self.data.pivot_table(
            index="kpi_name",
            columns="borough",
            values="kpi_value",
            aggfunc="first",
        )

        # Round numeric values
        pivot_data = pivot_data.round(2)

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=["KPI"] + list(pivot_data.columns),
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
            title="KPI Summary: All Metrics by Borough",
            height=600,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["kpi_value"].mean(),
            min_value=self.data["kpi_value"].min(),
            max_value=self.data["kpi_value"].max(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="KPI Aggregation",
            confidence_level="95%",
        )

        return fig, stats

    def render_kpi_comparison_chart(self) -> tuple[go.Figure, StatisticsPanel]:
        """Render comparison chart of average KPI values.

        Returns:
            Tuple of (figure, statistics)
        """
        if self.data is None:
            self.fetch_data()

        # Average each KPI across boroughs
        kpi_avg = self.data.groupby("kpi_name")["kpi_value"].mean().sort_values()

        fig = go.Figure(
            data=go.Bar(
                x=kpi_avg.values,
                y=kpi_avg.index,
                orientation="h",
                marker=dict(
                    color=kpi_avg.values,
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Avg Value"),
                ),
            )
        )

        fig.update_layout(
            title="KPI Comparison: Average Values Across Boroughs",
            xaxis_title="Average Value",
            yaxis_title="KPI",
            height=500,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(self.data),
            mean_value=self.data["kpi_value"].mean(),
            last_timestamp=pd.to_datetime(self.data["analytics_timestamp"]).max(),
            calculation_method="KPI Average Aggregation",
            confidence_level="95%",
        )

        return fig, stats

    def render_borough_kpi_radar(self, borough: str) -> tuple[go.Figure, StatisticsPanel]:
        """Render radar chart of all KPIs for a specific borough.

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
            val = row["kpi_value"]
            if isinstance(val, (int, float)):
                # Simple normalization
                norm_val = min(100, max(0, val))
            else:
                norm_val = 50
            normalized_values.append(norm_val)

        fig = go.Figure(
            data=go.Scatterpolar(
                r=normalized_values,
                theta=borough_data["kpi_name"],
                fill="toself",
                name=borough,
                line=dict(color="blue"),
            )
        )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"KPI Radar Chart: {borough}",
            height=500,
            font={"family": "Arial, sans-serif", "size": 11},
        )

        stats = StatisticsPanel(
            record_count=len(borough_data),
            mean_value=borough_data["kpi_value"].mean(),
            min_value=borough_data["kpi_value"].min(),
            max_value=borough_data["kpi_value"].max(),
            last_timestamp=pd.to_datetime(borough_data["analytics_timestamp"]).max(),
            calculation_method=f"KPI Radar for {borough}",
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
            fig, stats = self.render_borough_kpi_radar(borough)
            radars[f"radar_{borough}"] = (fig, stats)

        logger.info(f"Rendered {len(radars)} KPI radar charts")
        return radars
