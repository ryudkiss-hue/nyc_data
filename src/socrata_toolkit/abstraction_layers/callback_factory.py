"""CallbackFactory: Auto-generated Dash callbacks with consistent pattern."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from dash import Input, Output, callback, html

logger = logging.getLogger(__name__)


class CallbackFactory:
    """Factory for generating Dash callbacks with consistent pattern.

    Implements pattern:
        User filter change → Fetch data → Calculate KPIs → Render visualization → Return figure + narrative

    Usage:
        factory = CallbackFactory(registry, analytics_engine, data_loader)
        factory.register_dataset_callback("inspection")
        factory.register_all_callbacks()
    """

    def __init__(
        self,
        registry: dict[str, Any],
        analytics_engine: Any | None = None,
        data_loader: Any | None = None,
    ):
        """Initialize callback factory.

        Args:
            registry: DATASET_REGISTRY configuration
            analytics_engine: AnalyticsEngine instance for KPI computation
            data_loader: DatasetLoader instance for fetching data
        """
        self.registry = registry
        self.analytics_engine = analytics_engine
        self.data_loader = data_loader
        self.datasets = registry.get("datasets", {})
        self.registered_callbacks = []

    def register_all_callbacks(self) -> None:
        """Register callbacks for all active datasets."""
        active_datasets = {
            k: v
            for k, v in self.datasets.items()
            if v.get("status") == "active"
        }

        for key, dataset in active_datasets.items():
            self.register_dataset_callback(key)

        logger.info(
            f"Registered {len(self.registered_callbacks)} Dash callbacks"
        )

    def register_dataset_callback(self, dataset_key: str) -> Callable:
        """Register callback for single dataset.

        Args:
            dataset_key: Dataset identifier

        Returns:
            Decorated callback function
        """
        if dataset_key not in self.datasets:
            raise ValueError(f"Unknown dataset: {dataset_key}")

        dataset = self.datasets[dataset_key]

        def callback_handler(filters: dict[str, Any]) -> tuple[Any, Any]:
            """Handle callback for dataset visualization.

            Args:
                filters: Filter dictionary from store

            Returns:
                Tuple of (figure, narrative_html)
            """
            try:
                # Step 1: Fetch data (with optional filtering)
                df = self._fetch_data(dataset_key, filters)

                # Step 2: Calculate KPIs if configured
                kpi_results = {}
                if dataset.get("kpis"):
                    kpi_results = self._compute_kpis(dataset_key, df)

                # Step 3: Render visualization
                fig = self._create_figure(dataset_key, df, dataset)

                # Step 4: Generate narrative insight
                narrative = self._generate_narrative(
                    dataset_key, df, kpi_results
                )

                return fig, narrative

            except Exception as e:
                logger.error(
                    f"Error in callback for {dataset_key}: {e}",
                    exc_info=True,
                )
                return {}, html.Div(f"Error: {str(e)}", style={"color": "red"})

        # Register callback with Dash
        callback_id = f"callback-{dataset_key}"
        decorated_callback = callback(
            Output(f"chart-{dataset_key}", "figure"),
            Output(f"narrative-{dataset_key}", "children"),
            Input("store-global-filters", "data"),
            prevent_initial_call=True,
        )(callback_handler)

        self.registered_callbacks.append(callback_id)
        logger.debug(f"Registered callback: {callback_id}")

        return decorated_callback

    def _fetch_data(
        self, dataset_key: str, filters: dict[str, Any]
    ) -> Any:
        """Fetch data for dataset with optional filtering.

        Args:
            dataset_key: Dataset identifier
            filters: Filter dictionary

        Returns:
            DataFrame
        """
        if self.data_loader is None:
            logger.warning("DatasetLoader not configured, returning empty DataFrame")
            import pandas as pd

            return pd.DataFrame()

        return self.data_loader.load(dataset_key, filters=filters)

    def _compute_kpis(
        self, dataset_key: str, df: Any
    ) -> dict[str, Any]:
        """Compute KPIs for dataset.

        Args:
            dataset_key: Dataset identifier
            df: DataFrame

        Returns:
            Dictionary of KPI name → result
        """
        if self.analytics_engine is None:
            logger.warning("AnalyticsEngine not configured, skipping KPI computation")
            return {}

        dataset = self.datasets[dataset_key]
        kpi_results = {}

        for kpi_name in dataset.get("kpis", []):
            try:
                result = self.analytics_engine.compute(
                    dataset_key=dataset_key,
                    kpi_name=kpi_name,
                    data=df,
                )
                kpi_results[kpi_name] = result
            except Exception as e:
                logger.error(
                    f"Error computing KPI {kpi_name} for {dataset_key}: {e}"
                )

        return kpi_results

    def _create_figure(
        self, dataset_key: str, df: Any, dataset: dict[str, Any]
    ) -> Any:
        """Create Plotly figure for dataset.

        Args:
            dataset_key: Dataset identifier
            df: DataFrame
            dataset: Dataset configuration

        Returns:
            plotly.graph_objects.Figure
        """
        try:
            from socrata_toolkit.abstraction_layers import (
                ChartFactory,
                ChartSpec,
            )

            viz = dataset.get("visualization", {})
            if not viz:
                logger.warning(f"No visualization config for {dataset_key}")
                return {}

            chart_factory = ChartFactory()
            spec = ChartSpec(
                chart_type=viz.get("default_chart", "vertical_bar"),
                data=df,
                iv_column=viz.get("iv_column"),
                dv_column=viz.get("dv_column"),
                title=viz.get("title_template", dataset["name"]),
                colors=viz.get("colors", {}),
                aggregation=viz.get("aggregation", "count"),
                limit_records=viz.get("limit_records"),
            )

            return chart_factory.create(spec)

        except Exception as e:
            logger.error(f"Error creating figure for {dataset_key}: {e}")
            return {}

    def _generate_narrative(
        self,
        dataset_key: str,
        df: Any,
        kpi_results: dict[str, Any],
    ) -> html.Div:
        """Generate insight narrative.

        Args:
            dataset_key: Dataset identifier
            df: DataFrame
            kpi_results: Dictionary of computed KPIs

        Returns:
            Dash html.Div component
        """
        try:
            import pandas as pd

            # Simple narrative generation (can be enhanced with LLM)
            row_count = len(df) if isinstance(df, pd.DataFrame) else 0
            narrative_text = f"Showing {row_count} records from {dataset_key}"

            if kpi_results:
                narrative_text += ". Key metrics: "
                narrative_text += ", ".join(
                    f"{k}={v.get('value', 'N/A')}"
                    for k, v in list(kpi_results.items())[:3]
                )

            return html.Div(
                narrative_text,
                style={
                    "padding": "12px",
                    "backgroundColor": "#f0f8ff",
                    "borderRadius": "4px",
                },
            )

        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return html.Div("Narrative generation failed")
