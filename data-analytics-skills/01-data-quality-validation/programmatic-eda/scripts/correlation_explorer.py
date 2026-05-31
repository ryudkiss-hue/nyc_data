"""
Compute pairwise correlations for numeric columns and flag strong pairs.

Usage:
    python correlation_explorer.py --input data.csv
    python correlation_explorer.py --input data.csv --threshold 0.7 --output corr.csv
"""

import argparse
import sys

import numpy as np
import pandas as pd


def find_strong_pairs(corr_matrix: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    pairs = []
    cols = corr_matrix.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr_matrix.iloc[i, j]
            if abs(val) >= threshold:
                pairs.append({"col_a": cols[i], "col_b": cols[j], "correlation": round(val, 4)})
    return pd.DataFrame(pairs).sort_values("correlation", key=abs, ascending=False)


def explore_correlations(df: pd.DataFrame, threshold: float = 0.8, method: str = "pearson") -> None:
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        print("Need at least 2 numeric columns for correlation analysis.")
        return

    corr = numeric.corr(method=method)
    print(f"=== Correlation Matrix ({method}) ===")
    print(corr.round(3).to_string())

    pairs = find_strong_pairs(corr, threshold=threshold)
    print(f"\n=== Strong Pairs (|r| ≥ {threshold}) ===")
    if pairs.empty:
        print("  None found.")
    else:
        print(pairs.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Explore pairwise correlations and flag strong pairs.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--threshold", type=float, default=0.8, help="Abs correlation threshold (default 0.8)")
    parser.add_argument("--method", choices=["pearson", "spearman", "kendall"], default="pearson")
    parser.add_argument("--output", help="Optional CSV output for correlation matrix")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    explore_correlations(df, threshold=args.threshold, method=args.method)

    if args.output:
        df.select_dtypes(include="number").corr(method=args.method).to_csv(args.output)
        print(f"\nMatrix saved to {args.output}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        rng = np.random.default_rng(4)
        base = rng.normal(0, 1, 200)
        demo = pd.DataFrame({
            "revenue": base * 100 + rng.normal(0, 5, 200),
            "gross_profit": base * 80 + rng.normal(0, 8, 200),  # high corr with revenue
            "sessions": rng.poisson(20, 200),
            "bounce_rate": rng.uniform(0.2, 0.9, 200),
        })
        explore_correlations(demo, threshold=0.7)
    else:
        main()
