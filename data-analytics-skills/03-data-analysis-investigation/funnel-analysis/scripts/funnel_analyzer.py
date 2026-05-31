"""
Funnel Analyzer

Calculates step-by-step conversion rates, absolute drop-off counts,
and identifies the highest-impact drop-off step in a funnel.

Usage:
    python funnel_analyzer.py --steps "Visited,Signed Up,Activated,Paid" \
        --counts "10000,3200,1800,720"
    python funnel_analyzer.py --csv funnel_data.csv --steps-col step \
        --counts-col users --output funnel_report.md
    python funnel_analyzer.py --demo
"""

import argparse
import csv
import sys


def analyze_funnel(steps: list[str], counts: list[int]) -> list[dict]:
    """
    Compute step-by-step and overall conversion, drop-off absolute and rate.

    Returns a list of step dicts ordered by funnel position.
    """
    if len(steps) != len(counts):
        raise ValueError("steps and counts must have equal length")
    if not steps:
        raise ValueError("Funnel must have at least one step")

    top = counts[0]
    results = []

    for i, (step, count) in enumerate(zip(steps, counts)):
        prev_count = counts[i - 1] if i > 0 else count
        step_conv = count / prev_count if prev_count > 0 else 0
        overall_conv = count / top if top > 0 else 0
        dropoff_n = prev_count - count if i > 0 else 0
        dropoff_rate = 1 - step_conv if i > 0 else 0

        results.append({
            "step": step,
            "users": count,
            "step_conversion": round(step_conv, 6),
            "step_conversion_pct": round(step_conv * 100, 2),
            "overall_conversion": round(overall_conv, 6),
            "overall_conversion_pct": round(overall_conv * 100, 2),
            "dropoff_n": dropoff_n,
            "dropoff_rate": round(dropoff_rate, 6),
            "dropoff_pct": round(dropoff_rate * 100, 2),
        })

    return results


def biggest_opportunity(steps: list[dict]) -> dict:
    """Return the step with the largest absolute drop-off (highest recovery opportunity)."""
    return max(steps[1:], key=lambda s: s["dropoff_n"]) if len(steps) > 1 else steps[0]


def format_report(steps: list[dict], title: str = "Funnel Analysis") -> str:
    lines = [
        "=" * 65,
        f"  {title.upper()}",
        "=" * 65,
        f"  {'Step':<22} {'Users':>8}  {'Step Conv':>10}  {'Overall':>8}  {'Drop-off':>10}",
        "  " + "-" * 61,
    ]

    for s in steps:
        dropoff_str = f"-{s['dropoff_n']:,} ({s['dropoff_pct']:.1f}%)" if s["dropoff_n"] else "—"
        lines.append(
            f"  {s['step']:<22} {s['users']:>8,}  {s['step_conversion_pct']:>9.1f}%"
            f"  {s['overall_conversion_pct']:>7.1f}%  {dropoff_str:>10}"
        )

    top_op = biggest_opportunity(steps)
    overall_final = steps[-1]["overall_conversion_pct"]

    lines += [
        "  " + "-" * 61,
        f"  Overall funnel conversion: {overall_final:.1f}%",
        "",
        "  HIGHEST IMPACT DROP-OFF:",
        f"  → {top_op['step']}: lost {top_op['dropoff_n']:,} users ({top_op['dropoff_pct']:.1f}% of prior step)",
        "  This is the best place to focus optimisation effort.",
        "=" * 65,
    ]

    return "\n".join(lines)


def load_funnel_from_csv(filepath: str, step_col: str, count_col: str) -> tuple[list, list]:
    steps, counts = [], []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            steps.append(row[step_col].strip())
            counts.append(int(row[count_col]))
    return steps, counts


def main():
    parser = argparse.ArgumentParser(description="Analyze a conversion funnel.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--steps", help="Comma-separated step names")
    parser.add_argument("--counts", help="Comma-separated user counts matching --steps")
    parser.add_argument("--csv", dest="csv_path", help="CSV file with funnel data")
    parser.add_argument("--steps-col", default="step")
    parser.add_argument("--counts-col", default="users")
    parser.add_argument("--title", default="Funnel Analysis")
    parser.add_argument("--output", help="Write report to file")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    if args.steps and args.counts:
        steps = [s.strip() for s in args.steps.split(",")]
        counts = [int(c.strip()) for c in args.counts.split(",")]
    elif args.csv_path:
        steps, counts = load_funnel_from_csv(args.csv_path, args.steps_col, args.counts_col)
    else:
        parser.error("Provide --steps + --counts, --csv, or --demo")

    result = analyze_funnel(steps, counts)
    report = format_report(result, args.title)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


def _demo():
    steps = ["Landing Page", "Sign Up", "Email Verified", "Profile Complete", "First Purchase"]
    counts = [25_000, 8_500, 5_100, 3_200, 960]
    result = analyze_funnel(steps, counts)
    print(format_report(result, "New User Acquisition Funnel"))
    print()
    top = biggest_opportunity(result)
    print(f"Biggest opportunity: {top['step']} (lost {top['dropoff_n']:,} users)")


if __name__ == "__main__":
    _demo()
