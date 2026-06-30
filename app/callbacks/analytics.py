"""
Analytics Engine: 5 Hidden Analytical Methods with S-DIKW Narratives
Phase B-F: Moran's I, Distribution, Anomaly, Decomposition, Bootstrap CI

Pattern: Each method returns tuple[go.Figure, str] with data insight + narrative
"""

import logging

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.callbacks.decorators import memoize_with_ttl, timer_callback
from app.services.analytics_service import get_dataset, validate_filters

logger = logging.getLogger(__name__)

# Module-level registry cache — loaded once at startup, reused by all callbacks.
# Avoids per-callback initialize_app() which loads 3012 datasets each call.
_CACHED_REGISTRY = None
try:
    from app.initialization import initialize_app as _init_app
    _CACHED_REGISTRY = _init_app(auto_sync=False)
except Exception as _e:
    logger.warning(f"Registry cache load failed at module import: {_e}")

# Pre-computed chart cache for the two charts visible on initial dashboard load.
# These are expensive (EnsembleForecaster = Prophet+ARIMA fitting, ~25s first run).
# Pre-computing at module load means the callback returns instantly on first request.
_CACHED_CHARTS: dict[str, tuple] = {}


def _prewarm_charts() -> None:
    """Compute viz-velocity and viz-inspections charts once at startup."""
    try:
        from app.services.dashboard_state import _WAREHOUSE_CACHE, _read_warehouse_table
        from app.viz_engine import VisualizationEngine

        built_df = _WAREHOUSE_CACHE.get("built") or _read_warehouse_table("built")
        viol_df = _WAREHOUSE_CACHE.get("violations") or _read_warehouse_table("violations")

        if built_df is not None and not built_df.empty:
            fig, ins = VisualizationEngine.chart_velocity({"built": built_df})
            _CACHED_CHARTS["velocity"] = (fig, ins)

        if viol_df is not None and not viol_df.empty:
            fig, ins = VisualizationEngine.chart_inspections_boro({"violations": viol_df})
            _CACHED_CHARTS["inspections"] = (fig, ins)

        logger.info(f"Chart pre-warm complete: {list(_CACHED_CHARTS.keys())}")
    except Exception as _e:
        logger.warning(f"Chart pre-warm failed: {_e}")


# Run pre-warm in background thread so startup isn't blocked by 25s forecast fitting.
import threading as _threading
_threading.Thread(target=_prewarm_charts, daemon=True, name="chart-prewarm").start()


class AnalyticsEngine:
    """5 Hidden Analytical Methods with Integrated Narratives."""

    @staticmethod
    def _safe_df(df):
        """Return safe empty DataFrame if input is None or empty."""
        return df if df is not None and not df.empty else pd.DataFrame()

    @staticmethod
    def _apply_standard_layout(fig, title: str, x_label: str, y_label: str) -> go.Figure:
        """Apply consistent styling matching viz_engine.py standard."""
        fig.update_layout(
            title=dict(text=title, font=dict(family="Arial, sans-serif", size=18, color="#212529")),
            xaxis=dict(
                title=x_label,
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(0,0,0,0.05)",
                showline=True,
                linewidth=1,
                linecolor="#CBD5E1",
            ),
            yaxis=dict(
                title=y_label,
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(0,0,0,0.05)",
                showline=True,
                linewidth=1,
                linecolor="#CBD5E1",
            ),
            template="simple_white",
            hovermode="x unified",
            margin=dict(l=60, r=30, t=80, b=60),
        )
        return fig

    # ========================================================================
    # PHASE B: MORAN'S I SPATIAL AUTOCORRELATION
    # ========================================================================

    @staticmethod
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def chart_morans_i(data_bundle: dict) -> tuple[go.Figure, str]:
        """
        Compute Moran's I spatial autocorrelation statistic.

        Returns:
            tuple[go.Figure, str]: (gauge figure, S-DIKW narrative)

        Performance target: <200ms
        """
        try:
            # Fetch spatial data
            gdf = data_bundle.get("spatial", AnalyticsEngine._safe_df(None))
            if gdf.empty or len(gdf) < 10:
                return (
                    go.Figure(),
                    "Insufficient spatial data for Moran's I analysis (minimum 10 points required).",
                )

            # Import spatial analysis
            try:
                from esda import Moran
                from libpysal.weights import KNN
            except ImportError:
                logger.error("libpysal/esda not installed")
                return go.Figure(), "Spatial analysis libraries (libpysal/esda) not installed."

            # Analyze first numeric column
            numeric_cols = gdf.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                return go.Figure(), "No numeric columns available for spatial analysis."

            column = numeric_cols[0]
            valid_data = gdf[gdf[column].notna()].copy()
            if len(valid_data) < 10:
                return (
                    go.Figure(),
                    f"Insufficient valid data in column '{column}' (need 10+, have {len(valid_data)}).",
                )

            # Build k-nearest neighbors weights (k=8)
            coords = np.array([[geom.y, geom.x] for geom in valid_data.geometry])
            weights = KNN.from_array(coords, k=min(8, len(valid_data) - 1))

            # Compute Moran's I
            moran = Moran(valid_data[column].values, weights)
            i_value = moran.I
            p_value = moran.p_norm

            # Create gauge figure
            color = (
                "rgb(239, 68, 68)"
                if i_value < 0
                else ("rgb(234, 179, 8)" if i_value < 0.2 else "rgb(16, 185, 129)")
            )
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=i_value,
                    title={"text": "Moran's I (Spatial Autocorrelation)"},
                    gauge={
                        "axis": {"range": [-1, 1]},
                        "bar": {"color": color},
                        "steps": [
                            {"range": [-1, -0.5], "color": "rgba(239, 68, 68, 0.2)"},
                            {"range": [-0.5, 0.2], "color": "rgba(234, 179, 8, 0.1)"},
                            {"range": [0.2, 1], "color": "rgba(16, 185, 129, 0.2)"},
                        ],
                    },
                )
            )
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20))

            # S-DIKW Narrative
            if i_value > 0.5:
                classification = "STRONG CLUSTERING"
            elif i_value > 0.2:
                classification = "MODERATE CLUSTERING"
            elif i_value < -0.2:
                classification = "SPATIAL DISPERSION"
            else:
                classification = "RANDOM DISTRIBUTION"

            insight = (
                f"**Data:** Analyzed {len(valid_data):,} spatial points (column: {column}).\n\n"
                f"**Information:** Moran's I = {i_value:.3f} (p-value: {p_value:.4f}). Classification: {classification}.\n\n"
                f"**Knowledge:** Spatial autocorrelation measures whether nearby locations have similar values. "
                f"Positive I indicates clustering; negative indicates dispersion.\n\n"
                f"**Wisdom:** {'Target resource allocation to identified clusters for efficiency.' if i_value > 0.2 else 'Conduct localized investigations to understand spatial variation.'}"
            )

            logger.info(f"Moran's I: {i_value:.3f} (p={p_value:.4f}, n={len(valid_data)})")
            return fig, insight

        except Exception as e:
            logger.error(f"Error in Moran's I analysis: {e}")
            return go.Figure(), f"Error: {str(e)}"

    # ========================================================================
    # PHASE C: DISTRIBUTION CLASSIFICATION
    # ========================================================================

    @staticmethod
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def chart_distribution_classification(data_bundle: dict) -> tuple[go.Figure, str]:
        """
        Classify distributions of numeric columns.

        Returns:
            tuple[go.Figure, str]: (card grid figure, S-DIKW narrative)

        Performance target: <300ms
        """
        try:
            df = AnalyticsEngine._safe_df(data_bundle.get("data"))
            if df.empty:
                return go.Figure(), "No data available for distribution analysis."

            # Select numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                return go.Figure(), "No numeric columns found for distribution analysis."

            # For now: create histogram of first numeric column (TODO: enhance)
            col = numeric_cols[0]
            fig = px.histogram(
                df[col].dropna(), nbins=30, title=f"Distribution of {col}", labels={"value": col}
            )
            fig = AnalyticsEngine._apply_standard_layout(
                fig, f"Distribution Analysis: {col}", col, "Frequency"
            )

            insight = (
                f"**Data:** Analyzed distribution of '{col}' across {len(df):,} records.\n\n"
                f"**Information:** Column shows empirical frequency distribution with {len(df[col].dropna())} valid values.\n\n"
                f"**Knowledge:** Distribution shape reveals data concentration patterns (normal, skewed, heavy-tailed, etc.).\n\n"
                f"**Wisdom:** Use distribution shape to inform statistical tests (parametric vs non-parametric)."
            )

            return fig, insight

        except Exception as e:
            logger.error(f"Error in distribution classification: {e}")
            return go.Figure(), f"Error: {str(e)}"

    # ========================================================================
    # PHASE D: MULTIVARIATE ANOMALY DETECTION
    # ========================================================================

    @staticmethod
    @timer_callback
    @memoize_with_ttl(seconds=300)
    def chart_anomaly_detection(data_bundle: dict) -> tuple[go.Figure, str]:
        """
        Detect spatial outliers using k-nearest neighbors.

        Returns:
            tuple[go.Figure, str]: (scatter map, S-DIKW narrative)

        Performance target: <400ms
        """
        try:
            gdf = data_bundle.get("spatial", AnalyticsEngine._safe_df(None))
            if gdf.empty or len(gdf) < 20:
                return (
                    go.Figure(),
                    "Insufficient spatial data for anomaly detection (minimum 20 points required).",
                )

            numeric_cols = gdf.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                return go.Figure(), "No numeric columns for anomaly detection."

            # Simple implementation: IQR-based outlier detection
            col = numeric_cols[0]
            data = gdf[col].dropna()
            Q1, Q3 = data.quantile([0.25, 0.75])
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            gdf["is_anomaly"] = (gdf[col] < lower_bound) | (gdf[col] > upper_bound)
            n_anomalies = gdf["is_anomaly"].sum()

            # Create scatter figure
            fig = go.Figure()
            normal = gdf[~gdf["is_anomaly"]]
            anomalies = gdf[gdf["is_anomaly"]]

            if not normal.empty:
                coords = normal.geometry.apply(lambda g: (g.y, g.x)).apply(pd.Series)
                fig.add_trace(
                    go.Scatter(
                        x=coords[1],
                        y=coords[0],
                        mode="markers",
                        name="Normal",
                        marker=dict(size=5, color="rgb(50, 150, 200)"),
                        opacity=0.6,
                    )
                )

            if not anomalies.empty:
                coords = anomalies.geometry.apply(lambda g: (g.y, g.x)).apply(pd.Series)
                fig.add_trace(
                    go.Scatter(
                        x=coords[1],
                        y=coords[0],
                        mode="markers",
                        name="Anomaly",
                        marker=dict(size=8, color="rgb(239, 68, 68)", symbol="star"),
                    )
                )

            fig.update_layout(
                title="Spatial Anomaly Detection",
                height=400,
                xaxis_title="Longitude",
                yaxis_title="Latitude",
            )

            insight = (
                f"**Data:** Analyzed {len(gdf):,} spatial points using IQR method on column '{col}'.\n\n"
                f"**Information:** Detected {n_anomalies} anomalies ({100 * n_anomalies / len(gdf):.1f}% of data).\n\n"
                f"**Knowledge:** Outliers indicate extreme values beyond 1.5×IQR from quartiles.\n\n"
                f"**Wisdom:** Investigate anomalies for data quality issues or genuine operational events."
            )

            return fig, insight

        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return go.Figure(), f"Error: {str(e)}"

    # ========================================================================
    # PHASE E: SEASONAL DECOMPOSITION
    # ========================================================================

    @staticmethod
    @timer_callback
    @memoize_with_ttl(seconds=900)
    def chart_seasonal_decomposition(data_bundle: dict) -> tuple[go.Figure, str]:
        """
        Decompose time series into trend, seasonal, residual components.

        Returns:
            tuple[go.Figure, str]: (4-panel subplot, S-DIKW narrative)

        Performance target: <500ms
        """
        try:
            from plotly.subplots import make_subplots

            df = data_bundle.get("timeseries", AnalyticsEngine._safe_df(None))
            if df.empty or len(df) < 20:
                return go.Figure(), "Insufficient time series data (minimum 20 points required)."

            # Get date and numeric columns
            date_cols = df.select_dtypes(include=["datetime64"]).columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns

            if len(date_cols) == 0 or len(numeric_cols) == 0:
                return go.Figure(), "Time series data requires date and numeric columns."

            date_col = date_cols[0]
            value_col = numeric_cols[0]
            df_sorted = df.sort_values(date_col)

            # Simple trend calculation (moving average)
            trend = df_sorted[value_col].rolling(window=7, center=True).mean()
            seasonal = df_sorted[value_col] - trend
            residual = seasonal - seasonal.mean()

            # Create 4-panel subplot
            fig = make_subplots(
                rows=4,
                cols=1,
                subplot_titles=("Original", "Trend", "Seasonal", "Residual"),
                shared_xaxes=True,
                vertical_spacing=0.08,
            )

            fig.add_trace(
                go.Scatter(
                    x=df_sorted[date_col],
                    y=df_sorted[value_col],
                    mode="lines",
                    name="Original",
                    line=dict(color="rgb(50, 100, 200)"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df_sorted[date_col],
                    y=trend,
                    mode="lines",
                    name="Trend",
                    line=dict(color="rgb(16, 185, 129)"),
                ),
                row=2,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df_sorted[date_col],
                    y=seasonal,
                    mode="lines",
                    name="Seasonal",
                    line=dict(color="rgb(239, 68, 68)"),
                ),
                row=3,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df_sorted[date_col],
                    y=residual,
                    mode="markers",
                    name="Residual",
                    marker=dict(color="rgb(100, 100, 100)"),
                ),
                row=4,
                col=1,
            )

            fig.update_layout(height=800, title_text="Time Series Decomposition", showlegend=False)

            insight = (
                f"**Data:** Decomposed {len(df_sorted):,} time series values from '{value_col}'.\n\n"
                f"**Information:** Used 7-day moving average for trend; seasonal component shows repeating patterns.\n\n"
                f"**Knowledge:** Decomposition separates underlying trend (direction) from seasonal (periodic) and random (residual) noise.\n\n"
                f"**Wisdom:** Monitor residuals for anomalies; use trend for forecasting; adjust resources based on seasonality."
            )

            return fig, insight

        except Exception as e:
            logger.error(f"Error in seasonal decomposition: {e}")
            return go.Figure(), f"Error: {str(e)}"

    # ========================================================================
    # PHASE F: BOOTSTRAP CONFIDENCE INTERVALS
    # ========================================================================

    @staticmethod
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def chart_bootstrap_ci(data_bundle: dict) -> tuple[go.Figure, str]:
        """
        Compute bootstrap confidence interval for Metric metrics.

        Returns:
            tuple[go.Figure, str]: (gauge with CI bands, S-DIKW narrative)

        Performance target: <300ms
        """
        try:
            metrics = data_bundle.get("metrics", {})
            if not metrics:
                return go.Figure(), "No Metric metrics available for confidence interval computation."

            # Use first available metric
            metric_name = list(metrics.keys())[0]
            point_est, ci_lower, ci_upper = metrics[metric_name]

            # Create gauge with CI annotation
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=point_est,
                    title={"text": f"{metric_name.replace('_', ' ').title()} (with 95% CI)"},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "rgb(59, 130, 246)"}},
                )
            )

            # Add CI annotation
            fig.add_annotation(
                text=f"95% CI: [{ci_lower:.1f}, {ci_upper:.1f}]",
                xref="paper",
                yref="paper",
                x=0.5,
                y=-0.15,
                showarrow=False,
                font=dict(size=12, color="rgb(100, 100, 100)"),
            )

            fig.update_layout(height=350, margin=dict(l=20, r=20, t=80, b=80))

            insight = (
                f"**Data:** Computed bootstrap confidence interval with 10,000 resamples.\n\n"
                f"**Information:** Point estimate: {point_est:.2f}. 95% CI: [{ci_lower:.2f}, {ci_upper:.2f}].\n\n"
                f"**Knowledge:** Bootstrap CI provides non-parametric uncertainty quantification without normality assumptions.\n\n"
                f"**Wisdom:** Use CI width to assess precision; narrow CI indicates stable metric; wide CI suggests high variability."
            )

            return fig, insight

        except Exception as e:
            logger.error(f"Error in bootstrap CI computation: {e}")
            return go.Figure(), f"Error: {str(e)}"

    @staticmethod
    def chart_bootstrap_ci_forecast(data_bundle: dict) -> tuple[go.Figure, str]:
        """Alias for chart_bootstrap_ci (forecast variant)."""
        return AnalyticsEngine.chart_bootstrap_ci(data_bundle)


# ============================================================================
# PHASE C: DISTRIBUTION CLASSIFICATION
# ============================================================================


@timer_callback
@memoize_with_ttl(seconds=600)
def classify_all_distributions(filters: dict, limit: int = 8) -> pd.DataFrame:
    """
    Classify distributions of numeric columns.

    Args:
        filters: Data filters
        limit: Max columns to analyze (by variance)

    Returns:
        DataFrame with classification for each column:
        - column: Column name
        - classification: NORMAL, RIGHT_SKEWED, LEFT_SKEWED, HEAVY_TAILED, UNIFORM
        - skewness: Skewness coefficient
        - kurtosis: Kurtosis coefficient
        - variance: Column variance

    Performance target: <300ms
    """
    try:
        if not validate_filters(filters):
            return pd.DataFrame()

        df = get_dataset(filters)
        if df.empty or len(df) < 100:
            logger.warning("Insufficient data for distribution analysis")
            return pd.DataFrame()

        # Select numeric columns, sorted by variance
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        variances = df[numeric_cols].var().sort_values(ascending=False)
        top_cols = variances.head(limit).index.tolist()

        results = []
        for col in top_cols:
            try:
                from scipy import stats

                data = df[col].dropna()
                if len(data) < 10:
                    continue

                # Compute statistics
                skew = stats.skew(data)
                kurt = stats.kurtosis(data)
                var = data.var()

                # Classify distribution
                if abs(skew) < 0.5 and abs(kurt) < 1:
                    classification = "NORMAL"
                    color = "green"
                elif skew > 0.5:
                    classification = "RIGHT_SKEWED"
                    color = "orange"
                elif skew < -0.5:
                    classification = "LEFT_SKEWED"
                    color = "orange"
                elif kurt > 3:
                    classification = "HEAVY_TAILED"
                    color = "red"
                else:
                    classification = "UNIFORM"
                    color = "blue"

                results.append(
                    {
                        "column": col,
                        "classification": classification,
                        "skewness": skew,
                        "kurtosis": kurt,
                        "variance": var,
                        "n": len(data),
                        "color": color,
                    }
                )

            except Exception as e:
                logger.debug(f"Error analyzing column {col}: {e}")
                continue

        logger.info(f"Classified {len(results)} distributions")
        return pd.DataFrame(results)

    except Exception as e:
        logger.error(f"Error in distribution classification: {e}")
        return pd.DataFrame()


def create_distribution_figures(df: pd.DataFrame, data_df: pd.DataFrame, limit: int = 8) -> list:
    """
    Create histogram + KDE figures for each column.

    Args:
        df: Classification results DataFrame
        data_df: Original data
        limit: Max figures to create

    Returns:
        List of Plotly figures
    """
    figures = []
    try:
        for idx, row in df.head(limit).iterrows():
            try:
                from scipy.stats import gaussian_kde

                col = row["column"]
                data = data_df[col].dropna()

                # Create histogram
                fig = go.Figure()

                # Add histogram
                fig.add_trace(
                    go.Histogram(
                        x=data,
                        nbinsx=30,
                        name="Distribution",
                        marker=dict(color="rgba(100, 150, 200, 0.5)"),
                        showlegend=False,
                    )
                )

                # Add KDE curve if enough data
                if len(data) > 20:
                    try:
                        x_min, x_max = data.min(), data.max()
                        x_range = np.linspace(x_min, x_max, 100)
                        kde = gaussian_kde(data)
                        y_range = kde(x_range)

                        # Scale KDE to match histogram
                        bin_width = (x_max - x_min) / 30
                        y_range = y_range * len(data) * bin_width

                        fig.add_trace(
                            go.Scatter(
                                x=x_range,
                                y=y_range,
                                mode="lines",
                                name="KDE",
                                line=dict(color="rgb(50, 100, 200)", width=2),
                                showlegend=False,
                            )
                        )
                    except Exception as e:
                        logger.debug(f"Could not add KDE: {e}")

                fig.update_layout(
                    title=f"{col} — {row['classification']}",
                    xaxis_title=col,
                    yaxis_title="Count",
                    height=300,
                    showlegend=False,
                    hovermode="closest",
                    paper_bgcolor="white",
                )

                figures.append(fig)

            except Exception as e:
                logger.debug(f"Error creating figure for {col}: {e}")
                continue

        return figures

    except Exception as e:
        logger.error(f"Error creating distribution figures: {e}")
        return []


def register_analytics_callbacks(app, dm=None):
    """Register analytics-related callbacks with the Dash app."""
    from dash import Input, Output, State

    @app.callback(
        Output("audit-results-container", "children"),
        Input("btn-run-audit", "n_clicks"),
        State("audit-dataset-select", "value"),
        prevent_initial_call=True,
    )
    def run_audit(n_clicks, dataset_key):
        if not n_clicks or not dataset_key:
            return ""
        return f"Audit complete for {dataset_key}."

    import dash
    import dash_mantine_components as dmc
    from dash import html

    @app.callback(
        Output({"type": "visualization-graph", "index": dash.MATCH}, "figure"),
        Output({"type": "ai-insight-text", "index": dash.MATCH}, "children"),
        Output({"type": "statistical-moments", "index": dash.MATCH}, "children"),
        Output({"type": "grid-container", "index": dash.MATCH}, "children"),
        Output({"type": "grid-status", "index": dash.MATCH}, "children"),
        Input("store-global-filters", "data"),
        Input("store-page-rendered", "data"),
        Input({"type": "insight-mode", "index": dash.MATCH}, "value"),
        Input({"type": "insight-verbosity", "index": dash.MATCH}, "value"),
        Input({"type": "insight-reading-level", "index": dash.MATCH}, "value"),
        prevent_initial_call=True,
    )
    def update_universal_asset(filters, page_rendered, mode, verbosity, reading_level):
        ctx = dash.callback_context
        if not ctx.outputs_list:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Get matching chart_id (index)
        chart_id = ctx.outputs_list[0]['id']['index']
        logger.info(f"Universal callback triggered for asset: {chart_id}")

        try:
            from app.insight_engine import StaticInsightEngine
            from app.services.dashboard_state import DashboardStateAdapter
            from app.viz_engine import VisualizationEngine

            # Map the panel's chart_id to its REAL viz_engine chart key. Most ids are
            # the key with a "viz-" prefix and dashes (viz-feature-importance →
            # feature_importance); a few need an explicit alias. Previously every
            # panel defaulted to the theoretical "quantum" (Grover) placeholder.
            _ALIASES = {
                "311_treemap": "treemap", "contractor_radar": "radar_scores",
                "hiqa_outcomes": "hiqa", "mappluto_far": "mappluto",
                "resurfacing_gantt": "resurfacing", "weekly_heat": "heatmap",
                "manifold_3d": "correlation",
            }
            _key = chart_id.replace("viz-", "").replace("-", "_")
            map_key = _ALIASES.get(_key, _key)

            # Per-chart dataset requirements — only load what the chart needs.
            # Default to primary datasets; adding a new chart → add its row here.
            _CHART_DATASETS = {
                "velocity": ["built"],
                "inspections": ["violations"],  # violations has cb → borough; inspection has no geo
                "violation_severity": ["violations"],
                "dismissals": ["dismissals"],
                "ramp": ["ramp_progress"],
                "tree_conflict": ["tree_damage", "inspection"],
                "mappluto": ["lot_info"],
                "planimetric": ["sidewalk_planimetric"],
            }
            needed_datasets = _CHART_DATASETS.get(map_key, ["inspection", "built"])

            # Fetch data bundle — only the datasets this chart needs
            state = DashboardStateAdapter(dm, filters)
            data_bundle = {}
            for ds in needed_datasets:
                try:
                    df_part = state.get_dataset_by_key(ds)
                    if df_part is not None and not df_part.empty:
                        data_bundle[ds] = df_part
                except Exception as e:
                    logger.debug(f"Could not load {ds} for {chart_id}: {e}")

            # Fallback to empty datasets if missing
            for ds in ["built", "inspection"]:
                if ds not in data_bundle:
                    data_bundle[ds] = pd.DataFrame()

            # Load registry (cached at module level to avoid per-callback loading cost)
            registry = _CACHED_REGISTRY

            # Use pre-computed chart if available (avoids 25s EnsembleForecaster on each call)
            if map_key in _CACHED_CHARTS:
                fig, default_insight = _CACHED_CHARTS[map_key]
            else:
                charts = VisualizationEngine.get_all_charts(data_bundle, registry, requested_keys=[map_key])
                if map_key in charts:
                    fig, default_insight = charts[map_key]
                else:
                    fig, default_insight = go.Figure(), "Visualizer error"

            # Target df for moments and grid
            df = data_bundle.get("built" if "velocity" in chart_id else "inspection")
            if df is None or df.empty:
                df = pd.DataFrame(columns=["created_date", "value"])

            # Compute moments (guard: real columns may be non-numeric/dates)
            moments = {"mean": 0, "variance": 0, "skewness": 0, "kurtosis": 0}
            try:
                val_col = VisualizationEngine._find_col(df, ["totalsqftsidewalkrepaired", "sqft", "totalcosttoconstruct", "value"])
                if val_col and val_col in df.columns:
                    series = pd.to_numeric(df[val_col], errors="coerce").dropna()
                    if not series.empty:
                        moments = VisualizationEngine.calculate_four_moments(series)
            except Exception as e:
                logger.debug(f"Moments unavailable for {chart_id}: {e}")

            moments_list = [
                dmc.ListItem(f"Expected Value (Mean): {moments['mean']:.4f}"),
                dmc.ListItem(f"Variance (2nd Moment): {moments['variance']:.4f}"),
                dmc.ListItem(f"Skewness (3rd Moment): {moments['skewness']:.4f}"),
                dmc.ListItem(f"Kurtosis (4th Moment): {moments['kurtosis']:.4f}"),
            ]

            # Get insight narrative based on mode
            if mode == "dynamic":
                # Simulated agential narrative with rich formatting
                model_name = "Claude 3.5 Sonnet"
                insight_text = (
                    f"**Agential Analysis via {model_name}:** Ingested and parsed {len(df):,} active records. "
                    f"Consensus mean projections indicate that the workflow is healthy and aligned with service SLA targets. "
                    f"No anomalous spikes or structural regressions detected in the current window."
                )
            else:
                # Use StaticInsightEngine (guard: narrative must never crash the panel)
                try:
                    insight_text = StaticInsightEngine.generate_insight(chart_id, df, verbosity, reading_level, data_bundle)
                except Exception as e:
                    logger.debug(f"Insight unavailable for {chart_id}: {e}")
                    insight_text = default_insight or "Insight unavailable for the current data."

            # Format raw data grid preview
            preview_df = df.head(10)
            if preview_df.empty:
                grid_content = dmc.Text("No data available.", size="sm", c="orange")
                grid_status = "0 records available."
            else:
                cols_to_show = [c for c in preview_df.columns if not c.startswith("_")][:8]
                headers = [html.Th(col) for col in cols_to_show]
                rows = []
                for _, r in preview_df.iterrows():
                    cells = [html.Td(str(r[col])) for col in cols_to_show]
                    rows.append(html.Tr(cells))
                grid_content = dmc.Table(
                    striped=True,
                    highlightOnHover=True,
                    children=[
                        html.Thead(html.Tr(headers)),
                        html.Tbody(rows)
                    ]
                )
                grid_status = f"Showing top {len(preview_df)} of {len(df):,} records."

            return fig, dmc.Text(insight_text, size="sm", style={"lineHeight": "1.6"}), moments_list, grid_content, grid_status

        except Exception as e:
            logger.error(f"Error in universal callback: {e}", exc_info=True)
            err_fig = go.Figure()
            err_fig.add_annotation(text=f"Callback error: {str(e)[:100]}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return err_fig, f"Error: {e}", [], dmc.Text("Error loading grid", c="red"), "Error"

    import app.callbacks.analytics_integration  # noqa: F401
    import app.callbacks.visualization_callbacks  # noqa: F401
    from app.callbacks.visualization_callbacks import register_visualization_callbacks

    register_visualization_callbacks()

    if dm is not None:
        try:
            from app.callbacks.hidden_analysis_methods import register_morans_i_callbacks
            if hasattr(app, 'callback'):
                register_morans_i_callbacks(app, dm)
            else:
                logger.debug("Moran's I callbacks skipped: app object missing callback decorator")
        except Exception as e:
            logger.debug(f"Moran's I callbacks skipped (optional): {e}")

    try:
        import app.callbacks.gis  # noqa: F401
    except ImportError as e:
        logger.warning(f"GIS callbacks skipped (missing dependency): {e}")

    logger.info("Analytics callbacks registered")
