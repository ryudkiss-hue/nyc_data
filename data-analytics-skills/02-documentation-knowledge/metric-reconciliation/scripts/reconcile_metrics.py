"""
Metric Reconciliation Helper

Compare a metric value from two sources for the same period and identify
where the computation paths diverge.

Usage:
    python reconcile_metrics.py --source-a source_a.csv --source-b source_b.csv \
        --metric revenue --date 2025-01-01
    python reconcile_metrics.py --values 125000 118500 --metric revenue --tolerance 0.02
"""

import argparse
import csv
import io
import sys


def compare_values(value_a: float, value_b: float, tolerance: float = 0.001) -> dict:
    """
    Compare two metric values and return reconciliation stats.

    Args:
        value_a: Value from source A
        value_b: Value from source B
        tolerance: Fractional tolerance below which gap is accepted (default 0.1%)

    Returns:
        dict with absolute_diff, pct_diff, within_tolerance, status
    """
    absolute_diff = value_a - value_b
    pct_diff = absolute_diff / value_a if value_a != 0 else float("inf")
    within_tolerance = abs(pct_diff) <= tolerance

    return {
        "value_a": value_a,
        "value_b": value_b,
        "absolute_diff": absolute_diff,
        "pct_diff": pct_diff,
        "within_tolerance": within_tolerance,
        "status": "ACCEPTED" if within_tolerance else "INVESTIGATE",
    }


def load_metric_from_csv(filepath: str, metric_col: str, date_col: str = None, date: str = None) -> float:
    """
    Load a single metric value from a CSV file.

    Sums metric_col for all rows matching date (if provided).
    """
    total = 0.0
    matched = 0

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if date_col and date and row.get(date_col) != date:
                continue
            total += float(row[metric_col])
            matched += 1

    if matched == 0:
        raise ValueError(f"No rows found in {filepath}" + (f" for date {date}" if date else ""))

    return total


def reconciliation_report(result: dict, source_a_label: str, source_b_label: str) -> str:
    """Produce a human-readable reconciliation summary."""
    lines = [
        "=" * 60,
        "METRIC RECONCILIATION REPORT",
        "=" * 60,
        f"  {source_a_label}: {result['value_a']:,.2f}",
        f"  {source_b_label}: {result['value_b']:,.2f}",
        f"  Absolute difference: {result['absolute_diff']:+,.2f}",
        f"  Percentage difference: {result['pct_diff']:+.4%}",
        "",
        f"  STATUS: {result['status']}",
    ]

    if result["within_tolerance"]:
        lines.append("  Gap is within tolerance — no further action required.")
    else:
        lines += [
            "",
            "  NEXT STEPS:",
            "  1. Compare query/pipeline definition for each source side-by-side.",
            "  2. Check: filter conditions, join types, null handling, date truncation.",
            "  3. Pull row-level data to find the first divergence point.",
            "  4. Document the root cause in assets/reconciliation_report_template.md.",
        ]

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Reconcile a metric between two sources.")
    parser.add_argument("--source-a", help="Path to CSV for source A")
    parser.add_argument("--source-b", help="Path to CSV for source B")
    parser.add_argument("--values", nargs=2, type=float, metavar=("A", "B"),
                        help="Direct values: --values 125000 118500")
    parser.add_argument("--metric", required=False, default="value", help="Column name for the metric")
    parser.add_argument("--date-col", default=None, help="Date column name for filtering")
    parser.add_argument("--date", default=None, help="Date to filter on (e.g. 2025-01-01)")
    parser.add_argument("--tolerance", type=float, default=0.001, help="Accepted gap fraction (default 0.001 = 0.1%%)")
    parser.add_argument("--label-a", default="Source A")
    parser.add_argument("--label-b", default="Source B")
    args = parser.parse_args()

    if args.values:
        value_a, value_b = args.values
    elif args.source_a and args.source_b:
        value_a = load_metric_from_csv(args.source_a, args.metric, args.date_col, args.date)
        value_b = load_metric_from_csv(args.source_b, args.metric, args.date_col, args.date)
    else:
        parser.error("Provide --values or both --source-a and --source-b")

    result = compare_values(value_a, value_b, args.tolerance)
    print(reconciliation_report(result, args.label_a, args.label_b))

    sys.exit(0 if result["within_tolerance"] else 1)


if __name__ == "__main__":
    # Demo: two values with a 5.5% gap — should trigger INVESTIGATE
    demo_a = 125_000.0
    demo_b = 118_120.0
    result = compare_values(demo_a, demo_b, tolerance=0.001)
    print(reconciliation_report(result, "Dashboard (Source A)", "Finance Report (Source B)"))
    print()
    print("Demo exited with status:", "ACCEPTED" if result["within_tolerance"] else "INVESTIGATE")
