"""Time-Series Analysis & Forecasting for NYC DOT SIM Program metrics."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import streamlit as st

from app.data_loader import (
    DATE_CANDIDATES,
    demo_mode_enabled,
    fetch_dataset,
    pick_column,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    from statsmodels.tsa.seasonal import STL, seasonal_decompose  # type: ignore[import]
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

try:
    from prophet import Prophet  # type: ignore[import]
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False

try:
    import openpyxl  # type: ignore[import]  # noqa: F401
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# Confidence level label -> (Prophet interval_width, normal z-score for bounds).
_CONFIDENCE_LEVELS: dict[str, tuple[float, float]] = {
    "80%": (0.80, 1.2816),
    "90%": (0.90, 1.6449),
    "95%": (0.95, 1.9600),
}

# ---------------------------------------------------------------------------
# Socrata data loader
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86_400, show_spinner="Loading time-series data from Socrata…")
def _load_timeseries_from_socrata(dataset_key: str, limit: int = 50_000) -> pd.DataFrame:
    """Fetch a dataset and aggregate to monthly time-series."""
    df = fetch_dataset(dataset_key, limit=limit)
    if df.empty:
        return df
    date_col = pick_column(df, DATE_CANDIDATES)
    if not date_col:
        date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if not date_col:
        return pd.DataFrame()
    df = df.copy()
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_date"])
    df["date"] = df["_date"].dt.to_period("M").dt.to_timestamp()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]
    if not numeric_cols:
        agg_df = df.groupby("date").size().reset_index(name="record_count")
    else:
        agg_df = df.groupby("date")[numeric_cols].sum().reset_index()
        agg_df["record_count"] = df.groupby("date").size().values
    return agg_df.sort_values("date")

# ---------------------------------------------------------------------------
# Exponential smoothing (manual — no external deps)
# ---------------------------------------------------------------------------

def _exp_smooth_forecast(
    series: np.ndarray, alpha: float, periods: int, z_score: float = 1.96
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    smoothed = np.zeros(len(series))
    smoothed[0] = series[0]
    for i in range(1, len(series)):
        smoothed[i] = alpha * series[i] + (1 - alpha) * smoothed[i - 1]
    last = smoothed[-1]
    forecast = np.full(periods, last)
    residuals = series - smoothed
    std_resid = np.std(residuals)
    lower = forecast - z_score * std_resid
    upper = forecast + z_score * std_resid
    return forecast, lower, upper

# ---------------------------------------------------------------------------
# NYC DOT holiday / construction-season calendar (for Prophet)
# ---------------------------------------------------------------------------

def _build_nyc_dot_holidays(start_year: int, end_year: int) -> pd.DataFrame:
    """Return a Prophet holidays frame of NYC DOT operationally relevant dates.

    Covers federal holidays that reduce field crew availability (New Year,
    July 4th, Thanksgiving, Christmas) plus the summer construction-season
    window (Jun–Aug) when sidewalk/ramp work volume peaks. Years are derived
    from the fetched series range — no dates are fabricated outside it.
    """
    rows: list[dict[str, object]] = []
    for year in range(start_year, end_year + 1):
        rows.append({"holiday": "new_year", "ds": pd.Timestamp(year, 1, 1)})
        rows.append({"holiday": "independence_day", "ds": pd.Timestamp(year, 7, 4)})
        rows.append({"holiday": "christmas", "ds": pd.Timestamp(year, 12, 25)})
        # Thanksgiving — 4th Thursday of November.
        nov_first = pd.Timestamp(year, 11, 1)
        first_thu = nov_first + pd.Timedelta(days=(3 - nov_first.dayofweek) % 7)
        rows.append({"holiday": "thanksgiving", "ds": first_thu + pd.Timedelta(weeks=3)})
        # Summer construction season — anchor on month starts Jun/Jul/Aug.
        for month in (6, 7, 8):
            rows.append({"holiday": "summer_construction_season", "ds": pd.Timestamp(year, month, 1)})

    holidays = pd.DataFrame(rows)
    holidays["ds"] = pd.to_datetime(holidays["ds"])
    # Construction-season months carry a wider window of influence.
    holidays["lower_window"] = 0
    holidays["upper_window"] = np.where(
        holidays["holiday"] == "summer_construction_season", 30, 1
    )
    return holidays.sort_values("ds").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Forecast Excel export (multi-sheet, openpyxl)
# ---------------------------------------------------------------------------

def _build_forecast_excel(
    actuals: pd.DataFrame, forecast: pd.DataFrame, metric: str, method: str
) -> bytes:
    """Serialise actuals + forecast (with bounds) to a multi-sheet workbook."""
    bounds = forecast[["date", "lower", "upper"]].copy()
    summary = pd.DataFrame(
        {
            "field": ["metric", "method", "forecast_periods", "generated"],
            "value": [
                metric,
                method,
                len(forecast),
                pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            ],
        }
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        actuals.to_excel(writer, sheet_name="Actuals", index=False)
        forecast[["date", "forecast"]].to_excel(writer, sheet_name="Forecast", index=False)
        bounds.to_excel(writer, sheet_name="Bounds", index=False)
    return buffer.getvalue()

# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def _render_trend_analysis(df: pd.DataFrame, date_col: str, metrics: list[str]) -> None:
    st.subheader("Trend Analysis")

    if not metrics:
        st.info("Select at least one metric to analyze.")
        return

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)

    window = st.select_slider("Rolling average window", options=[7, 14, 30, 90], value=30, key="trend_window")
    show_trendline = st.checkbox("Show linear trendline", value=True, key="trend_line")

    for metric in metrics:
        if metric not in df.columns:
            continue
        series = df.set_index(date_col)[metric].dropna()
        if series.empty:
            continue

        rolling = series.rolling(window, min_periods=1).mean()
        x_numeric = np.arange(len(series))
        slope, intercept = np.polyfit(x_numeric, series.values, 1)
        direction = "↑ Upward" if slope > 0 else "↓ Downward"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{metric} — Mean", f"{series.mean():.1f}")
        c2.metric("Std Dev", f"{series.std():.1f}")
        c3.metric("Min / Max", f"{series.min():.0f} / {series.max():.0f}")
        c4.metric("Trend", direction)

        if not HAS_PLOTLY:
            st.line_chart(series)
            continue

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values,
            mode="lines", name=metric,
            line=dict(color="#4C78A8", width=1.5),
            opacity=0.7,
        ))
        fig.add_trace(go.Scatter(
            x=rolling.index, y=rolling.values,
            mode="lines", name=f"{window}-day avg",
            line=dict(color="#F58518", width=2.5),
        ))
        if show_trendline:
            trendline = slope * x_numeric + intercept
            fig.add_trace(go.Scatter(
                x=series.index, y=trendline,
                mode="lines", name="Linear Trend",
                line=dict(color="#E45756", width=1.5, dash="dash"),
            ))
        fig.update_layout(title=f"{metric} — Trend Analysis", height=320,
                          xaxis_title="Date", yaxis_title=metric, legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)

def _render_seasonality(df: pd.DataFrame, date_col: str, metrics: list[str]) -> None:
    st.subheader("Seasonality & Patterns")

    if not metrics:
        st.info("Select metrics in the sidebar.")
        return

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    df["month"] = df[date_col].dt.month
    df["month_name"] = df[date_col].dt.strftime("%b")
    df["day_of_week"] = df[date_col].dt.dayofweek
    df["dow_name"] = df[date_col].dt.strftime("%a")
    df["year"] = df[date_col].dt.year

    metric = metrics[0]
    if metric not in df.columns:
        st.info(f"Column '{metric}' not found.")
        return

    if not HAS_PLOTLY:
        st.bar_chart(df.groupby("month")[metric].mean())
        return

    col1, col2 = st.columns(2)
    with col1:
        monthly = df.groupby(["month", "month_name"])[metric].mean().reset_index().sort_values("month")
        fig = px.bar(monthly, x="month_name", y=metric, title=f"Avg {metric} by Month (Seasonality)")
        fig.update_layout(height=320, xaxis_title="Month", yaxis_title=f"Avg {metric}")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        dow = df.groupby(["day_of_week", "dow_name"])[metric].mean().reset_index().sort_values("day_of_week")
        fig2 = px.bar(dow, x="dow_name", y=metric, title=f"Avg {metric} by Day of Week")
        fig2.update_layout(height=320, xaxis_title="Day", yaxis_title=f"Avg {metric}")
        st.plotly_chart(fig2, use_container_width=True)

    years = sorted(df["year"].unique())
    if len(years) >= 2:
        st.markdown("**Year-over-Year Comparison**")
        monthly_yoy = df.groupby(["year", "month"])[metric].mean().reset_index()
        fig3 = px.line(monthly_yoy, x="month", y=metric, color=monthly_yoy["year"].astype(str),
                       title=f"{metric} — Year over Year", markers=True)
        fig3.update_layout(height=350, xaxis=dict(tickmode="linear"),
                           xaxis_title="Month", yaxis_title=f"Avg {metric}")
        st.plotly_chart(fig3, use_container_width=True)

    if HAS_STATSMODELS and len(df) >= 24:
        with st.expander("Seasonal Decomposition (statsmodels)"):
            try:
                series = df.set_index(date_col)[metric].resample("MS").mean().dropna()
                if len(series) >= 12:
                    result = seasonal_decompose(series, model="additive", period=12)
                    fig_dec = go.Figure()
                    for comp, name, color in [
                        (result.trend, "Trend", "#4C78A8"),
                        (result.seasonal, "Seasonal", "#F58518"),
                        (result.resid, "Residual", "#E45756"),
                    ]:
                        fig_dec.add_trace(go.Scatter(x=comp.index, y=comp.values,
                                                     mode="lines", name=name, line=dict(color=color)))
                    fig_dec.update_layout(title="Decomposition", height=400)
                    st.plotly_chart(fig_dec, use_container_width=True)
            except Exception as e:
                st.info(f"Decomposition unavailable: {e}")

    _render_stl_decomposition(df, date_col, metric)

def _render_stl_decomposition(df: pd.DataFrame, date_col: str, metric: str) -> None:
    """STL (Seasonal-Trend decomposition using LOESS) component subplots."""
    if not HAS_STATSMODELS:
        st.info("STL decomposition requires statsmodels. Install with `pip install statsmodels`.")
        return

    with st.expander("STL Decomposition (Seasonal-Trend via LOESS)"):
        series = df.set_index(date_col)[metric].resample("MS").mean().dropna()
        if len(series) < 24:
            st.info(
                f"STL needs at least 24 monthly observations (have {len(series)}). "
                "Fetch a longer history to enable robust seasonal-trend decomposition."
            )
            return
        try:
            stl_result = STL(series, period=12, robust=True).fit()
        except (ValueError, np.linalg.LinAlgError) as exc:
            st.info(f"STL decomposition unavailable: {exc}")
            return

        components = [
            ("Observed", series, "#54A24B"),
            ("Trend", stl_result.trend, "#4C78A8"),
            ("Seasonal", stl_result.seasonal, "#F58518"),
            ("Residual", stl_result.resid, "#E45756"),
        ]

        if not HAS_PLOTLY:
            for name, comp, _ in components:
                st.markdown(f"**{name}**")
                st.line_chart(comp)
            return

        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
            subplot_titles=[name for name, _, _ in components],
        )
        for row, (name, comp, color) in enumerate(components, start=1):
            mode = "markers" if name == "Residual" else "lines"
            fig.add_trace(
                go.Scatter(x=comp.index, y=comp.values, mode=mode,
                           name=name, line=dict(color=color), marker=dict(color=color, size=4)),
                row=row, col=1,
            )
        fig.update_layout(height=640, showlegend=False,
                          title=f"{metric} — STL Decomposition (period=12 months)")
        st.plotly_chart(fig, use_container_width=True)

        seasonal_strength = max(
            0.0,
            1.0 - stl_result.resid.var() / (stl_result.seasonal + stl_result.resid).var(),
        )
        trend_strength = max(
            0.0,
            1.0 - stl_result.resid.var() / (stl_result.trend + stl_result.resid).var(),
        )
        c1, c2 = st.columns(2)
        c1.metric("Seasonal strength", f"{seasonal_strength:.2f}")
        c2.metric("Trend strength", f"{trend_strength:.2f}")
        st.caption(
            "Strength scores (0–1, Hyndman) gauge how much of the variance each component "
            "explains. Values near 1 indicate a strong, well-defined pattern."
        )

def _render_forecasting(df: pd.DataFrame, date_col: str, metrics: list[str]) -> None:
    st.subheader("Forecasting")

    if not metrics:
        st.info("Select metrics to forecast.")
        return

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)

    metric = st.selectbox("Metric to forecast", metrics, key="fc_metric")
    if metric not in df.columns:
        return

    series_raw = df.set_index(date_col)[metric].dropna()
    if len(series_raw) < 3:
        st.warning("Need at least 3 data points to forecast.")
        return

    col1, col2 = st.columns(2)
    with col1:
        forecast_periods = st.number_input("Forecast periods (months)", 1, 24, 12, key="fc_periods")
    with col2:
        method = st.radio(
            "Method",
            ["Exponential Smoothing"] + (["Prophet"] if HAS_PROPHET else []),
            key="fc_method",
        )

    if method == "Exponential Smoothing":
        alpha = st.slider("Smoothing factor α (higher = more weight on recent data)", 0.1, 0.9, 0.3, key="fc_alpha")
        hist_vals = series_raw.values.astype(float)
        fc_vals, fc_lower, fc_upper = _exp_smooth_forecast(hist_vals, alpha, int(forecast_periods))
        freq = pd.infer_freq(series_raw.index) or "MS"
        fc_dates = pd.date_range(series_raw.index[-1], periods=int(forecast_periods) + 1, freq=freq)[1:]
        fc_df = pd.DataFrame({"date": fc_dates, "forecast": fc_vals, "lower": fc_lower, "upper": fc_upper})

    elif method == "Prophet" and HAS_PROPHET:
        try:
            prophet_df = series_raw.reset_index()
            prophet_df.columns = ["ds", "y"]
            m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
            m.fit(prophet_df)
            future = m.make_future_dataframe(periods=int(forecast_periods), freq="MS")
            forecast = m.predict(future)
            fc_df = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(int(forecast_periods)).copy()
            fc_df.columns = ["date", "forecast", "lower", "upper"]
        except Exception as e:
            st.error(f"Prophet failed: {e}")
            return
    else:
        st.info("Select a forecasting method.")
        return

    if not HAS_PLOTLY:
        st.line_chart(series_raw)
        st.dataframe(fc_df)
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series_raw.index, y=series_raw.values,
        mode="lines+markers", name="Historical",
        line=dict(color="#4C78A8", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=fc_df["date"], y=fc_df["forecast"],
        mode="lines", name="Forecast",
        line=dict(color="#F58518", width=2.5, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([fc_df["date"], fc_df["date"][::-1]]),
        y=pd.concat([fc_df["upper"], fc_df["lower"][::-1]]),
        fill="toself", fillcolor="rgba(245,133,24,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="95% CI",
    ))
    fig.update_layout(title=f"{metric} Forecast ({method})", height=420,
                      xaxis_title="Date", yaxis_title=metric)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Forecast Table**")
    fc_df["date"] = fc_df["date"].dt.strftime("%Y-%m")
    fc_df[["forecast", "lower", "upper"]] = fc_df[["forecast", "lower", "upper"]].round(1)
    st.dataframe(fc_df, use_container_width=True, hide_index=True)

    csv = fc_df.to_csv(index=False).encode()
    st.download_button("📥 Download Forecast CSV", csv, f"forecast_{metric}.csv", "text/csv")

def _render_metric_targets(df: pd.DataFrame, date_col: str, metrics: list[str]) -> None:
    st.subheader("Metric Targets vs Actuals")

    if not metrics or df.empty:
        st.info("Load data and select metrics.")
        return

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    df["month"] = df[date_col].dt.to_period("M").astype(str)

    metric = st.selectbox("Metric", metrics, key="metric_metric")
    if metric not in df.columns:
        return

    monthly_actual = df.groupby("month")[metric].sum().reset_index()
    monthly_actual.columns = ["month", "actual"]

    st.markdown("**Set Monthly Targets** (edit the table below)")
    n = min(len(monthly_actual), 12)
    default_target = float(monthly_actual["actual"].mean() * 1.05)
    target_df = monthly_actual.head(n).copy()
    target_df["target"] = default_target

    edited = st.data_editor(
        target_df[["month", "target"]],
        num_rows="fixed",
        use_container_width=True,
        key="metric_targets",
        column_config={"target": st.column_config.NumberColumn("Target", min_value=0, step=1)},
    )

    combined = monthly_actual.merge(edited, on="month", how="left")
    combined["variance"] = combined["actual"] - combined["target"]
    combined["variance_pct"] = ((combined["actual"] / combined["target"]) * 100 - 100).round(1)
    combined["status"] = combined.apply(
        lambda r: "🟢 On Target" if r["actual"] >= r["target"] * 0.95
        else ("🟡 Watch" if r["actual"] >= r["target"] * 0.80 else "🔴 Below Target"),
        axis=1,
    )

    on_target = (combined["actual"] >= combined["target"] * 0.95).sum()
    total_months = len(combined)
    achievement_rate = round(on_target / total_months * 100, 1) if total_months > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Achievement Rate", f"{achievement_rate}%")
    c2.metric("Months On Target", f"{on_target} / {total_months}")
    c3.metric("Avg Variance", f"{combined['variance_pct'].mean():+.1f}%")

    if HAS_PLOTLY:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=combined["month"], y=combined["actual"],
            mode="lines+markers", name="Actual",
            line=dict(color="#4C78A8", width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=combined["month"], y=combined["target"],
            mode="lines", name="Target",
            line=dict(color="#E45756", width=2, dash="dot"),
        ))
        fig.update_layout(title=f"{metric} — Targets vs Actuals", height=380,
                          xaxis_title="Month", yaxis_title=metric, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        combined[["month", "actual", "target", "variance", "variance_pct", "status"]],
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_forecasting_page() -> None:
    st.header("📈 Trend Analysis & Forecasting")
    st.caption("Time-series analysis, seasonality detection, and forecasting for SIM Program Metrics.")

    st.sidebar.markdown("**Data Source**")
    source = st.sidebar.radio("Source", ["Socrata (live)", "Upload CSV/Excel"], key="fc_src")

    if source == "Socrata (live)":
        SOCRATA_KEYS = {
            "SMD Inspection (dntt-gqwq)": "inspection",
            "SMD Built (ugc8-s3f6)": "built",
            "Ramp Progress (e7gc-ub6z)": "ramp_progress",
            "Street Permits (tqtj-sjs8)": "street_permits",
            "Weekly Construction (r528-jcks)": "weekly_construction",
        }
        dataset_label = st.sidebar.selectbox("Dataset", list(SOCRATA_KEYS.keys()), key="fc_dataset")
        dataset_key = SOCRATA_KEYS[dataset_label]
        fc_limit = st.sidebar.number_input("Row limit", 1_000, 100_000, 25_000, step=5_000, key="fc_limit")
        with st.spinner(f"Loading {dataset_label} from Socrata…"):
            df = _load_timeseries_from_socrata(dataset_key, int(fc_limit))
        if df.empty:
            st.warning("No data returned from Socrata. Check your API token in Settings.")
            return
        if demo_mode_enabled():
            st.sidebar.caption("⚠️ Demo mode — configure SOCRATA_APP_TOKEN in Settings for live data.")
        date_col = "date"
    else:
        up = st.sidebar.file_uploader("Upload time-series CSV/Excel", type=["csv", "xlsx"], key="fc_upload")
        if up is None:
            st.info("Upload a CSV/Excel with a date column and numeric metric columns, or switch to Socrata.")
            return
        df = pd.read_excel(up) if up.name.endswith(".xlsx") else pd.read_csv(up)
        date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
        if not date_cols:
            st.error("No date column found. Ensure your file has a column with 'date' or 'time' in the name.")
            return
        date_col = st.sidebar.selectbox("Date column", date_cols, key="fc_date_col")

    numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != date_col]

    selected_metrics = st.sidebar.multiselect(
        "Metrics to analyze", numeric_cols,
        default=numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols,
        key="fc_metrics",
    )

    if not selected_metrics:
        st.info("Select at least one metric to analyze from the sidebar.")
        return

    st.caption(f"Loaded {len(df):,} rows · {len(numeric_cols)} numeric columns")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📉 Trends",
        "📅 Seasonality",
        "🔮 Forecast",
        "🎯 Metric Targets",
    ])

    with tab1:
        _render_trend_analysis(df, date_col, selected_metrics)
    with tab2:
        _render_seasonality(df, date_col, selected_metrics)
    with tab3:
        _render_forecasting(df, date_col, selected_metrics)
    with tab4:
        _render_metric_targets(df, date_col, selected_metrics)
