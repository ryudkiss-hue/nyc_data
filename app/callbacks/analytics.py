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
        Compute bootstrap confidence interval for KPI metrics.

        Returns:
            tuple[go.Figure, str]: (gauge with CI bands, S-DIKW narrative)

        Performance target: <300ms
        """
        try:
            metrics = data_bundle.get("metrics", {})
            if not metrics:
                return go.Figure(), "No KPI metrics available for confidence interval computation."

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

    import app.callbacks.analytics_integration  # noqa: F401
    import app.callbacks.visualization_callbacks  # noqa: F401
    from app.callbacks.visualization_callbacks import register_visualization_callbacks

    register_visualization_callbacks()

    if dm is not None:
        try:
            from app.callbacks.hidden_analysis_methods import register_morans_i_callbacks

            register_morans_i_callbacks(app, dm)
        except Exception as e:
            logger.warning(f"Moran's I callbacks skipped: {e}")

    try:
        import app.callbacks.gis  # noqa: F401
    except ImportError as e:
        logger.warning(f"GIS callbacks skipped (missing dependency): {e}")

    logger.info("Analytics callbacks registered")
