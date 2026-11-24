#!/usr/bin/env python3
"""
trend_analyzer.py — Compute rolling averages, detect trend direction,
flag seasonal patterns, and summarise anomalies for a time-series metric.

Usage:
    python trend_analyzer.py \
        --input daily_inspections.csv \
        --date-col inspection_date \
        --metric-col daily_count \
        --window 7 \
        --output trend_summary.csv

Requirements: pandas, numpy, scipy. No LLM or API keys required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_data(path: str, date_col: str, metric_col: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        sys.exit(f"ERROR: File not found: {path}")
    suffix = p.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, parse_dates=[date_col])
    elif suffix in (".xls", ".xlsx"):
        df = pd.read_excel(path, parse_dates=[date_col])
    elif suffix == ".parquet":
        df = pd.read_parquet(path)
        df[date_col] = pd.to_datetime(df[date_col])
    else:
        sys.exit(f"ERROR: Unsupported file type '{suffix}'.")

    if date_col not in df.columns:
        sys.exit(f"ERROR: Date column '{date_col}' not found. Available: {list(df.columns)}")
    if metric_col not in df.columns:
        sys.exit(f"ERROR: Metric column '{metric_col}' not found. Available: {list(df.columns)}")

    df = df.sort_values(date_col).reset_index(drop=True)
    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce")
    null_count = df[metric_col].isna().sum()
    if null_count > 0:
        print(f"WARNING: {null_count} null values in '{metric_col}' — these rows will be excluded.")
    df = df.dropna(subset=[metric_col])
    print(
        f"Loaded {len(df):,} rows. Date range: {df[date_col].min().date()} to {df[date_col].max().date()}"
    )
    return df


# ---------------------------------------------------------------------------
# Rolling average
# ---------------------------------------------------------------------------


def compute_rolling_average(df: pd.DataFrame, metric_col: str, window: int) -> pd.DataFrame:
    df = df.copy()
    df[f"rolling_{window}d_avg"] = (
        df[metric_col].rolling(window=window, min_periods=max(1, window // 2)).mean()
    )
    df[f"rolling_{window}d_std"] = (
        df[metric_col].rolling(window=window, min_periods=max(1, window // 2)).std()
    )
    return df


# ---------------------------------------------------------------------------
# Trend direction (linear regression slope)
# ---------------------------------------------------------------------------


def detect_trend(df: pd.DataFrame, metric_col: str) -> dict:
    """Fit a linear regression on the metric values over time index."""
    y = df[metric_col].values
    x = np.arange(len(y))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    r_squared = r_value**2
    total_range = y.max() - y.min() if len(y) > 1 else 1
    # Express slope as % change per week (7 data points)
    weekly_change = slope * 7
    weekly_change_pct = (weekly_change / abs(y.mean()) * 100) if y.mean() != 0 else 0.0

    if p_value < 0.05:
        if slope > 0:
            direction = "INCREASING"
        else:
            direction = "DECREASING"
    else:
        direction = "FLAT (no statistically significant trend)"

    return {
        "trend_direction": direction,
        "slope_per_period": round(slope, 4),
        "weekly_change_estimate": round(weekly_change, 2),
        "weekly_change_pct": round(weekly_change_pct, 2),
        "r_squared": round(r_squared, 4),
        "p_value": round(p_value, 6),
        "trend_significant": p_value < 0.05,
    }


# ---------------------------------------------------------------------------
# Month-over-month seasonal pattern
# ---------------------------------------------------------------------------


def detect_seasonal_patterns(df: pd.DataFrame, date_col: str, metric_col: str) -> pd.DataFrame:
    """Compute month-over-month % change by calendar month."""
    df = df.copy()
    df["_month"] = df[date_col].dt.to_period("M")
    monthly = (
        df.groupby("_month")[metric_col]
        .mean()
        .reset_index()
        .rename(columns={metric_col: "monthly_avg"})
    )
    monthly["_month_str"] = monthly["_month"].astype(str)
    monthly["mom_pct_change"] = monthly["monthly_avg"].pct_change() * 100
    monthly["mom_pct_change"] = monthly["mom_pct_change"].round(1)

    # Season classification (Northern Hemisphere / NYC calendar)
    def season(period):
        m = period.month
        if m in (12, 1, 2):
            return "Winter"
        elif m in (3, 4, 5):
            return "Spring"
        elif m in (6, 7, 8):
            return "Summer"
        else:
            return "Fall"

    monthly["season"] = monthly["_month"].apply(season)
    return monthly[["_month_str", "monthly_avg", "mom_pct_change", "season"]].rename(
        columns={"_month_str": "month"}
    )


def detect_day_of_week_pattern(df: pd.DataFrame, date_col: str, metric_col: str) -> pd.DataFrame:
    """Compute average metric by day of week."""
    df = df.copy()
    df["_dow"] = df[date_col].dt.day_name()
    df["_dow_num"] = df[date_col].dt.dayofweek  # 0=Mon
    dow = df.groupby(["_dow_num", "_dow"])[metric_col].mean().reset_index().sort_values("_dow_num")
    overall_avg = df[metric_col].mean()
    dow["vs_weekly_avg_pct"] = ((dow[metric_col] - overall_avg) / overall_avg * 100).round(1)
    return dow[["_dow", metric_col, "vs_weekly_avg_pct"]].rename(
        columns={"_dow": "day_of_week", metric_col: "avg_value"}
    )


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def detect_anomalies(
    df: pd.DataFrame, metric_col: str, window: int, sigma: float = 2.0
) -> pd.DataFrame:
    """Flag rows where the metric exceeds rolling_mean ± sigma * rolling_std."""
    roll_avg_col = f"rolling_{window}d_avg"
    roll_std_col = f"rolling_{window}d_std"

    if roll_avg_col not in df.columns:
        df = compute_rolling_average(df, metric_col, window)

    df = df.copy()
    upper = df[roll_avg_col] + sigma * df[roll_std_col].fillna(0)
    lower = df[roll_avg_col] - sigma * df[roll_std_col].fillna(0)

    df["is_anomaly"] = (df[metric_col] > upper) | (df[metric_col] < lower)
    df["anomaly_direction"] = np.where(
        df[metric_col] > upper, "HIGH", np.where(df[metric_col] < lower, "LOW", "")
    )
    anomalies = df[df["is_anomaly"]].copy()
    anomalies["z_score"] = (
        (anomalies[metric_col] - df[metric_col].mean()) / df[metric_col].std()
    ).round(2)
    return anomalies


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def print_summary(
    trend: dict,
    monthly: pd.DataFrame,
    dow: pd.DataFrame,
    anomalies: pd.DataFrame,
    metric_col: str,
    window: int,
    df: pd.DataFrame,
) -> None:
    print("\n" + "=" * 60)
    print("TREND ANALYSIS SUMMARY")
    print("=" * 60)

    print(f"\nMetric:        {metric_col}")
    print(f"Records:       {len(df):,}")
    print(f"Overall mean:  {df[metric_col].mean():.2f}")
    print(f"Overall std:   {df[metric_col].std():.2f}")
    print(f"Rolling window: {window} periods")

    print("\n--- Trend Direction ---")
    print(f"  Direction:           {trend['trend_direction']}")
    print(
        f"  Weekly change:       {trend['weekly_change_estimate']:+.2f} ({trend['weekly_change_pct']:+.1f}% per week)"
    )
    print(f"  R-squared:           {trend['r_squared']:.4f}")
    print(f"  p-value:             {trend['p_value']:.6f}")
    print(f"  Statistically sig.:  {'Yes' if trend['trend_significant'] else 'No'}")

    print("\n--- Monthly Seasonality (last 12 months) ---")
    display_monthly = monthly.tail(12)
    print(display_monthly.to_string(index=False))

    peak_month = (
        monthly.loc[monthly["monthly_avg"].idxmax(), "month"] if len(monthly) > 0 else "N/A"
    )
    low_month = monthly.loc[monthly["monthly_avg"].idxmin(), "month"] if len(monthly) > 0 else "N/A"
    print(f"\n  Peak month:  {peak_month}")
    print(f"  Low month:   {low_month}")

    print("\n--- Day-of-Week Pattern ---")
    print(dow.to_string(index=False))

    print("\n--- Anomalies (±2σ from rolling mean) ---")
    if len(anomalies) == 0:
        print("  No anomalies detected.")
    else:
        print(f"  {len(anomalies)} anomalies found:")
        print(anomalies[["is_anomaly", "anomaly_direction", "z_score"]].head(10).to_string())

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse trends, seasonality, and anomalies in a time-series metric.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trend_analyzer.py --input daily_inspections.csv \\
      --date-col inspection_date --metric-col daily_count

  python trend_analyzer.py --input ramp_progress.csv \\
      --date-col completion_date --metric-col completions \\
      --window 14 --output ramp_trend.csv
""",
    )
    parser.add_argument("--input", required=True, help="Input CSV, Excel, or Parquet file.")
    parser.add_argument("--date-col", required=True, help="Name of the date/datetime column.")
    parser.add_argument("--metric-col", required=True, help="Name of the numeric metric column.")
    parser.add_argument(
        "--window",
        type=int,
        default=7,
        help="Rolling window size in periods (default: 7).",
    )
    parser.add_argument(
        "--output",
        default="trend_summary.csv",
        help="Path for the output trend summary CSV (default: trend_summary.csv).",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=2.0,
        help="Standard deviation threshold for anomaly flagging (default: 2.0).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    df = load_data(args.input, args.date_col, args.metric_col)

    if len(df) < args.window * 2:
        print(
            f"WARNING: Only {len(df)} rows — fewer than 2× the window size ({args.window}). "
            "Results may be unreliable."
        )

    # Rolling average
    df = compute_rolling_average(df, args.metric_col, args.window)

    # Trend direction
    trend = detect_trend(df, args.metric_col)

    # Seasonal patterns
    monthly = detect_seasonal_patterns(df, args.date_col, args.metric_col)
    dow = detect_day_of_week_pattern(df, args.date_col, args.metric_col)

    # Anomaly detection
    anomalies = detect_anomalies(df, args.metric_col, args.window, args.sigma)

    # Print summary to console
    print_summary(trend, monthly, dow, anomalies, args.metric_col, args.window, df)

    # Write output CSV (full series with rolling averages and anomaly flags)
    df.to_csv(args.output, index=False)
    print(f"\nFull annotated series written to: {args.output}")

    # Write anomaly table if any found
    if len(anomalies) > 0:
        anomaly_path = args.output.replace(".csv", "_anomalies.csv")
        anomaly_cols = [args.date_col, args.metric_col, "anomaly_direction", "z_score"]
        anomaly_cols = [c for c in anomaly_cols if c in anomalies.columns]
        anomalies[anomaly_cols].to_csv(anomaly_path, index=False)
        print(f"Anomaly table written to: {anomaly_path}")

    # Write monthly seasonality
    seasonal_path = args.output.replace(".csv", "_seasonality.csv")
    monthly.to_csv(seasonal_path, index=False)
    print(f"Seasonality table written to: {seasonal_path}")


if __name__ == "__main__":
    main()
