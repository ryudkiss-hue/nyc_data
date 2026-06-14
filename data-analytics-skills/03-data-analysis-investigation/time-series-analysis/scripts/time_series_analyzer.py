"""
time_series_analyzer.py — Trend, seasonality, and anomaly detection for NYC DOT time series.

Usage:
    python time_series_analyzer.py --input data.csv --date-col inspection_date --metric-col count
    python time_series_analyzer.py --input data.csv --date-col created_date --metric-col violations --window 14 --output report.md
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_series(path: str, date_col: str, metric_col: str) -> pd.Series:
    df = pd.read_csv(path, parse_dates=[date_col])
    if date_col not in df.columns:
        print(f"[ERROR] Date column '{date_col}' not found. Available: {list(df.columns)}")
        sys.exit(1)
    if metric_col not in df.columns:
        print(f"[ERROR] Metric column '{metric_col}' not found.")
        sys.exit(1)
    series = df.set_index(date_col)[metric_col].sort_index()
    return series


def fill_gaps(series: pd.Series, freq: str = "D") -> pd.Series:
    """Reindex to regular frequency, forward-fill gaps up to 3 periods."""
    full_index = pd.date_range(series.index.min(), series.index.max(), freq=freq)
    return series.reindex(full_index).fillna(method="ffill", limit=3)


def rolling_stats(series: pd.Series, window: int) -> pd.DataFrame:
    df = pd.DataFrame({"value": series})
    df["rolling_mean"] = series.rolling(window).mean()
    df["rolling_std"] = series.rolling(window).std()
    df["upper"] = df["rolling_mean"] + 2 * df["rolling_std"]
    df["lower"] = df["rolling_mean"] - 2 * df["rolling_std"]
    return df


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Flag points outside 2-sigma band as anomalies."""
    anomalies = df[(df["value"] > df["upper"]) | (df["value"] < df["lower"])].copy()
    anomalies["direction"] = np.where(anomalies["value"] > anomalies["upper"], "spike", "dip")
    return anomalies


def trend_slope(series: pd.Series) -> float:
    """Linear regression slope (units per day)."""
    x = np.arange(len(series))
    y = series.values
    mask = ~np.isnan(y)
    if mask.sum() < 2:
        return 0.0
    coeffs = np.polyfit(x[mask], y[mask], 1)
    return float(coeffs[0])


def mom_change(series: pd.Series) -> pd.Series:
    """Month-over-month % change."""
    monthly = series.resample("ME").mean()
    return monthly.pct_change() * 100


def adf_interpretation(series: pd.Series) -> str:
    """Augmented Dickey-Fuller stationarity test (requires statsmodels)."""
    try:
        from statsmodels.tsa.stattools import adfuller

        result = adfuller(series.dropna())
        p = result[1]
        if p < 0.05:
            return f"Stationary (ADF p={p:.3f}) — no unit root; trend/seasonality can be modelled directly."
        return f"Non-stationary (ADF p={p:.3f}) — differencing recommended before ARIMA fitting."
    except ImportError:
        return "statsmodels not installed — skipping ADF test."


def seasonal_summary(series: pd.Series) -> str:
    """Day-of-week and month-of-year averages."""
    lines = []
    if len(series) >= 14:
        dow = series.groupby(series.index.day_of_week).mean()
        peak_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow.idxmax()]
        low_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow.idxmin()]
        lines.append(f"  Day-of-week peak: {peak_day} | trough: {low_day}")
    if len(series) >= 90:
        mom = series.groupby(series.index.month).mean()
        peak_month = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ][mom.idxmax() - 1]
        lines.append(f"  Seasonal peak month: {peak_month}")
    return (
        "\n".join(lines)
        if lines
        else "  Insufficient data for seasonal decomposition (need ≥14 points)."
    )


def render_report(
    series: pd.Series, df_stats: pd.DataFrame, anomalies: pd.DataFrame, window: int, output: str
):
    slope = trend_slope(series)
    direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    adf = adf_interpretation(series)
    seasonal = seasonal_summary(series)

    lines = [
        "# Time-Series Analysis Report",
        "",
        f"**Series:** {series.name or 'metric'}",
        f"**Period:** {series.index.min().date()} → {series.index.max().date()}",
        f"**Points:** {len(series):,}  |  **Rolling window:** {window} days",
        "",
        "---",
        "",
        "## Trend",
        "",
        f"- Direction: **{direction}**",
        f"- Slope: {slope:+.3f} units/day",
        f"- Overall mean: {series.mean():.2f}  |  std: {series.std():.2f}",
        f"- Min: {series.min():.2f} on {series.idxmin().date()}",
        f"- Max: {series.max():.2f} on {series.idxmax().date()}",
        "",
        "## Stationarity",
        "",
        f"- {adf}",
        "",
        "## Seasonality",
        "",
        seasonal,
        "",
        f"## Anomalies ({len(anomalies)} detected)",
        "",
    ]

    if anomalies.empty:
        lines.append("No anomalies detected outside 2-sigma band.")
    else:
        lines.append("| Date | Value | Direction | Rolling Mean |")
        lines.append("|------|-------|-----------|-------------|")
        for dt, row in anomalies.head(10).iterrows():
            lines.append(
                f"| {dt.date()} | {row['value']:.1f} | {row['direction']} | {row['rolling_mean']:.1f} |"
            )

    lines += [
        "",
        "## Month-over-Month Change",
        "",
    ]
    mom = mom_change(series).dropna().tail(6)
    if not mom.empty:
        lines.append("| Month | MoM % Change |")
        lines.append("|-------|-------------|")
        for dt, val in mom.items():
            lines.append(f"| {dt.strftime('%Y-%m')} | {val:+.1f}% |")
    else:
        lines.append("Insufficient data for MoM calculation.")

    lines += [
        "",
        "---",
        "",
        "## Next Steps",
        "",
        "- [ ] Correlate anomaly dates with operational events (crew changes, policy shifts, data gaps)",
        f"- [ ] Fit ARIMA model for {direction} series (use statsmodels or scikit-learn)",
        "- [ ] Set alert threshold at rolling_mean ± 2σ",
        "- [ ] Share trend finding with operations lead",
    ]

    Path(output).write_text("\n".join(lines))
    print(f"[DONE] Report written to {output}")
    print(f"  Trend: {direction} ({slope:+.3f}/day)")
    print(f"  Anomalies: {len(anomalies)}")


def main():
    parser = argparse.ArgumentParser(description="Time-series trend and anomaly analysis.")
    parser.add_argument("--input", required=True, help="CSV with date and metric columns")
    parser.add_argument("--date-col", required=True, help="Name of the date/timestamp column")
    parser.add_argument("--metric-col", required=True, help="Name of the numeric metric column")
    parser.add_argument("--window", type=int, default=7, help="Rolling average window (days)")
    parser.add_argument("--output", default="time_series_report.md")
    args = parser.parse_args()

    series = load_series(args.input, args.date_col, args.metric_col)
    series = fill_gaps(series)
    df_stats = rolling_stats(series, args.window)
    anomalies = detect_anomalies(df_stats)
    render_report(series, df_stats, anomalies, args.window, args.output)


if __name__ == "__main__":
    main()
