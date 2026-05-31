"""
Drill-Down / Root Cause Analyzer

Given a metric value change, breaks down contribution by one or more
dimensions to identify which segments drive the movement.

Usage:
    python drilldown_analyzer.py --demo
    python drilldown_analyzer.py --csv data.csv --metric revenue \
        --dimension region --period-col month \
        --period-a 2025-01 --period-b 2025-02
    python drilldown_analyzer.py --csv data.csv --metric revenue \
        --dimension region product_line --period-col month \
        --period-a 2025-01 --period-b 2025-02
"""

import argparse
import csv
import sys
from collections import defaultdict


def load_csv(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict], dimension: str, metric: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        key = row.get(dimension, "unknown")
        totals[key] += float(row.get(metric, 0))
    return dict(totals)


def drill_down(rows_a: list[dict], rows_b: list[dict],
               dimensions: list[str], metric: str) -> list[dict]:
    """
    For each dimension value present in either period, compute:
      - value_a, value_b, absolute_change, pct_change, contribution_pct
    """
    results = []

    for dim in dimensions:
        agg_a = aggregate(rows_a, dim, metric)
        agg_b = aggregate(rows_b, dim, metric)
        total_a = sum(agg_a.values())
        total_b = sum(agg_b.values())
        total_change = total_b - total_a

        all_keys = sorted(set(agg_a) | set(agg_b))
        for key in all_keys:
            v_a = agg_a.get(key, 0.0)
            v_b = agg_b.get(key, 0.0)
            change = v_b - v_a
            pct_change = change / v_a if v_a != 0 else float("inf")
            contribution = change / total_change if total_change != 0 else 0.0
            share_a = v_a / total_a if total_a else 0
            share_b = v_b / total_b if total_b else 0
            mix_effect = (share_b - share_a) * total_a

            results.append({
                "dimension": dim,
                "segment": key,
                "value_a": round(v_a, 2),
                "value_b": round(v_b, 2),
                "absolute_change": round(change, 2),
                "pct_change": round(pct_change * 100, 2) if pct_change != float("inf") else None,
                "contribution_pct": round(contribution * 100, 2),
                "mix_effect": round(mix_effect, 2),
            })

    return sorted(results, key=lambda r: abs(r["absolute_change"]), reverse=True)


def format_report(breakdown: list[dict], metric: str, period_a: str, period_b: str) -> str:
    lines = [
        "=" * 70,
        f"  ROOT CAUSE DRILL-DOWN: {metric.upper()}",
        f"  Period A: {period_a}  →  Period B: {period_b}",
        "=" * 70,
    ]

    current_dim = None
    for row in breakdown:
        if row["dimension"] != current_dim:
            current_dim = row["dimension"]
            lines.append(f"\n  DIMENSION: {current_dim.upper()}")
            lines.append(f"  {'Segment':<25} {'A':>12}  {'B':>12}  {'Change':>12}  {'Contribution':>13}")
            lines.append("  " + "-" * 66)

        pct = f"{row['pct_change']:+.1f}%" if row["pct_change"] is not None else "new"
        contrib = f"{row['contribution_pct']:+.1f}%"
        lines.append(
            f"  {row['segment']:<25} {row['value_a']:>12,.0f}  {row['value_b']:>12,.0f}"
            f"  {row['absolute_change']:>+12,.0f} [{pct}]  {contrib:>12}"
        )

    top = breakdown[0] if breakdown else None
    if top:
        lines += [
            "",
            f"  TOP DRIVER: {top['dimension']} = '{top['segment']}'",
            f"  Drove {top['contribution_pct']:+.1f}% of total metric change.",
            "  Investigate this segment first.",
        ]

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Drill down into a metric change by dimension.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--csv", dest="csv_path")
    parser.add_argument("--metric", default="value")
    parser.add_argument("--dimension", nargs="+", default=["segment"])
    parser.add_argument("--period-col", default="period")
    parser.add_argument("--period-a", help="Label for period A")
    parser.add_argument("--period-b", help="Label for period B")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    if not args.csv_path:
        parser.error("Provide --csv or --demo")

    rows = load_csv(args.csv_path)
    rows_a = [r for r in rows if r.get(args.period_col) == args.period_a]
    rows_b = [r for r in rows if r.get(args.period_col) == args.period_b]

    if not rows_a:
        sys.exit(f"No rows found for period-a={args.period_a}")
    if not rows_b:
        sys.exit(f"No rows found for period-b={args.period_b}")

    breakdown = drill_down(rows_a, rows_b, args.dimension, args.metric)
    print(format_report(breakdown, args.metric, args.period_a, args.period_b))


def _demo():
    # Simulated revenue by region — Jan vs Feb
    rows_a = [
        {"period": "2025-01", "region": "EMEA",   "product": "Pro",   "revenue": 120_000},
        {"period": "2025-01", "region": "EMEA",   "product": "Basic", "revenue": 45_000},
        {"period": "2025-01", "region": "AMER",   "product": "Pro",   "revenue": 220_000},
        {"period": "2025-01", "region": "AMER",   "product": "Basic", "revenue": 80_000},
        {"period": "2025-01", "region": "APAC",   "product": "Pro",   "revenue": 55_000},
    ]
    rows_b = [
        {"period": "2025-02", "region": "EMEA",   "product": "Pro",   "revenue": 98_000},
        {"period": "2025-02", "region": "EMEA",   "product": "Basic", "revenue": 47_000},
        {"period": "2025-02", "region": "AMER",   "product": "Pro",   "revenue": 215_000},
        {"period": "2025-02", "region": "AMER",   "product": "Basic", "revenue": 82_000},
        {"period": "2025-02", "region": "APAC",   "product": "Pro",   "revenue": 60_000},
    ]
    breakdown = drill_down(rows_a, rows_b, ["region", "product"], "revenue")
    print(format_report(breakdown, "revenue", "2025-01", "2025-02"))


if __name__ == "__main__":
    _demo()
