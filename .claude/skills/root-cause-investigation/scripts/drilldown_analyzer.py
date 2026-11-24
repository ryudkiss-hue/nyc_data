"""
drilldown_analyzer.py — NYC DOT SIM Root Cause Drilldown Analyzer

Decomposes metric changes into contributing dimensions and ranks them
by absolute and relative contribution. Supports inspection completion
rate, violation resolution, ramp completion, and SLA breach metrics.

Usage:
    python drilldown_analyzer.py --input data/inspections_monthly.csv \
        --metric completion_rate --date-col month \
        --baseline-period 2025-01:2025-06 --current-period 2025-07:2025-12 \
        --dimensions borough defect_type material_type

    python drilldown_analyzer.py --demo
"""

import argparse
import json
import sys
from typing import Optional

try:
    import numpy as np
    import pandas as pd
    from scipy import stats
except ImportError:
    print("ERROR: requires numpy, pandas, scipy — pip install numpy pandas scipy")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Metric change validation
# ---------------------------------------------------------------------------


def validate_change(
    series: pd.Series,
    baseline_mask: pd.Series,
    current_mask: pd.Series,
    sigma_threshold: float = 2.0,
) -> dict:
    """Check if metric change exceeds normal variance (rolling avg ± 2σ)."""
    baseline_vals = series[baseline_mask]
    current_vals = series[current_mask]

    baseline_mean = baseline_vals.mean()
    baseline_std = baseline_vals.std()
    current_mean = current_vals.mean()

    z_score = (current_mean - baseline_mean) / baseline_std if baseline_std > 0 else 0
    is_significant = abs(z_score) >= sigma_threshold

    return {
        "baseline_mean": round(baseline_mean, 4),
        "current_mean": round(current_mean, 4),
        "absolute_change": round(current_mean - baseline_mean, 4),
        "relative_change": round((current_mean - baseline_mean) / baseline_mean, 4)
        if baseline_mean != 0
        else None,
        "baseline_std": round(baseline_std, 4),
        "z_score": round(z_score, 4),
        "exceeds_2sigma": is_significant,
    }


# ---------------------------------------------------------------------------
# Dimensional decomposition
# ---------------------------------------------------------------------------


def decompose_by_dimension(
    df: pd.DataFrame,
    metric_col: str,
    dimension_col: str,
    baseline_mask: pd.Series,
    current_mask: pd.Series,
    weight_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    For each value of dimension_col, compute baseline vs. current metric
    and estimate contribution to overall change.
    """
    results = []
    overall_baseline = df.loc[baseline_mask, metric_col].mean()
    overall_current = df.loc[current_mask, metric_col].mean()
    overall_change = overall_current - overall_baseline

    for dim_val, grp in df.groupby(dimension_col):
        b_vals = grp.loc[baseline_mask & (df[dimension_col] == dim_val), metric_col]
        c_vals = grp.loc[current_mask & (df[dimension_col] == dim_val), metric_col]

        if b_vals.empty or c_vals.empty:
            continue

        b_mean = b_vals.mean()
        c_mean = c_vals.mean()
        change = c_mean - b_mean

        # Weight: fraction of total records this dimension represents
        weight = len(grp) / len(df)
        weighted_contribution = change * weight

        results.append(
            {
                "dimension": dimension_col,
                "value": dim_val,
                "n_baseline": len(b_vals),
                "n_current": len(c_vals),
                "baseline_rate": round(b_mean, 4),
                "current_rate": round(c_mean, 4),
                "absolute_change": round(change, 4),
                "weight": round(weight, 4),
                "weighted_contribution": round(weighted_contribution, 4),
                "pct_of_total_change": round(weighted_contribution / overall_change, 4)
                if overall_change != 0
                else 0,
            }
        )

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values("weighted_contribution", key=abs, ascending=False)
    return result_df


def rank_contributors(contributions: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge dimensional contributions and rank by absolute weighted impact."""
    if not contributions:
        return pd.DataFrame()
    combined = pd.concat(contributions, ignore_index=True)
    combined = combined.sort_values("weighted_contribution", key=abs, ascending=False)
    combined["rank"] = range(1, len(combined) + 1)
    return combined


# ---------------------------------------------------------------------------
# Timing analysis
# ---------------------------------------------------------------------------


def identify_change_timing(series: pd.Series, dates: pd.Series) -> dict:
    """Find the approximate date when the metric shift began."""
    df = pd.DataFrame({"date": dates, "metric": series}).sort_values("date")
    df["rolling_mean"] = df["metric"].rolling(3, min_periods=1).mean()
    df["delta"] = df["rolling_mean"].diff()

    if df["delta"].empty:
        return {"change_start": None, "shift_type": "unknown"}

    max_drop_idx = df["delta"].abs().idxmax()
    change_start = df.loc[max_drop_idx, "date"]

    # Classify shift type
    if abs(df["delta"].iloc[1:].max()) > 3 * df["delta"].std():
        shift_type = "sudden"
    else:
        shift_type = "gradual"

    return {
        "change_start": str(change_start),
        "shift_type": shift_type,
        "max_single_period_change": round(float(df["delta"].abs().max()), 4),
    }


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------


def generate_demo_data() -> pd.DataFrame:
    """Monthly inspection summary with simulated metric drop in Q3 2025."""
    np.random.seed(7)
    months = pd.date_range("2025-01", periods=12, freq="MS")
    boroughs = ["MN", "BX", "BK", "QN", "SI"]
    rows = []
    for m in months:
        for b in boroughs:
            is_post = m >= pd.Timestamp("2025-07-01")
            bx_hit = (b == "BX") and is_post
            # Simulate BX having a drop in completion rate from July
            base_rate = {"MN": 0.78, "BX": 0.72, "BK": 0.75, "QN": 0.73, "SI": 0.68}[b]
            rate = base_rate + np.random.normal(0, 0.02) - (0.10 if bx_hit else 0)
            n = int(
                np.random.normal({"MN": 1200, "BX": 900, "BK": 1100, "QN": 950, "SI": 350}[b], 50)
            )
            rows.append(
                {
                    "month": m.strftime("%Y-%m"),
                    "borough": b,
                    "total_inspections": n,
                    "completion_rate": round(max(0, min(1, rate)), 4),
                    "sla_breach_rate": round(
                        max(0, 0.20 + np.random.normal(0, 0.03) + (0.08 if bx_hit else 0)), 4
                    ),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="NYC DOT SIM Root Cause Drilldown Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", help="Path to monthly summary CSV")
    p.add_argument("--demo", action="store_true", help="Run with built-in demo data")
    p.add_argument("--metric", default="completion_rate", help="Metric column to analyze")
    p.add_argument("--date-col", default="month", help="Date column")
    p.add_argument(
        "--baseline-period",
        default="2025-01:2025-06",
        help="Baseline period as START:END (YYYY-MM)",
    )
    p.add_argument(
        "--current-period", default="2025-07:2025-12", help="Current period as START:END (YYYY-MM)"
    )
    p.add_argument(
        "--dimensions", nargs="+", default=["borough"], help="Dimensions to decompose by"
    )
    p.add_argument("--output-json", help="Write ranked contributors JSON to this path")
    return p.parse_args()


def main():
    args = parse_args()

    if args.demo:
        df = generate_demo_data()
        print("Demo data: 12 months × 5 boroughs (simulated Bronx drop Jul–Dec 2025)")
    elif args.input:
        df = pd.read_csv(args.input)
        print(f"Loaded {len(df):,} rows from {args.input}")
    else:
        print("ERROR: provide --input FILE or --demo")
        sys.exit(1)

    b_start, b_end = args.baseline_period.split(":")
    c_start, c_end = args.current_period.split(":")

    baseline_mask = (df[args.date_col] >= b_start) & (df[args.date_col] <= b_end)
    current_mask = (df[args.date_col] >= c_start) & (df[args.date_col] <= c_end)

    print("\n" + "=" * 60)
    print("NYC DOT SIM — Root Cause Drilldown Analysis")
    print("=" * 60)
    print(f"Metric: {args.metric}")
    print(f"Baseline: {b_start} to {b_end}  |  Current: {c_start} to {c_end}")

    # Step 1: Validate change
    change = validate_change(df[args.metric], baseline_mask, current_mask)
    print("\n[1] Change Validation")
    print(f"  Baseline mean: {change['baseline_mean']:.3%}")
    print(f"  Current mean:  {change['current_mean']:.3%}")
    print(f"  Absolute change: {change['absolute_change']:+.3%}")
    print(
        f"  Relative change: {change['relative_change']:+.1%}" if change["relative_change"] else ""
    )
    print(f"  Z-score: {change['z_score']:.2f}")
    print(
        f"  Exceeds 2σ threshold: {'YES — real signal' if change['exceeds_2sigma'] else 'NO — within normal variance'}"
    )

    # Step 2: Timing
    if args.date_col in df.columns:
        agg = df.groupby(args.date_col)[args.metric].mean()
        timing = identify_change_timing(agg, pd.Series(agg.index))
        print("\n[2] Change Timing")
        print(f"  Shift type: {timing['shift_type']}")
        print(f"  Change start: {timing['change_start']}")
        print(f"  Max single-period delta: {timing['max_single_period_change']:.3%}")

    # Step 3: Dimension decomposition
    contributions = []
    for dim in args.dimensions:
        if dim not in df.columns:
            print(f"\n  WARNING: dimension '{dim}' not found in data — skipping")
            continue
        contrib = decompose_by_dimension(df, args.metric, dim, baseline_mask, current_mask)
        contributions.append(contrib)

        print(f"\n[3] Decomposition by {dim}")
        if not contrib.empty:
            print(
                f"  {'Value':<20} {'Baseline':>10}  {'Current':>10}  {'Change':>8}  {'Contribution':>13}"
            )
            print("  " + "-" * 68)
            for _, row in contrib.iterrows():
                print(
                    f"  {str(row['value']):<20} {row['baseline_rate']:>9.1%}  "
                    f"{row['current_rate']:>9.1%}  {row['absolute_change']:>+7.1%}  "
                    f"{row['pct_of_total_change']:>12.1%}"
                )

    # Step 4: Ranked contributors
    all_ranked = rank_contributors(contributions)
    if not all_ranked.empty:
        print("\n[4] Top Contributors (ranked by weighted impact)")
        top5 = all_ranked.head(5)
        print(
            top5[
                ["rank", "dimension", "value", "absolute_change", "weight", "pct_of_total_change"]
            ].to_string(index=False)
        )

    if args.output_json and not all_ranked.empty:
        out = all_ranked.head(10).to_dict(orient="records")
        with open(args.output_json, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\n  Contributors written to {args.output_json}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
