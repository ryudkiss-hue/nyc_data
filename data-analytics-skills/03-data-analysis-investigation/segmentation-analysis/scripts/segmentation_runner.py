"""
Segmentation Runner

Profile segments by comparing their metric distributions to the overall population.
Identifies over- and under-indexing segments and ranks them by impact.

Usage:
    python segmentation_runner.py --demo
    python segmentation_runner.py --csv users.csv \
        --segment-col plan --metric-col ltv --output segments.md
    python segmentation_runner.py --csv orders.csv \
        --segment-col region --metric-col revenue --agg sum
"""

import argparse
import csv
import math
import sys
from collections import defaultdict
from statistics import mean, stdev


def load_csv(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def profile_segments(rows: list[dict], segment_col: str, metric_col: str,
                     agg: str = "mean") -> dict:
    """
    Compute per-segment and overall statistics.

    agg: "mean" (average metric), "sum" (total metric), or "count" (row count)
    """
    groups: dict[str, list[float]] = defaultdict(list)
    all_values = []

    for row in rows:
        seg = row.get(segment_col, "unknown")
        val = float(row.get(metric_col, 0))
        groups[seg].append(val)
        all_values.append(val)

    def _agg(values):
        if agg == "sum":
            return sum(values)
        elif agg == "count":
            return len(values)
        else:
            return mean(values)

    overall = _agg(all_values)
    total_n = len(all_values)

    segments = []
    for seg, values in sorted(groups.items()):
        seg_val = _agg(values)
        n = len(values)
        share_pct = n / total_n * 100
        index = seg_val / overall * 100 if overall != 0 else 0

        entry = {
            "segment": seg,
            "n": n,
            "share_pct": round(share_pct, 1),
            "metric_value": round(seg_val, 2),
            "overall_value": round(overall, 2),
            "index": round(index, 1),
            "diff_from_overall": round(seg_val - overall, 2),
        }

        # Significance flag: Z-score of segment mean vs overall mean (mean agg only)
        if agg == "mean" and len(values) > 1 and len(all_values) > 1:
            try:
                s = stdev(values)
                se = s / math.sqrt(n)
                z = (seg_val - overall) / se if se > 0 else 0
                entry["z_score"] = round(z, 2)
                entry["notable"] = abs(z) > 1.96
            except Exception:
                entry["z_score"] = None
                entry["notable"] = False
        else:
            entry["z_score"] = None
            entry["notable"] = False

        segments.append(entry)

    return {
        "segments": sorted(segments, key=lambda s: abs(s["diff_from_overall"]), reverse=True),
        "overall": round(overall, 2),
        "total_n": total_n,
        "agg": agg,
        "metric": metric_col,
        "segment_col": segment_col,
    }


def format_report(profile: dict) -> str:
    lines = [
        "=" * 70,
        f"  SEGMENTATION ANALYSIS: {profile['metric'].upper()} by {profile['segment_col'].upper()}",
        f"  Aggregation: {profile['agg']}  |  Overall {profile['agg']}: {profile['overall']:,.2f}  |  N={profile['total_n']:,}",
        "=" * 70,
        f"\n  {'Segment':<22} {'N':>7}  {'Share':>6}  {'Value':>12}  {'Index':>7}  {'Notable':>8}",
        "  " + "-" * 64,
    ]

    for s in profile["segments"]:
        notable = "*** " if s["notable"] else ""
        lines.append(
            f"  {s['segment']:<22} {s['n']:>7,}  {s['share_pct']:>5.1f}%  "
            f"{s['metric_value']:>12,.2f}  {s['index']:>6.0f}   {notable}"
        )

    # Highlight over-indexers and under-indexers
    over = [s for s in profile["segments"] if s["index"] >= 120]
    under = [s for s in profile["segments"] if s["index"] <= 80]

    if over:
        lines.append("\n  OVER-INDEXING SEGMENTS (index ≥ 120):")
        for s in over:
            lines.append(f"    - {s['segment']}: index {s['index']:.0f}")

    if under:
        lines.append("\n  UNDER-INDEXING SEGMENTS (index ≤ 80):")
        for s in under:
            lines.append(f"    - {s['segment']}: index {s['index']:.0f}")

    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Profile segments against overall population.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--csv", dest="csv_path")
    parser.add_argument("--segment-col", default="segment")
    parser.add_argument("--metric-col", default="value")
    parser.add_argument("--agg", choices=["mean", "sum", "count"], default="mean")
    parser.add_argument("--output", help="Write report to file")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    if not args.csv_path:
        parser.error("Provide --csv or --demo")

    rows = load_csv(args.csv_path)
    profile = profile_segments(rows, args.segment_col, args.metric_col, args.agg)
    report = format_report(profile)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


def _demo():
    rows = [
        {"plan": "Enterprise", "ltv": 12_400}, {"plan": "Enterprise", "ltv": 15_800},
        {"plan": "Enterprise", "ltv": 11_200}, {"plan": "Enterprise", "ltv": 18_000},
        {"plan": "Pro",        "ltv": 3_800},  {"plan": "Pro",        "ltv": 4_200},
        {"plan": "Pro",        "ltv": 3_600},  {"plan": "Pro",        "ltv": 4_500},
        {"plan": "Pro",        "ltv": 3_900},  {"plan": "Pro",        "ltv": 4_100},
        {"plan": "Basic",      "ltv": 1_200},  {"plan": "Basic",      "ltv": 950},
        {"plan": "Basic",      "ltv": 1_100},  {"plan": "Basic",      "ltv": 1_350},
        {"plan": "Basic",      "ltv": 880},    {"plan": "Basic",      "ltv": 1_050},
        {"plan": "Free",       "ltv": 0},      {"plan": "Free",       "ltv": 120},
        {"plan": "Free",       "ltv": 0},      {"plan": "Free",       "ltv": 80},
    ]
    profile = profile_segments(rows, "plan", "ltv", agg="mean")
    print(format_report(profile))


if __name__ == "__main__":
    _demo()
