"""
Time Series Analyzer

Detects trends, seasonality patterns, anomalies, and week-over-week /
year-over-year growth rates in ordered metric data.

Usage:
    python ts_analyzer.py --demo
    python ts_analyzer.py --csv metric_daily.csv --date-col date \
        --metric-col revenue --freq weekly
    python ts_analyzer.py --csv data.csv --date-col week --metric-col users \
        --freq weekly --output ts_report.md
"""

import argparse
import csv
import math
import sys
from statistics import mean, stdev


def load_csv(filepath: str, date_col: str, metric_col: str) -> list[dict]:
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({"date": row[date_col], "value": float(row[metric_col])})
    return sorted(rows, key=lambda r: r["date"])


def compute_growth_rates(rows: list[dict], period: int = 1) -> list[dict]:
    """Add period-over-period growth rate to each row."""
    result = []
    for i, row in enumerate(rows):
        prev = rows[i - period]["value"] if i >= period else None
        if prev is not None and prev != 0:
            growth = (row["value"] - prev) / prev
        else:
            growth = None
        result.append({**row, "prev_value": prev, "growth_rate": growth})
    return result


def detect_trend(values: list[float]) -> dict:
    """Simple linear trend via least-squares slope."""
    n = len(values)
    if n < 3:
        return {"slope": None, "direction": "insufficient data"}
    x_mean = (n - 1) / 2
    y_mean = mean(values)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0
    pct_slope = slope / y_mean * 100 if y_mean != 0 else 0
    direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    return {"slope": round(slope, 4), "pct_slope_per_period": round(pct_slope, 3),
            "direction": direction}


def detect_anomalies(rows: list[dict], z_threshold: float = 2.5) -> list[dict]:
    """Flag rows where value is more than z_threshold standard deviations from mean."""
    values = [r["value"] for r in rows]
    if len(values) < 4:
        return []
    mu = mean(values)
    sigma = stdev(values)
    anomalies = []
    for row in rows:
        z = (row["value"] - mu) / sigma if sigma > 0 else 0
        if abs(z) >= z_threshold:
            anomalies.append({
                "date": row["date"],
                "value": row["value"],
                "z_score": round(z, 2),
                "direction": "spike" if z > 0 else "dip",
            })
    return anomalies


def rolling_average(rows: list[dict], window: int = 4) -> list[dict]:
    result = []
    for i, row in enumerate(rows):
        window_vals = [rows[j]["value"] for j in range(max(0, i - window + 1), i + 1)]
        result.append({**row, "rolling_avg": round(mean(window_vals), 2)})
    return result


def summary_stats(values: list[float]) -> dict:
    if not values:
        return {}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return {
        "n": n,
        "mean": round(mean(values), 2),
        "median": round(sorted_vals[n // 2], 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "std": round(stdev(values), 2) if n > 1 else 0,
        "total": round(sum(values), 2),
    }


def format_report(rows: list[dict], trend: dict, anomalies: list[dict],
                  stats: dict, metric: str, freq: str) -> str:
    lines = [
        "=" * 65,
        f"  TIME SERIES ANALYSIS: {metric.upper()}  ({freq})",
        "=" * 65,
        "",
        "--- Summary Statistics ---",
        f"  Periods:  {stats['n']}",
        f"  Mean:     {stats['mean']:,.2f}",
        f"  Median:   {stats['median']:,.2f}",
        f"  Min:      {stats['min']:,.2f}",
        f"  Max:      {stats['max']:,.2f}",
        f"  Std dev:  {stats['std']:,.2f}",
        f"  Total:    {stats['total']:,.2f}",
        "",
        "--- Trend ---",
        f"  Direction: {trend['direction'].upper()}",
    ]

    if trend["slope"] is not None:
        lines.append(f"  Slope: {trend['slope']:+,.4f} per period "
                     f"({trend['pct_slope_per_period']:+.2f}%/period)")

    lines += ["", "--- Recent Periods ---",
              f"  {'Date':<15}  {'Value':>12}  {'Growth':>10}  {'Rolling Avg':>12}"]
    lines.append("  " + "-" * 54)

    for row in rows[-8:]:
        growth = f"{row['growth_rate']:+.1%}" if row.get("growth_rate") is not None else "—"
        rolling = f"{row.get('rolling_avg', ''):>12.2f}" if "rolling_avg" in row else ""
        lines.append(f"  {row['date']:<15}  {row['value']:>12,.2f}  {growth:>10}  {rolling}")

    if anomalies:
        lines += ["", f"--- Anomalies Detected (|z| ≥ 2.5) ---"]
        for a in anomalies:
            lines.append(f"  {a['date']}: {a['value']:,.2f}  [{a['direction'].upper()}, z={a['z_score']}]")
    else:
        lines += ["", "--- No anomalies detected ---"]

    lines.append("=" * 65)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze a time series metric.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--csv", dest="csv_path")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--metric-col", default="value")
    parser.add_argument("--freq", default="weekly", help="Frequency label (weekly/daily/monthly)")
    parser.add_argument("--window", type=int, default=4, help="Rolling average window (default 4)")
    parser.add_argument("--output", help="Write report to file")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    if not args.csv_path:
        parser.error("Provide --csv or --demo")

    rows = load_csv(args.csv_path, args.date_col, args.metric_col)
    rows = compute_growth_rates(rows, period=1)
    rows = rolling_average(rows, window=args.window)
    values = [r["value"] for r in rows]
    trend = detect_trend(values)
    anomalies = detect_anomalies(rows)
    stats = summary_stats(values)
    report = format_report(rows, trend, anomalies, stats, args.metric_col, args.freq)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


def _demo():
    import random
    random.seed(42)
    base = 100_000
    rows_raw = []
    for i in range(24):
        # Slight upward trend + noise + one anomaly
        trend_val = base + i * 2_000 + random.gauss(0, 4_000)
        if i == 18:
            trend_val *= 0.55  # simulate a dip
        rows_raw.append({"date": f"2024-W{i+1:02d}", "value": round(trend_val, 2)})

    rows = compute_growth_rates(rows_raw, period=1)
    rows = rolling_average(rows, window=4)
    values = [r["value"] for r in rows]
    trend = detect_trend(values)
    anomalies = detect_anomalies(rows)
    stats = summary_stats(values)
    print(format_report(rows, trend, anomalies, stats, "weekly_revenue", "weekly"))


if __name__ == "__main__":
    _demo()
