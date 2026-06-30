"""
Dash callbacks for 5 hidden analysis methods.

Exposes advanced analytical capabilities:
1. Moran's I Spatial Autocorrelation (GIS Dashboard)
2. Distribution Classification (Analytics → Data Shapes)
3. Multivariate Anomaly Detection (Quality Dashboard)
4. Seasonal Decomposition (Labor View)
5. Bootstrap Confidence Intervals (Metric Cards)
"""

import logging
import time
from functools import wraps
from typing import Any, Callable

import dash_mantine_components as dmc
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc
from shapely.geometry import Point

from socrata_toolkit.analysis_advanced import (
    classify_distribution,
)
from socrata_toolkit.spatial.analytics import SpatialAnomalyDetector, moran_i

logger = logging.getLogger(__name__)

# ==========================================
# DECORATOR: Performance Monitoring
# ==========================================

def timer_callback(func: Callable) -> Callable:
    """Decorator to measure callback execution time."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            if elapsed > 0.5:
                logger.warning(f"SLOW: {func.__name__} took {elapsed:.3f}s")
            else:
                logger.info(f"OK: {func.__name__} took {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"ERROR: {func.__name__} failed after {elapsed:.3f}s: {e}")
            raise

    return wrapper

def memoize_with_ttl(seconds: int = 600):
    """Decorator to cache callback results with TTL (time-to-live)."""

    def decorator(func: Callable) -> Callable:
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from args/kwargs
            key = (
                args,
                tuple(sorted(kwargs.items()) if kwargs else []),
            )

            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < seconds:
                    logger.debug(f"CACHE HIT: {func.__name__}")
                    return result

            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            logger.debug(f"CACHE SET: {func.__name__} (TTL={seconds}s)")
            return result

        return wrapper

    return decorator

# ==========================================
# HELPER FUNCTIONS
# ==========================================

from app.services.dashboard_state import DashboardStateAdapter


def create_error_figure(error_msg: str) -> go.Figure:
    """Create error placeholder figure."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"Error: {error_msg[:100]}", xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False, font=dict(size=12, color="red"),
    )
    return fig

# ==========================================
# METHOD 1: MORAN'S I SPATIAL AUTOCORRELATION
# ==========================================

def register_morans_i_callbacks(app, dm_instance):
    """Register Moran's I callback for GIS Dashboard."""

    @app.callback(
        Output("moran-i-gauge", "figure"),
        Output("moran-i-interpretation", "children"),
        Output("moran-i-metadata", "children"),
        Input("store-global-filters", "data"),
        Input("moran-i-column-select", "value"),
        prevent_initial_call=True,
    )
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def update_morans_i(filters, column):
        """
        Compute Moran's I spatial autocorrelation for sidewalk data.

        Returns:
            - Gauge figure (I value -1 to +1)
            - Interpretation text
            - Metadata (n, k, p-value if available)
        """
        try:
            if not filters or not column:
                return (
                    create_error_figure("No column selected"),
                    dmc.Text("Select a numeric column to analyze", c="gray"),
                    dmc.Text("", size="xs"),
                )

            # Fetch spatial data
            state = DashboardStateAdapter(dm_instance, filters)
            df = state.get_dataset_by_key("inspection")
            if df.empty:
                return (
                    create_error_figure("No data available"),
                    dmc.Text("No data for selected filters", c="gray"),
                    dmc.Text("", size="xs"),
                )

            # Identify lat/lon columns
            lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
            lon_col = next((c for c in df.columns if "lon" in c.lower()), None)

            if not (lat_col and lon_col):
                return (
                    create_error_figure("No spatial columns found"),
                    dmc.Text("Dataset lacks latitude/longitude columns", c="gray"),
                    dmc.Text("", size="xs"),
                )

            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(
                df,
                geometry=[
                    Point(xy)
                    for xy in zip(df[lon_col], df[lat_col])
                ],
                crs="EPSG:4326",
            )

            # Compute Moran's I
            i_value = moran_i(gdf, column, max_neighbors=8)

            if i_value is None:
                return (
                    create_error_figure("Moran's I computation failed"),
                    dmc.Text("Insufficient data or invalid column", c="gray"),
                    dmc.Text("", size="xs"),
                )

            # Create gauge figure
            fig = go.Figure(
                data=[
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=i_value,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": f"Moran's I ({column})"},
                        gauge={
                            "axis": {"range": [-1, 1]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [-1, -0.3], "color": "lightcoral"},
                                {"range": [-0.3, 0.3], "color": "lightyellow"},
                                {"range": [0.3, 1], "color": "lightgreen"},
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 0,
                            },
                        },
                    )
                ]
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=50, b=20))

            # Interpretation text
            if i_value > 0.3:
                interpretation = f"Strong spatial clustering detected (I = {i_value:.3f}). Similar sidewalk conditions cluster geographically."
                color = "green"
            elif i_value < -0.3:
                interpretation = f"Spatial dispersion detected (I = {i_value:.3f}). Opposite conditions are near each other."
                color = "red"
            else:
                interpretation = f"Random spatial pattern (I = {i_value:.3f}). No significant spatial autocorrelation."
                color = "gray"

            interpretation_card = dmc.Card(
                [
                    dmc.Group(
                        [
                            dmc.Badge(
                                interpretation.split(".")[0],
                                color=color,
                                size="lg",
                            ),
                        ]
                    ),
                    dmc.Text(interpretation, size="sm", mt="md"),
                ],
                p="md",
            )

            # Metadata
            n = len(gdf)
            metadata = dmc.Group(
                [
                    dmc.Badge(f"n = {n:,}", color="blue", variant="light"),
                    dmc.Badge("k = 8 neighbors", color="blue", variant="light"),
                    dmc.Badge("Method: k-NN", color="blue", variant="light"),
                ],
                size="sm",
                mt="sm",
            )

            return fig, interpretation_card, metadata

        except Exception as e:
            logger.error(f"Error in update_morans_i: {e}")
            return (
                create_error_figure(str(e)),
                dmc.Text(f"Error: {str(e)}", c="red"),
                dmc.Text("", size="xs"),
            )

# ==========================================
# METHOD 2: DISTRIBUTION CLASSIFICATION
# ==========================================

def register_distribution_callbacks(app, dm_instance):
    """Register distribution classification callbacks."""

    @app.callback(
        Output("distribution-card-grid", "children"),
        Input("store-global-filters", "data"),
        Input("distribution-column-limit", "value"),
        prevent_initial_call=True,
    )
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def update_distributions(filters, limit):
        """
        Classify distributions for numeric columns.

        Returns:
            Grid of distribution cards (each with histogram + classification)
        """
        try:
            if not filters:
                return [dmc.Text("No data selected", c="gray")]

            # Fetch data
            state = DashboardStateAdapter(dm_instance, filters)
            df = state.get_dataset_by_key("inspection")
            if df.empty:
                return [dmc.Text("No data for selected filters", c="gray")]

            # Classify all distributions
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_cols:
                return [dmc.Text("No numeric columns found", c="gray")]

            # Sort by variance, take top N
            variances = df[numeric_cols].var().sort_values(ascending=False)
            top_cols = variances.head(limit or 8).index.tolist()

            cards = []
            for col in top_cols:
                try:
                    dist_info = classify_distribution(df, col)

                    # Create histogram with KDE
                    series = pd.to_numeric(df[col], errors="coerce").dropna()
                    fig = go.Figure()
                    fig.add_trace(
                        go.Histogram(x=series, nbinsx=30, name="Data", opacity=0.7)
                    )
                    fig.update_layout(
                        height=250,
                        title=f"Distribution: {col}",
                        xaxis_title="Value",
                        yaxis_title="Frequency",
                        showlegend=False,
                        margin=dict(l=30, r=30, t=40, b=30),
                    )

                    # Classification badge color
                    color_map = {
                        "normal": "green",
                        "right_skewed": "orange",
                        "left_skewed": "orange",
                        "heavy_tailed": "red",
                        "uniform": "blue",
                        "sparse": "gray",
                    }
                    color = color_map.get(dist_info.classification, "gray")

                    # Create card
                    card = dmc.Card(
                        [
                            dmc.Group(
                                [
                                    dmc.Badge(
                                        dist_info.classification.upper().replace(
                                            "_", " "
                                        ),
                                        color=color,
                                        size="lg",
                                    ),
                                    dmc.Text(
                                        f"n = {dist_info.sample_size:,}",
                                        size="xs",
                                        c="gray",
                                    ),
                                ],
                                justify="space-between",
                                mb="sm",
                            ),
                            dcc.Graph(figure=fig, config={"displayModeBar": False}),
                            dmc.Stack(
                                [
                                    dmc.Text(
                                        f"Skewness: {dist_info.skewness:.3f}",
                                        size="xs",
                                    ),
                                    dmc.Text(
                                        f"Kurtosis: {dist_info.kurtosis:.3f}",
                                        size="xs",
                                    ),
                                    dmc.Text(
                                        f"Unique ratio: {dist_info.unique_ratio:.1%}",
                                        size="xs",
                                    ),
                                ],
                                gap="xs",
                                mt="sm",
                            ),
                        ],
                        p="md",
                    )
                    cards.append(card)

                except Exception as e:
                    logger.error(f"Error classifying {col}: {e}")
                    continue

            if not cards:
                return [dmc.Text("No distributions could be classified", c="gray")]

            return dmc.SimpleGrid(
                cols={"base": 1, "sm": 2, "md": 3, "lg": 4}, children=cards
            )

        except Exception as e:
            logger.error(f"Error in update_distributions: {e}")
            return [dmc.Text(f"Error: {str(e)}", c="red")]

# ==========================================
# METHOD 3: MULTIVARIATE ANOMALY DETECTION
# ==========================================

def register_anomaly_detection_callbacks(app, dm_instance):
    """Register spatial anomaly detection callbacks."""

    @app.callback(
        Output("anomaly-scatter", "figure"),
        Output("anomaly-count-badge", "children"),
        Output("anomaly-table", "data"),
        Input("store-global-filters", "data"),
        Input("anomaly-column-select", "value"),
        Input("anomaly-k-slider", "value"),
        Input("anomaly-threshold-slider", "value"),
        prevent_initial_call=True,
    )
    @timer_callback
    @memoize_with_ttl(seconds=300)
    def update_anomalies(filters, column, k, threshold):
        """
        Detect spatial outliers in sidewalk data.

        Returns:
            - Scatter plot (lat/lon colored by anomaly status)
            - Count badge
            - Table of top anomalies
        """
        try:
            if not filters or not column:
                return (
                    create_error_figure("No column selected"),
                    dmc.Badge("0 anomalies", color="gray"),
                    [],
                )

            # Fetch data
            state = DashboardStateAdapter(dm_instance, filters)
            df = state.get_dataset_by_key("inspection")
            if df.empty:
                return (
                    create_error_figure("No data available"),
                    dmc.Badge("0 anomalies", color="gray"),
                    [],
                )

            # Find lat/lon columns
            lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
            lon_col = next((c for c in df.columns if "lon" in c.lower()), None)

            if not (lat_col and lon_col):
                return (
                    create_error_figure("No spatial columns"),
                    dmc.Badge("0 anomalies", color="gray"),
                    [],
                )

            # Prepare data
            df_clean = df[
                [lat_col, lon_col, column]
            ].copy()
            df_clean = df_clean.dropna()

            if len(df_clean) < k + 1:
                return (
                    create_error_figure(f"Insufficient data (need >{k} rows)"),
                    dmc.Badge("0 anomalies", color="gray"),
                    [],
                )

            # Extract coordinates and values
            coordinates = list(
                zip(df_clean[lon_col].values, df_clean[lat_col].values)
            )
            values = df_clean[column].values

            # Detect anomalies
            anomaly_indices = SpatialAnomalyDetector.detect_spatial_outliers(
                coordinates, values, k=k, std_threshold=threshold
            )

            # Create scatter figure
            colors = [
                "red" if i in anomaly_indices else "lightblue"
                for i in range(len(df_clean))
            ]
            sizes = [
                10 if i in anomaly_indices else 5
                for i in range(len(df_clean))
            ]

            fig = go.Figure(
                data=[
                    go.Scatter(
                        x=df_clean[lon_col],
                        y=df_clean[lat_col],
                        mode="markers",
                        marker=dict(
                            color=colors,
                            size=sizes,
                            opacity=0.7,
                        ),
                        text=[
                            f"Anomaly: {values[i]:.2f}"
                            if i in anomaly_indices
                            else f"Normal: {values[i]:.2f}"
                            for i in range(len(df_clean))
                        ],
                        hoverinfo="text",
                    )
                ]
            )
            fig.update_layout(
                title="Spatial Anomalies",
                xaxis_title="Longitude",
                yaxis_title="Latitude",
                height=400,
                showlegend=False,
                margin=dict(l=30, r=30, t=40, b=30),
            )

            # Badge
            badge = dmc.Badge(
                f"{len(anomaly_indices)} anomalies ({len(anomaly_indices)/len(df_clean)*100:.1f}%)",
                color="red" if anomaly_indices else "green",
                size="lg",
            )

            # Table of top anomalies
            table_data = []
            for idx in sorted(anomaly_indices)[:10]:
                table_data.append(
                    {
                        "latitude": f"{df_clean.iloc[idx][lat_col]:.4f}",
                        "longitude": f"{df_clean.iloc[idx][lon_col]:.4f}",
                        "value": f"{values[idx]:.2f}",
                        "type": "Outlier",
                    }
                )

            return fig, badge, table_data

        except Exception as e:
            logger.error(f"Error in update_anomalies: {e}")
            return (
                create_error_figure(str(e)),
                dmc.Badge("Error", color="red"),
                [],
            )

# ==========================================
# METHOD 4: SEASONAL DECOMPOSITION
# ==========================================

def decompose_timeseries(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    period: int = 7,
) -> dict[str, Any]:
    """
    Decompose time series into trend, seasonal, and residual components.

    Args:
        df: DataFrame with time series data
        date_col: Name of date column
        value_col: Name of numeric column to decompose
        period: Period for seasonal component (7=weekly, 30=monthly)

    Returns:
        Dict with original, trend, seasonal, residual series
    """
    try:
        tmp = df[[date_col, value_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.dropna().sort_values(date_col)

        if len(tmp) < period * 2:
            return {
                "error": f"Need at least {period * 2} observations for decomposition"
            }

        # Set date as index
        tmp = tmp.set_index(date_col)
        series = tmp[value_col]

        # Simple moving average for trend (not statsmodels)
        trend = series.rolling(window=period, center=True).mean()

        # Detrended series
        detrended = series - trend

        # Seasonal component (average for each period)
        seasonal = np.zeros(len(series))
        for i in range(period):
            seasonal[i::period] = detrended.iloc[i::period].mean()

        # Residual
        residual = series - trend - seasonal

        return {
            "dates": series.index,
            "original": series.values,
            "trend": trend.values,
            "seasonal": seasonal,
            "residual": residual.values,
        }

    except Exception as e:
        logger.error(f"Error in decompose_timeseries: {e}")
        return {"error": str(e)}

def register_decomposition_callbacks(app, dm_instance):
    """Register seasonal decomposition callbacks."""

    @app.callback(
        Output("decomposition-4panel", "figure"),
        Output("decomposition-stats", "children"),
        Input("store-global-filters", "data"),
        Input("decomposition-period", "value"),
        prevent_initial_call=True,
    )
    @timer_callback
    @memoize_with_ttl(seconds=900)
    def update_decomposition(filters, period):
        """
        Decompose time series into components.

        Returns:
            - 4-panel figure (original, trend, seasonal, residual)
            - Summary statistics
        """
        try:
            if not filters:
                return (
                    create_error_figure("No data selected"),
                    dmc.Text("Select data to analyze", c="gray"),
                )

            # Fetch base data
            state = DashboardStateAdapter(dm_instance, filters)
            df = state.get_dataset_by_key("inspection")
            if df.empty:
                return (
                    create_error_figure("No data available"),
                    dmc.Text("No data for selected filters", c="gray"),
                )

            # Find date and value columns
            date_col = next(
                (
                    c
                    for c in df.columns
                    if "date" in c.lower() or "created" in c.lower()
                ),
                None,
            )
            if not date_col:
                return (
                    create_error_figure("No date column found"),
                    dmc.Text("Dataset lacks date column", c="gray"),
                )

            # Use first numeric column as value
            value_col = df.select_dtypes(include=[np.number]).columns[0]

            # Decompose
            result = decompose_timeseries(df, date_col, value_col, period=period)

            if "error" in result:
                return (
                    create_error_figure(result["error"]),
                    dmc.Text(result["error"], c="gray"),
                )

            # Create 4-panel figure
            dates = result["dates"]
            fig = go.Figure()

            # Panel 1: Original
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=result["original"],
                    name="Original",
                    mode="lines",
                )
            )

            # Panel 2: Trend
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=result["trend"],
                    name="Trend",
                    mode="lines",
                    visible="legendonly",
                )
            )

            # Panel 3: Seasonal
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=result["seasonal"],
                    name="Seasonal",
                    mode="lines",
                    visible="legendonly",
                )
            )

            # Panel 4: Residual
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=result["residual"],
                    name="Residual",
                    mode="lines",
                    visible="legendonly",
                )
            )

            fig.update_layout(
                title=f"Seasonal Decomposition (Period={period})",
                xaxis_title="Date",
                yaxis_title="Value",
                height=500,
                hovermode="x unified",
                margin=dict(l=40, r=40, t=50, b=40),
            )

            # Statistics
            original = np.array(result["original"])
            trend = np.array(result["trend"])
            seasonal = np.array(result["seasonal"])
            residual = np.array(result["residual"])

            # Remove NaN for calculations
            valid_trend = trend[~np.isnan(trend)]
            trend_slope = (
                (valid_trend[-1] - valid_trend[0]) / len(valid_trend)
                if len(valid_trend) > 1
                else 0
            )
            seasonal_strength = (
                np.var(seasonal) / (np.var(seasonal) + np.var(residual)) * 100
                if np.var(residual) > 0
                else 0
            )

            stats = dmc.Stack(
                [
                    dmc.Group(
                        [
                            dmc.Badge(
                                f"Trend slope: {trend_slope:.4f}",
                                color="blue",
                                variant="light",
                            ),
                            dmc.Badge(
                                f"Seasonal strength: {seasonal_strength:.1f}%",
                                color="green",
                                variant="light",
                            ),
                            dmc.Badge(
                                f"Period: {period}",
                                color="orange",
                                variant="light",
                            ),
                        ]
                    ),
                    dmc.Text(
                        f"Series length: {len(original):,} observations",
                        size="sm",
                        c="gray",
                    ),
                ],
                gap="sm",
            )

            return fig, stats

        except Exception as e:
            logger.error(f"Error in update_decomposition: {e}")
            return (
                create_error_figure(str(e)),
                dmc.Text(f"Error: {str(e)}", c="red"),
            )

# ==========================================
# METHOD 5: BOOTSTRAP CONFIDENCE INTERVALS
# ==========================================

def bootstrap_confidence_interval(
    data: np.ndarray,
    confidence: float = 0.95,
    n_resamples: int = 10000,
) -> tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for the mean.

    Args:
        data: 1D array of numeric data
        confidence: Confidence level (0-1)
        n_resamples: Number of bootstrap samples

    Returns:
        (point_estimate, ci_lower, ci_upper)
    """
    try:
        data = np.array(data)
        data = data[~np.isnan(data)]

        if len(data) < 2:
            return float(data[0]) if len(data) == 1 else 0.0, 0.0, 0.0

        point_estimate = np.mean(data)
        bootstrap_means = []

        for _ in range(n_resamples):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))

        ci_lower = np.percentile(
            bootstrap_means, (1 - confidence) / 2 * 100
        )
        ci_upper = np.percentile(
            bootstrap_means, (1 + confidence) / 2 * 100
        )

        return point_estimate, ci_lower, ci_upper

    except Exception as e:
        logger.error(f"Error in bootstrap_confidence_interval: {e}")
        return 0.0, 0.0, 0.0

def register_bootstrap_callbacks(app, dm_instance):
    """Register bootstrap confidence interval callbacks."""

    @app.callback(
        Output("metric-gauge-completion-rate", "figure"),
        Input("store-global-filters", "data"),
        prevent_initial_call=True,
    )
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def update_metric_with_ci(filters):
        """
        Create Metric gauge with bootstrap confidence interval band.

        Returns:
            Gauge figure with CI band
        """
        try:
            if not filters:
                return create_error_figure("No data selected")

            # Fetch data
            state = DashboardStateAdapter(dm_instance, filters)
            df = state.get_dataset_by_key("inspection")
            if df.empty:
                return create_error_figure("No data available")

            # Calculate completion rate (example metric)
            completed = (df["_completion_status"] == "COMPLETED").sum()
            total = len(df)
            rate = (completed / total * 100) if total > 0 else 0

            # Bootstrap confidence interval
            completion_flag = (df["_completion_status"] == "COMPLETED").astype(
                int
            ).values
            point_est, ci_lower, ci_upper = bootstrap_confidence_interval(
                completion_flag * 100, confidence=0.95, n_resamples=10000
            )

            # Create gauge with CI band
            fig = go.Figure(
                data=[
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=rate,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": "Completion Rate (95% CI Band)"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 33], "color": "lightcoral"},
                                {"range": [33, 67], "color": "lightyellow"},
                                {"range": [67, 100], "color": "lightgreen"},
                            ],
                        },
                        number={
                            "suffix": "%",
                            "font": {"size": 24},
                        },
                    )
                ]
            )

            # Add CI annotation
            fig.add_annotation(
                text=f"95% CI: [{ci_lower:.1f}%, {ci_upper:.1f}%]",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.05,
                showarrow=False,
                font=dict(size=10, color="gray"),
            )

            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=50, b=50),
            )

            return fig

        except Exception as e:
            logger.error(f"Error in update_metric_with_ci: {e}")
            return create_error_figure(str(e))

# ==========================================
# REGISTRATION FUNCTION
# ==========================================

def register_all_hidden_method_callbacks(app, dm_instance):
    """Register all 5 hidden method callbacks."""
    register_morans_i_callbacks(app, dm_instance)
    register_distribution_callbacks(app, dm_instance)
    register_anomaly_detection_callbacks(app, dm_instance)
    register_decomposition_callbacks(app, dm_instance)
    register_bootstrap_callbacks(app, dm_instance)
    logger.info("All hidden method callbacks registered successfully")
