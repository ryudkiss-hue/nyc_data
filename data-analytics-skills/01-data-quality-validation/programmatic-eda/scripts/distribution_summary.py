"""
Produce descriptive statistics and ASCII histograms for numeric columns.

Usage:
    python distribution_summary.py --input data.csv
    python distribution_summary.py --input data.csv --bins 20 --output summary.csv
"""

import argparse
import sys

import numpy as np
import pandas as pd


def ascii_histogram(series: pd.Series, bins: int = 10, width: int = 40) -> str:
    counts, edges = np.histogram(series.dropna(), bins=bins)
    max_count = counts.max() or 1
    lines = []
    for count, left, right in zip(counts, edges[:-1], edges[1:]):
        bar = "#" * int(count / max_count * width)
        lines.append(f"  [{left:>10.2f}, {right:>10.2f}) | {bar:<{width}} {count}")
    return "\n".join(lines)


def distribution_summary(df: pd.DataFrame, bins: int = 10) -> None:
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        print("No numeric columns found.")
        return

    desc = numeric.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
    desc["skew"] = numeric.skew().round(3)
    desc["kurt"] = numeric.kurt().round(3)
    print("=== Descriptive Statistics ===")
    print(desc.to_string())

    print("\n=== Histograms ===")
    for col in numeric.columns:
        print(f"\n{col}")
        print(ascii_histogram(numeric[col], bins=bins))


def main():
    parser = argparse.ArgumentParser(description="Descriptive stats and histograms for numeric columns.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--output", help="Optional CSV for stats table")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    distribution_summary(df, bins=args.bins)

    if args.output:
        df.select_dtypes(include="number").describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T.to_csv(args.output)
        print(f"\nStats saved to {args.output}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        rng = np.random.default_rng(3)
        demo = pd.DataFrame({
            "revenue": rng.lognormal(mean=4, sigma=0.8, size=200),
            "sessions": rng.poisson(15, 200),
            "age": rng.integers(18, 70, 200),
        })
        distribution_summary(demo)
    else:
        main()
