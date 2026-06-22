"""ChartFactory: Universal Plotly chart creation from specifications."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ChartSpec:
    """Specification for Plotly chart generation.

    Defines all parameters needed to create a chart:
    - Data source (DataFrame)
    - Chart type (bar, line, heatmap, etc.)
    - Independent/dependent variables
    - Styling (colors, title, annotations)
    - Data transformations (aggregation, limits)
    """

    chart_type: str
    data: pd.DataFrame
    iv_column: str
    dv_column: str
    title: str
    colors: dict[str, str] | None = None
    aggregation: str = "count"
    limit_records: int | None = None
    annotations: dict[str, Any] | None = None
    group_by: str | None = None

    def validate(self) -> None:
        """Validate spec before chart creation.

        Raises:
            ValueError: If spec is invalid (missing columns, etc.)
        """
        if self.iv_column not in self.data.columns:
            raise ValueError(
                f"IV column '{self.iv_column}' not in DataFrame. "
                f"Available: {self.data.columns.tolist()}"
            )

        if self.dv_column not in self.data.columns and self.dv_column != "none":
            raise ValueError(
                f"DV column '{self.dv_column}' not in DataFrame. "
                f"Available: {self.data.columns.tolist()}"
            )


class ChartFactory:
    """Factory for creating Plotly figures from specifications.

    Supports all common chart types:
    - Bar (vertical, horizontal, stacked)
    - Line (simple, area, range)
    - Heatmap
    - Choropleth (with geometry)
    - Gauge
    - Scatter
    - Treemap

    Usage:
        factory = ChartFactory()
        spec = ChartSpec(
            chart_type="vertical_bar",
            data=df,
            iv_column="borough",
            dv_column="violation_count",
            title="Violations by Borough",
        )
        fig = factory.create(spec)
    """

    def __init__(self):
        """Initialize factory with Plotly imports."""
        try:
            import plotly.express as px
            import plotly.graph_objects as go

            self.go = go
            self.px = px
        except ImportError as exc:
            raise ImportError(
                "Install plotly: pip install plotly"
            ) from exc

    def create(self, spec: ChartSpec) -> Any:
        """Create Plotly figure from specification.

        Args:
            spec: ChartSpec object with all chart parameters

        Returns:
            plotly.graph_objects.Figure

        Raises:
            ValueError: If chart_type unsupported or spec invalid
        """
        spec.validate()

        method_name = f"_create_{spec.chart_type}"
        if not hasattr(self, method_name):
            raise ValueError(
                f"Unsupported chart type: {spec.chart_type}. "
                f"Supported: bar, line, heatmap, gauge, scatter, treemap, choropleth"
            )

        method = getattr(self, method_name)
        fig = method(spec)
        return fig

    def _create_vertical_bar(self, spec: ChartSpec) -> Any:
        """Create vertical bar chart."""
        agg_df = (
            spec.data.groupby(spec.iv_column)[spec.dv_column]
            .agg(spec.aggregation)
            .reset_index()
        )
        agg_df = agg_df.sort_values(spec.dv_column, ascending=False)
        if spec.limit_records:
            agg_df = agg_df.head(spec.limit_records)

        fig = self.go.Figure(
            self.go.Bar(
                x=agg_df[spec.iv_column],
                y=agg_df[spec.dv_column],
                text=agg_df[spec.dv_column],
                textposition="auto",
                marker_color=spec.colors.get("primary", "#003087")
                if spec.colors
                else "#003087",
            )
        )
        fig.update_layout(
            title=spec.title,
            xaxis_title=spec.iv_column,
            yaxis_title=spec.dv_column,
            template="plotly_white",
        )
        return fig

    def _create_horizontal_bar(self, spec: ChartSpec) -> Any:
        """Create horizontal bar chart."""
        agg_df = (
            spec.data.groupby(spec.iv_column)[spec.dv_column]
            .agg(spec.aggregation)
            .reset_index()
        )
        agg_df = agg_df.sort_values(spec.dv_column, ascending=True)
        if spec.limit_records:
            agg_df = agg_df.head(spec.limit_records)

        fig = self.go.Figure(
            self.go.Bar(
                y=agg_df[spec.iv_column],
                x=agg_df[spec.dv_column],
                text=agg_df[spec.dv_column],
                textposition="auto",
                orientation="h",
                marker_color=spec.colors.get("primary", "#003087")
                if spec.colors
                else "#003087",
            )
        )
        fig.update_layout(
            title=spec.title,
            yaxis_title=spec.iv_column,
            xaxis_title=spec.dv_column,
            template="plotly_white",
        )
        return fig

    def _create_stacked_bar(self, spec: ChartSpec) -> Any:
        """Create stacked bar chart."""
        if spec.group_by is None:
            raise ValueError("Stacked bar requires group_by column")

        fig = self.px.bar(
            spec.data,
            x=spec.iv_column,
            y=spec.dv_column,
            color=spec.group_by,
            title=spec.title,
            barmode="stack",
        )
        fig.update_layout(template="plotly_white")
        return fig

    def _create_line(self, spec: ChartSpec) -> Any:
        """Create line chart."""
        agg_df = (
            spec.data.groupby(spec.iv_column)[spec.dv_column]
            .agg(spec.aggregation)
            .reset_index()
        )
        agg_df = agg_df.sort_values(spec.iv_column)

        fig = self.go.Figure(
            self.go.Scatter(
                x=agg_df[spec.iv_column],
                y=agg_df[spec.dv_column],
                mode="lines+markers",
                fill="tozeroy",
                line_color=spec.colors.get("primary", "#003087")
                if spec.colors
                else "#003087",
            )
        )
        fig.update_layout(
            title=spec.title,
            xaxis_title=spec.iv_column,
            yaxis_title=spec.dv_column,
            template="plotly_white",
        )
        return fig

    def _create_scatter(self, spec: ChartSpec) -> Any:
        """Create scatter plot."""
        fig = self.px.scatter(
            spec.data,
            x=spec.iv_column,
            y=spec.dv_column,
            title=spec.title,
        )
        fig.update_layout(template="plotly_white")
        return fig

    def _create_heatmap(self, spec: ChartSpec) -> Any:
        """Create heatmap."""
        if spec.group_by is None:
            raise ValueError("Heatmap requires group_by column for pivot")

        pivot_df = spec.data.pivot_table(
            index=spec.iv_column,
            columns=spec.group_by,
            values=spec.dv_column,
            aggfunc=spec.aggregation,
        )

        fig = self.go.Figure(
            self.go.Heatmap(z=pivot_df.values, x=pivot_df.columns, y=pivot_df.index)
        )
        fig.update_layout(title=spec.title, template="plotly_white")
        return fig

    def _create_gauge(self, spec: ChartSpec) -> Any:
        """Create gauge chart (single value)."""
        value = spec.data[spec.dv_column].iloc[0]
        max_val = 100

        fig = self.go.Figure(
            self.go.Indicator(
                mode="gauge+number",
                value=value,
                title={"text": spec.title},
                gauge={"axis": {"range": [0, max_val]}},
            )
        )
        return fig

    def _create_choropleth(self, spec: ChartSpec) -> Any:
        """Create choropleth map (requires geometry column).

        Note: Requires GeoDataFrame with 'the_geom' or 'geometry' column.
        """
        try:
            import geopandas as gpd
        except ImportError:
            raise ImportError(
                "Choropleth charts require geopandas. "
                "Install: pip install geopandas"
            )

        geo_df = gpd.GeoDataFrame(spec.data)
        if geo_df.crs is None:
            geo_df = geo_df.set_crs("EPSG:4326")

        fig = self.px.choropleth(
            geo_df,
            title=spec.title,
        )
        fig.update_layout(template="plotly_white")
        return fig

    def _create_treemap(self, spec: ChartSpec) -> Any:
        """Create treemap chart."""
        fig = self.px.treemap(
            spec.data,
            values=spec.dv_column,
            names=spec.iv_column,
            title=spec.title,
        )
        fig.update_layout(template="plotly_white")
        return fig
