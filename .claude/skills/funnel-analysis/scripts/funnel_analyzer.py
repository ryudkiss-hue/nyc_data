"""
funnel_analyzer.py — NYC DOT SIM Inspection Workflow Funnel Analyzer

Tracks conversion through the sidewalk inspection lifecycle:
  Created → Assigned → Inspected → Violation Issued → Resolved

Usage:
    python funnel_analyzer.py --input data/inspections.csv \
        --id-col objectid --steps created_date assigned_date inspection_date \
        --window 90 --segment borough

    python funnel_analyzer.py --demo
"""

import argparse
import sys
from typing import Optional

try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("ERROR: requires numpy and pandas — pip install numpy pandas")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Default NYC DOT inspection funnel definition
# ---------------------------------------------------------------------------

NYC_DOT_FUNNEL_STEPS = [
    ("created", "created_date", "Inspection Record Created"),
    ("assigned", "assigned_date", "Assigned to Inspector"),
    ("inspected", "inspection_date", "Inspection Conducted"),
    ("violation", "violation_date", "Violation Issued"),
    ("resolved", "completion_date", "Resolved / Completed"),
]


# ---------------------------------------------------------------------------
# Core funnel logic
# ---------------------------------------------------------------------------


def build_funnel(
    df: pd.DataFrame,
    step_cols: list[str],
    step_labels: list[str],
    id_col: str,
    window_days: Optional[int] = 90,
    start_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute step-by-step conversion through the funnel.

    Args:
        df: DataFrame with one row per record
        step_cols: ordered list of date columns marking each funnel step
        step_labels: human-readable names for each step
        id_col: unique record identifier
        window_days: max days from first step to count as converted
        start_col: first step column (default: step_cols[0])

    Returns:
        DataFrame with step name, count, conversion rate, drop-off count
    """
    df = df.copy()
    for col in step_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    start = start_col or step_cols[0]

    # Apply completion window filter
    if window_days and start in df.columns:
        cutoff = df[start] + pd.Timedelta(days=window_days)
        for col in step_cols[1:]:
            df[col] = df[col].where(df[col] <= cutoff, other=pd.NaT)

    records = []
    n_base = df[start].notna().sum()

    for i, (col, label) in enumerate(zip(step_cols, step_labels)):
        n = df[col].notna().sum()
        if i == 0:
            conv_from_prev = 1.0
            conv_from_top = 1.0
            drop_count = 0
            drop_rate = 0.0
        else:
            prev_col = step_cols[i - 1]
            n_prev = df[prev_col].notna().sum()
            conv_from_prev = n / n_prev if n_prev > 0 else 0.0
            conv_from_top = n / n_base if n_base > 0 else 0.0
            drop_count = n_prev - n
            drop_rate = drop_count / n_prev if n_prev > 0 else 0.0

        records.append(
            {
                "step": i,
                "step_label": label,
                "column": col,
                "count": int(n),
                "conv_from_prev": round(conv_from_prev, 4),
                "conv_from_top": round(conv_from_top, 4),
                "drop_count": int(drop_count),
                "drop_rate": round(drop_rate, 4),
            }
        )

    return pd.DataFrame(records)


def time_to_convert(df: pd.DataFrame, from_col: str, to_col: str, label: str = "") -> dict:
    """Median and distribution of time between two funnel steps."""
    df = df.copy()
    df[from_col] = pd.to_datetime(df[from_col], errors="coerce")
    df[to_col] = pd.to_datetime(df[to_col], errors="coerce")
    both = df[df[from_col].notna() & df[to_col].notna()].copy()
    if both.empty:
        return {"label": label, "n": 0, "error": "No records with both dates"}
    days = (both[to_col] - both[from_col]).dt.days
    days = days[days >= 0]
    return {
        "label": label,
        "n": len(days),
        "median_days": round(days.median(), 1),
        "p25_days": round(days.quantile(0.25), 1),
        "p75_days": round(days.quantile(0.75), 1),
        "p90_days": round(days.quantile(0.90), 1),
        "mean_days": round(days.mean(), 1),
    }


def segment_funnel(
    df: pd.DataFrame,
    step_cols: list[str],
    step_labels: list[str],
    id_col: str,
    segment_col: str,
    window_days: Optional[int] = 90,
) -> pd.DataFrame:
    """Run funnel analysis for each segment value and return comparison."""
    rows = []
    for seg_val, seg_df in df.groupby(segment_col):
        funnel = build_funnel(seg_df, step_cols, step_labels, id_col, window_days)
        overall_conv = funnel.iloc[-1]["conv_from_top"]
        biggest_drop_idx = funnel["drop_rate"].iloc[1:].idxmax()
        biggest_drop_step = funnel.loc[biggest_drop_idx, "step_label"]
        rows.append(
            {
                segment_col: seg_val,
                "n_top_of_funnel": int(funnel.iloc[0]["count"]),
                "n_completed": int(funnel.iloc[-1]["count"]),
                "overall_conversion": round(overall_conv, 4),
                "biggest_drop_step": biggest_drop_step,
                "biggest_drop_rate": round(funnel.loc[biggest_drop_idx, "drop_rate"], 4),
            }
        )
    return pd.DataFrame(rows).sort_values("overall_conversion", ascending=False)


def prioritise_recommendations(
    funnel_df: pd.DataFrame, revenue_per_completion: float = 0
) -> pd.DataFrame:
    """Rank drop-off points by records lost × (optional) revenue impact."""
    drops = funnel_df[funnel_df["step"] > 0].copy()
    if revenue_per_completion > 0:
        drops["revenue_at_risk"] = drops["drop_count"] * revenue_per_completion
    drops = drops.sort_values("drop_count", ascending=False)
    drops["priority_rank"] = range(1, len(drops) + 1)
    return drops[
        ["priority_rank", "step_label", "drop_count", "drop_rate"]
        + (["revenue_at_risk"] if revenue_per_completion > 0 else [])
    ]


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------


def generate_demo_data() -> pd.DataFrame:
    """Synthetic inspection lifecycle data for demo."""
    np.random.seed(99)
    n = 5000
    start = pd.Timestamp("2025-06-01")
    created = start + pd.to_timedelta(np.random.randint(0, 365, n), unit="D")
    boroughs = np.random.choice(["MN", "BX", "BK", "QN", "SI"], n, p=[0.25, 0.20, 0.25, 0.20, 0.10])

    assigned_mask = np.random.random(n) < 0.88
    assigned = np.where(
        assigned_mask,
        created + pd.to_timedelta(np.random.randint(1, 5, n), unit="D"),
        pd.NaT,
    )

    inspected_mask = assigned_mask & (np.random.random(n) < 0.82)
    inspected = np.where(
        inspected_mask,
        pd.to_datetime(assigned) + pd.to_timedelta(np.random.randint(3, 14, n), unit="D"),
        pd.NaT,
    )

    violation_mask = inspected_mask & (np.random.random(n) < 0.58)
    violation_date = np.where(
        violation_mask,
        pd.to_datetime(inspected) + pd.to_timedelta(np.random.randint(1, 7, n), unit="D"),
        pd.NaT,
    )

    resolved_mask = violation_mask & (np.random.random(n) < 0.71)
    completion_date = np.where(
        resolved_mask,
        pd.to_datetime(violation_date) + pd.to_timedelta(np.random.randint(7, 45, n), unit="D"),
        pd.NaT,
    )

    return pd.DataFrame(
        {
            "objectid": range(1, n + 1),
            "borough": boroughs,
            "created_date": pd.to_datetime(created),
            "assigned_date": pd.to_datetime(assigned),
            "inspection_date": pd.to_datetime(inspected),
            "violation_date": pd.to_datetime(violation_date),
            "completion_date": pd.to_datetime(completion_date),
        }
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="NYC DOT SIM Inspection Funnel Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", help="Path to CSV with inspection records")
    p.add_argument("--demo", action="store_true", help="Run with built-in demo data")
    p.add_argument("--id-col", default="objectid")
    p.add_argument(
        "--steps",
        nargs="+",
        default=[
            "created_date",
            "assigned_date",
            "inspection_date",
            "violation_date",
            "completion_date",
        ],
        help="Ordered list of date columns defining funnel steps",
    )
    p.add_argument(
        "--labels",
        nargs="+",
        default=["Created", "Assigned", "Inspected", "Violation Issued", "Resolved"],
    )
    p.add_argument("--window", type=int, default=90, help="Completion window in days (default 90)")
    p.add_argument("--segment", help="Column to segment funnel by (e.g. borough)")
    p.add_argument(
        "--revenue-per-completion",
        type=float,
        default=0,
        help="Optional: $ value per completed case for impact ranking",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.demo:
        df = generate_demo_data()
        print(f"Demo data: {len(df):,} records")
    elif args.input:
        df = pd.read_csv(args.input)
        print(f"Loaded {len(df):,} records from {args.input}")
    else:
        print("ERROR: provide --input FILE or --demo")
        sys.exit(1)

    step_cols = args.steps
    step_labels = (
        args.labels
        if len(args.labels) == len(step_cols)
        else [f"Step {i}" for i in range(len(step_cols))]
    )

    print("\n" + "=" * 60)
    print("NYC DOT SIM — Inspection Workflow Funnel Analysis")
    print("=" * 60)
    print(f"Completion window: {args.window} days | n={len(df):,}")

    funnel = build_funnel(df, step_cols, step_labels, args.id_col, window_days=args.window)

    print("\n[1] Funnel Overview")
    print(f"  {'Step':<28} {'Count':>8}  {'vs. Prev':>9}  {'vs. Top':>9}  {'Drop':>8}")
    print("  " + "-" * 68)
    for _, row in funnel.iterrows():
        bar = "#" * int(row["conv_from_top"] * 30)
        drop_str = f"-{row['drop_count']:,} ({row['drop_rate']:.1%})" if row["step"] > 0 else ""
        print(
            f"  {row['step_label']:<28} {row['count']:>8,}  "
            f"{row['conv_from_prev']:>8.1%}  {row['conv_from_top']:>8.1%}  {drop_str:>14}"
        )

    # Time between steps
    print("\n[2] Time Between Steps")
    for i in range(1, len(step_cols)):
        ttc = time_to_convert(
            df, step_cols[i - 1], step_cols[i], label=f"{step_labels[i - 1]} → {step_labels[i]}"
        )
        if "error" not in ttc:
            print(f"  {ttc['label']}")
            print(
                f"    n={ttc['n']:,}  median={ttc['median_days']}d  "
                f"p75={ttc['p75_days']}d  p90={ttc['p90_days']}d"
            )

    # Prioritised recommendations
    print("\n[3] Drop-Off Priority (largest to smallest)")
    recs = prioritise_recommendations(funnel, revenue_per_completion=args.revenue_per_completion)
    print(recs.to_string(index=False))

    # Segment breakdown
    if args.segment and args.segment in df.columns:
        print(f"\n[4] Segment Breakdown by {args.segment}")
        seg_result = segment_funnel(
            df, step_cols, step_labels, args.id_col, args.segment, args.window
        )
        print(seg_result.to_string(index=False))

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
