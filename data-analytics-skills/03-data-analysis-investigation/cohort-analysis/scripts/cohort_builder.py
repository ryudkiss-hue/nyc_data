"""
cohort_builder.py — NYC DOT SIM Cohort Analysis Builder

Assigns inspection/violation records to cohorts by created_date month
and tracks resolution/completion retention across subsequent periods.

Usage:
    python cohort_builder.py --input data/inspections.csv \
        --cohort-col created_date --event-col completion_date \
        --id-col objectid --granularity monthly --periods 12

    python cohort_builder.py --demo
"""

import argparse
import json
import sys
from typing import Optional

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("ERROR: requires numpy and pandas — pip install numpy pandas")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Core cohort logic
# ---------------------------------------------------------------------------


def assign_cohorts(
    df: pd.DataFrame,
    cohort_col: str,
    id_col: str,
    granularity: str = "monthly",
) -> pd.DataFrame:
    """Assign each record to a cohort based on first qualifying event date."""
    df = df.copy()
    df[cohort_col] = pd.to_datetime(df[cohort_col], errors="coerce")
    df = df.dropna(subset=[cohort_col])

    if granularity == "monthly":
        df["cohort"] = df[cohort_col].dt.to_period("M")
    elif granularity == "weekly":
        df["cohort"] = df[cohort_col].dt.to_period("W")
    elif granularity == "quarterly":
        df["cohort"] = df[cohort_col].dt.to_period("Q")
    else:
        raise ValueError(f"granularity must be monthly/weekly/quarterly, got: {granularity}")

    return df


def compute_retention_matrix(
    df: pd.DataFrame,
    cohort_col: str,
    event_col: str,
    id_col: str,
    n_periods: int = 12,
    granularity: str = "monthly",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build cohort × period retention matrix.

    Returns:
        counts_df: absolute counts per cohort × period
        rate_df: retention rates (period 0 = 100%)
    """
    df = assign_cohorts(df, cohort_col, id_col, granularity)
    df[event_col] = pd.to_datetime(df[event_col], errors="coerce")

    # Only keep records with a completion event
    completed = df[df[event_col].notna()].copy()

    if granularity == "monthly":
        completed["event_period"] = completed[event_col].dt.to_period("M")
    elif granularity == "weekly":
        completed["event_period"] = completed[event_col].dt.to_period("W")
    else:
        completed["event_period"] = completed[event_col].dt.to_period("Q")

    completed["period_offset"] = (completed["event_period"] - completed["cohort"]).apply(
        lambda x: x.n if hasattr(x, "n") else int(x)
    )

    # Filter to valid offsets
    completed = completed[
        (completed["period_offset"] >= 0) & (completed["period_offset"] < n_periods)
    ]

    cohort_sizes = df.groupby("cohort")[id_col].count().rename("cohort_size")
    pivot = completed.groupby(["cohort", "period_offset"])[id_col].count().unstack(fill_value=0)

    # Align to n_periods columns
    for p in range(n_periods):
        if p not in pivot.columns:
            pivot[p] = 0
    pivot = pivot[[c for c in range(n_periods) if c in pivot.columns]]
    pivot = pivot.join(cohort_sizes)

    counts = pivot.copy()
    rate = pivot.copy()
    for col in range(n_periods):
        if col in rate.columns:
            rate[col] = (pivot[col] / pivot["cohort_size"].replace(0, np.nan)).round(4)

    return counts.drop(columns=["cohort_size"]), rate.drop(columns=["cohort_size"])


def summarise_cohorts(counts: pd.DataFrame, rates: pd.DataFrame, cohort_sizes: pd.Series) -> dict:
    """Summary statistics: median retention by period, best/worst cohort."""
    median_retention = rates.median().to_dict()
    if 0 in rates.columns:
        period_1_col = 1 if 1 in rates.columns else None
        if period_1_col:
            best_cohort = rates[period_1_col].idxmax()
            worst_cohort = rates[period_1_col].idxmin()
        else:
            best_cohort = worst_cohort = None
    else:
        best_cohort = worst_cohort = None

    return {
        "n_cohorts": len(rates),
        "median_retention_by_period": {str(k): round(v, 4) for k, v in median_retention.items()},
        "best_period1_cohort": str(best_cohort),
        "worst_period1_cohort": str(worst_cohort),
    }


def detect_cliff_drops(rates: pd.DataFrame, threshold: float = 0.15) -> list[dict]:
    """Flag periods where median retention drops by more than threshold."""
    median = rates.median()
    drops = []
    periods = sorted([c for c in median.index if isinstance(c, int)])
    for i in range(1, len(periods)):
        prev, curr = periods[i - 1], periods[i]
        drop = median[prev] - median[curr]
        if drop >= threshold:
            drops.append(
                {
                    "from_period": prev,
                    "to_period": curr,
                    "median_drop": round(drop, 4),
                    "before": round(float(median[prev]), 4),
                    "after": round(float(median[curr]), 4),
                }
            )
    return drops


# ---------------------------------------------------------------------------
# Demo data generator
# ---------------------------------------------------------------------------


def generate_demo_data() -> pd.DataFrame:
    """Generate 18 months of synthetic inspection records."""
    np.random.seed(42)
    n = 8000
    start = pd.Timestamp("2025-01-01")
    end = pd.Timestamp("2026-06-14")
    created = pd.to_datetime(np.random.randint(start.value, end.value, size=n), unit="ns")
    boroughs = np.random.choice(
        ["MN", "BX", "BK", "QN", "SI"], size=n, p=[0.25, 0.20, 0.25, 0.20, 0.10]
    )
    completed_mask = np.random.random(n) < 0.74
    lag_days = np.random.exponential(scale=12, size=n).astype(int) + 1
    completion_date = np.where(
        completed_mask,
        (created + pd.to_timedelta(lag_days, unit="D")).astype("datetime64[ns]"),
        pd.NaT,
    )
    return pd.DataFrame(
        {
            "objectid": range(1, n + 1),
            "created_date": created,
            "completion_date": completion_date,
            "borough": boroughs,
            "status": np.where(completed_mask, "COMPLETED", "OPEN"),
        }
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="NYC DOT SIM Cohort Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", help="Path to CSV with inspection records")
    p.add_argument("--demo", action="store_true", help="Run with built-in demo data")
    p.add_argument("--cohort-col", default="created_date", help="Column for cohort assignment date")
    p.add_argument("--event-col", default="completion_date", help="Column for retention event date")
    p.add_argument("--id-col", default="objectid", help="Unique record identifier column")
    p.add_argument("--granularity", choices=["monthly", "weekly", "quarterly"], default="monthly")
    p.add_argument(
        "--periods", type=int, default=12, help="Number of periods to track (default 12)"
    )
    p.add_argument("--segment", help="Optional: column to segment by (e.g. borough)")
    p.add_argument("--output-json", help="Write summary JSON to this path")
    return p.parse_args()


def main():
    args = parse_args()

    if args.demo:
        df = generate_demo_data()
        print(f"Demo data: {len(df):,} records, Jan 2025 – Jun 2026")
    elif args.input:
        df = pd.read_csv(args.input)
        print(f"Loaded {len(df):,} records from {args.input}")
    else:
        print("ERROR: provide --input FILE or --demo")
        sys.exit(1)

    segments = [None]
    if args.segment and args.segment in df.columns:
        segments = [None] + sorted(df[args.segment].dropna().unique().tolist())

    for seg in segments:
        seg_df = df if seg is None else df[df[args.segment] == seg]
        label = "ALL" if seg is None else f"{args.segment}={seg}"

        counts, rates = compute_retention_matrix(
            seg_df,
            cohort_col=args.cohort_col,
            event_col=args.event_col,
            id_col=args.id_col,
            n_periods=args.periods,
            granularity=args.granularity,
        )

        cohort_sizes = (
            seg_df.assign(
                cohort=pd.to_datetime(seg_df[args.cohort_col], errors="coerce").dt.to_period("M")
            )
            .groupby("cohort")[args.id_col]
            .count()
        )

        summary = summarise_cohorts(counts, rates, cohort_sizes)
        drops = detect_cliff_drops(rates)

        print(f"\n{'=' * 60}")
        print(f"Cohort Retention Analysis — {label}")
        print(f"{'=' * 60}")
        print(f"  Cohorts: {summary['n_cohorts']}  |  Periods tracked: {args.periods}")
        print(f"  Best period-1 cohort: {summary['best_period1_cohort']}")
        print(f"  Worst period-1 cohort: {summary['worst_period1_cohort']}")

        print("\n  Median retention by period:")
        for period, val in list(summary["median_retention_by_period"].items())[: args.periods]:
            bar = "#" * int(float(val) * 30)
            print(f"    Period {period:>2}: {float(val):>6.1%}  {bar}")

        if drops:
            print("\n  Cliff drops detected:")
            for d in drops:
                print(
                    f"    Period {d['from_period']} → {d['to_period']}: "
                    f"{d['before']:.1%} → {d['after']:.1%} (drop: {d['median_drop']:.1%})"
                )

        if args.output_json and seg is None:
            with open(args.output_json, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"\n  Summary written to {args.output_json}")

        if seg is not None:
            break  # Only print full breakdown for "ALL" by default


if __name__ == "__main__":
    main()
