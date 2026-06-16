"""
saas_metrics.py — NYC DOT SIM Operations Metrics Calculator

Adapted for public-sector program metrics: inspection throughput, violation
resolution rates, SLA compliance, ramp completion, and cost-per-inspection.

Usage:
    python saas_metrics.py --input data/inspection_monthly.csv \
        --date-col month --volume-col inspections_completed \
        --resolved-col violations_resolved --period 2026-01

    python saas_metrics.py --demo
"""

import argparse
import sys
from datetime import datetime, timedelta

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("ERROR: requires numpy and pandas — pip install numpy pandas")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------


def compute_throughput_metrics(df: pd.DataFrame, volume_col: str, date_col: str) -> pd.DataFrame:
    """Month-over-month throughput: total, growth rate, rolling 3M average."""
    df = df.copy().sort_values(date_col)
    df["mom_growth"] = df[volume_col].pct_change()
    df["rolling_3m_avg"] = df[volume_col].rolling(3, min_periods=1).mean().round(1)
    df["cumulative"] = df[volume_col].cumsum()
    return df


def compute_resolution_rate(resolved: pd.Series, total: pd.Series, window: int = 3) -> pd.DataFrame:
    """Resolution rate with rolling average and trend direction."""
    rate = (resolved / total.replace(0, np.nan)).round(4)
    rolling = rate.rolling(window, min_periods=1).mean().round(4)
    trend = rate.diff()
    return pd.DataFrame(
        {
            "resolution_rate": rate,
            f"rolling_{window}m_rate": rolling,
            "trend": trend.apply(
                lambda x: "improving" if x > 0.005 else ("declining" if x < -0.005 else "stable")
            ),
        }
    )


def compute_sla_compliance(
    df: pd.DataFrame,
    created_col: str = "created_date",
    completed_col: str = "completion_date",
    sla_days: int = 14,
) -> dict:
    """SLA compliance rate: % of records closed within threshold."""
    df = df.copy()
    df[created_col] = pd.to_datetime(df[created_col], errors="coerce")
    df[completed_col] = pd.to_datetime(df[completed_col], errors="coerce")
    completed = df[df[completed_col].notna()].copy()
    if completed.empty:
        return {"error": "No completed records found"}
    completed["days_to_close"] = (completed[completed_col] - completed[created_col]).dt.days
    within_sla = (completed["days_to_close"] <= sla_days).sum()
    total = len(completed)
    median_days = completed["days_to_close"].median()
    p90_days = completed["days_to_close"].quantile(0.90)
    return {
        "sla_days": sla_days,
        "total_completed": total,
        "within_sla": int(within_sla),
        "breach_count": int(total - within_sla),
        "compliance_rate": round(within_sla / total, 4),
        "median_days_to_close": round(median_days, 1),
        "p90_days_to_close": round(p90_days, 1),
    }


def compute_borough_scorecard(
    df: pd.DataFrame,
    borough_col: str = "borough",
    status_col: str = "status",
    completed_value: str = "COMPLETED",
) -> pd.DataFrame:
    """Per-borough completion rate and volume breakdown."""
    df = df.copy()
    df[borough_col] = df[borough_col].str.upper().str.strip()
    borough_map = {
        "MN": "Manhattan",
        "BX": "Bronx",
        "BK": "Brooklyn",
        "QN": "Queens",
        "SI": "Staten Island",
    }
    # normalise full names to codes
    rev_map = {v.upper(): k for k, v in borough_map.items()}
    df[borough_col] = df[borough_col].replace(rev_map)

    grp = df.groupby(borough_col)
    total = grp[status_col].count()
    completed = grp[status_col].apply(lambda s: (s.str.upper() == completed_value.upper()).sum())
    rate = (completed / total.replace(0, np.nan)).round(4)
    result = (
        pd.DataFrame(
            {
                "borough_code": total.index,
                "borough_name": [borough_map.get(b, b) for b in total.index],
                "total": total.values,
                "completed": completed.values,
                "completion_rate": rate.values,
            }
        )
        .sort_values("completion_rate", ascending=False)
        .reset_index(drop=True)
    )
    return result


def compute_quick_ratio(new: float, expansion: float, churned: float, contracted: float) -> float:
    """Quick ratio = (new + expansion) / (churned + contracted). >1 = growing."""
    denominator = churned + contracted
    if denominator == 0:
        return float("inf")
    return round((new + expansion) / denominator, 2)


def compute_cost_per_inspection(total_cost: float, inspections_completed: int) -> dict:
    """Unit cost metrics for budget reporting."""
    if inspections_completed == 0:
        return {"error": "No completed inspections"}
    cpi = total_cost / inspections_completed
    return {
        "total_cost": total_cost,
        "inspections_completed": inspections_completed,
        "cost_per_inspection": round(cpi, 2),
        "cost_per_1000": round(cpi * 1000, 2),
    }


# ---------------------------------------------------------------------------
# Demo data generator
# ---------------------------------------------------------------------------


def generate_demo_data() -> pd.DataFrame:
    """12 months of synthetic NYC DOT inspection summary data."""
    months = pd.date_range("2025-07", periods=12, freq="MS")
    np.random.seed(42)
    base = 3200
    rows = []
    for i, m in enumerate(months):
        inspections = int(base + np.random.normal(0, 150) + i * 25)
        resolved = int(inspections * np.random.uniform(0.68, 0.79))
        sla_breach = int(inspections * np.random.uniform(0.18, 0.26))
        rows.append(
            {
                "month": m.strftime("%Y-%m"),
                "inspections_completed": inspections,
                "violations_resolved": resolved,
                "sla_breaches": sla_breach,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="NYC DOT SIM Operations Metrics Calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", help="Path to monthly summary CSV")
    p.add_argument("--demo", action="store_true", help="Run with built-in demo data")
    p.add_argument("--date-col", default="month", help="Date/month column")
    p.add_argument("--volume-col", default="inspections_completed")
    p.add_argument("--resolved-col", default="violations_resolved")
    p.add_argument("--period", help="Focus period (YYYY-MM) for point-in-time metrics")
    p.add_argument(
        "--sla-days", type=int, default=14, help="SLA threshold in days (default 14 = HIGH)"
    )
    p.add_argument("--total-cost", type=float, help="Total program cost for CPI calculation")
    return p.parse_args()


def main():
    args = parse_args()

    if args.demo:
        df = generate_demo_data()
        print("Running with demo data (12 months, July 2025 – June 2026)")
    elif args.input:
        df = pd.read_csv(args.input)
        print(f"Loaded {len(df)} rows from {args.input}")
    else:
        print("ERROR: provide --input FILE or --demo")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("NYC DOT SIM — Operations Metrics Report")
    print("=" * 60)

    # Throughput
    throughput = compute_throughput_metrics(df, args.volume_col, args.date_col)
    print("\n[1] Inspection Throughput")
    print(
        throughput[[args.date_col, args.volume_col, "mom_growth", "rolling_3m_avg"]].to_string(
            index=False
        )
    )
    total_inspections = df[args.volume_col].sum()
    avg_monthly = df[args.volume_col].mean()
    print(f"\n  Total inspections (period): {total_inspections:,}")
    print(f"  Avg monthly: {avg_monthly:,.0f}")

    # Resolution rate
    if args.resolved_col in df.columns:
        res = compute_resolution_rate(df[args.resolved_col], df[args.volume_col])
        latest_rate = res["resolution_rate"].iloc[-1]
        latest_trend = res["trend"].iloc[-1]
        print("\n[2] Violation Resolution Rate")
        print(f"  Latest rate: {latest_rate:.1%}  |  Trend: {latest_trend}")
        print(f"  Rolling 3M avg: {res['rolling_3m_rate'].iloc[-1]:.1%}")

    # SLA compliance (if breach data present)
    if "sla_breaches" in df.columns:
        breach_rate = df["sla_breaches"].sum() / total_inspections
        print(f"\n[3] SLA Compliance (HIGH tier = {args.sla_days}d)")
        print(f"  Total breaches: {df['sla_breaches'].sum():,}")
        print(f"  Breach rate: {breach_rate:.1%}")
        print(f"  Compliance rate: {1 - breach_rate:.1%}")
        benchmark_label = (
            "GOOD" if breach_rate < 0.15 else ("AVG" if breach_rate < 0.25 else "POOR")
        )
        print(f"  Benchmark: {benchmark_label} (good <15%, poor >25%)")

    # Cost per inspection
    if args.total_cost:
        cpi = compute_cost_per_inspection(args.total_cost, total_inspections)
        print("\n[4] Cost per Inspection")
        print(f"  Total cost: ${cpi['total_cost']:,.0f}")
        print(f"  CPI: ${cpi['cost_per_inspection']:.2f}")
        print(f"  Cost per 1,000 inspections: ${cpi['cost_per_1000']:,.2f}")

    # Borough scorecard placeholder
    if "borough" in df.columns and "status" in df.columns:
        scorecard = compute_borough_scorecard(df)
        print("\n[5] Borough Scorecard")
        print(scorecard.to_string(index=False))

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
