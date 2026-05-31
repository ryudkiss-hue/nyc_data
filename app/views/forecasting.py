"""Time-Series Analysis & Forecasting for NYC DOT SIM Program metrics."""

from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    from statsmodels.tsa.seasonal import seasonal_decompose  # type: ignore[import]
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

try:
    from prophet import Prophet  # type: ignore[import]
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

def _demo_series(months: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=months, freq="MS")
    trend = np.linspace(100, 160, months)
    seasonal = 20 * np.sin(2 * np.pi * np.arange(months) / 12)
    noise = rng.normal(0, 8, months)
    lots = (trend + seasonal + noise).clip(50, 250).astype(int)
    sqft = (lots * rng.uniform(150, 300, months)).astype(int)
    contracts_active = rng.integers(8, 22, months)
    defects = (lots * rng.uniform(0.2, 0.5, months)).astype(int)
    return pd.DataFrame({
        "date": dates,
        "lots_completed": lots,
        "sqft_completed": sqft,
        "contracts_active": contracts_active,
        "defects_found": defects,
    })


# ---------------------------------------------------------------------------
# Exponential smoothing (manual — no external deps)
# ---------------------------------------------------------------------------

def _exp_smooth_forecast(series: np.ndarray, alpha: float, periods: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    smoothed = np.zeros(len(series))
    smoothed[0] = series[0]
    for i in range(1, len(series)):
        smoothed[i] = alpha * series[i] + (1 - alpha) * smoothed[i - 1]

    last = smoothed[-1]
    forecast = np.full(periods, last)

    residuals = series - smoothed
    std_resid = np.std(residuals)
    lower = forecast - 1.96 * std_resid
    upper = forecast + 1.96 * std_resid
    return forecast, lower, upper


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
            line=dict(color="#F58518", width=2.5, dash="solid"),
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

    # Year-over-year
    years = sorted(df["year"].unique())
    if len(years) >= 2:
        st.markdown("**Year-over-Year Comparison**")
        monthly_yoy = df.groupby(["year", "month"])[metric].mean().reset_index()
        fig3 = px.line(monthly_yoy, x="month", y=metric, color=monthly_yoy["year"].astype(str),
                       title=f"{metric} — Year over Year", markers=True)
        fig3.update_layout(height=350, xaxis=dict(tickmode="linear"),
                           xaxis_title="Month", yaxis_title=f"Avg {metric}")
        st.plotly_chart(fig3, use_container_width=True)

    # Decomposition
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


def _render_kpi_targets(df: pd.DataFrame, date_col: str, metrics: list[str]) -> None:
    st.subheader("KPI Targets vs Actuals")

    if not metrics or df.empty:
        st.info("Load data and select metrics.")
        return

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    df["month"] = df[date_col].dt.to_period("M").astype(str)

    metric = st.selectbox("Metric", metrics, key="kpi_metric")
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
        key="kpi_targets",
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
    st.caption("Time-series analysis, seasonality detection, and forecasting for SIM Program KPIs.")

    # Sidebar: data source + metric selection
    st.sidebar.markdown("**Data Source**")
    use_demo = st.sidebar.checkbox("Use demo data", value=True, key="fc_demo")

    if use_demo:
        df = _demo_series(30)
        date_col = "date"
        st.sidebar.caption("Demo: 30-month synthetic SIM series")
    else:
        up = st.sidebar.file_uploader("Upload time-series CSV", type="csv", key="fc_upload")
        if up is None:
            st.info("Upload a CSV with a date column and numeric metric columns, or enable demo data in the sidebar.")
            return
        df = pd.read_csv(up)
        date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
        date_col = st.sidebar.selectbox("Date column", date_cols, key="fc_date_col") if date_cols else df.columns[0]

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if date_col in numeric_cols:
        numeric_cols.remove(date_col)

    selected_metrics = st.sidebar.multiselect(
        "Metrics to analyze", numeric_cols,
        default=numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols,
        key="fc_metrics",
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📉 Trends",
        "📅 Seasonality",
        "🔮 Forecast",
        "🎯 KPI Targets",
    ])

    with tab1:
        _render_trend_analysis(df, date_col, selected_metrics)
    with tab2:
        _render_seasonality(df, date_col, selected_metrics)
    with tab3:
        _render_forecasting(df, date_col, selected_metrics)
    with tab4:
        _render_kpi_targets(df, date_col, selected_metrics)
