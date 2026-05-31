"""
Compute a cohort retention matrix from the cohort table produced by cohort_builder.py.

Output: retention rates as cohort × period matrix (rows = cohort, columns = period number).

Usage:
    python retention_matrix.py --input cohort_table.csv --output retention.csv
    python retention_matrix.py --input cohort_table.csv --format pct
"""

import argparse
import sys

import pandas as pd


def compute_retention_matrix(df: pd.DataFrame, fmt: str = "pct") -> pd.DataFrame:
    # Cohort size = distinct users in period 0
    cohort_sizes = (
        df[df["period_number"] == 0]
        .groupby("cohort_period")["user_id"]
        .nunique()
        .rename("cohort_size")
    )

    # Retained users per cohort × period
    retained = (
        df.groupby(["cohort_period", "period_number"])["user_id"]
        .nunique()
        .reset_index(name="retained_users")
    )

    retained = retained.merge(cohort_sizes, on="cohort_period")
    retained["retention_rate"] = retained["retained_users"] / retained["cohort_size"]

    # Pivot to matrix
    if fmt == "pct":
        matrix = retained.pivot(index="cohort_period", columns="period_number", values="retention_rate")
        matrix = (matrix * 100).round(1)
    elif fmt == "count":
        matrix = retained.pivot(index="cohort_period", columns="period_number", values="retained_users")
    else:
        matrix = retained.pivot(index="cohort_period", columns="period_number", values="retention_rate")

    matrix.index = matrix.index.astype(str)
    matrix.columns = [f"Period {c}" for c in matrix.columns]

    # Add cohort size as first column
    cohort_sizes.index = cohort_sizes.index.astype(str)
    matrix.insert(0, "Cohort Size", cohort_sizes)

    return matrix


def main():
    parser = argparse.ArgumentParser(description="Compute cohort retention matrix.")
    parser.add_argument("--input", required=True, help="CSV from cohort_builder.py")
    parser.add_argument("--format", choices=["pct", "count", "rate"], default="pct",
                        help="Output format: pct (%), count (users), rate (0-1 float)")
    parser.add_argument("--output", help="Optional CSV output path")
    args = parser.parse_args()

    df = pd.read_csv(args.input, parse_dates=["cohort_period"])
    matrix = compute_retention_matrix(df, fmt=args.format)

    print("=== Retention Matrix ===")
    print(matrix.to_string())

    if args.output:
        matrix.to_csv(args.output)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(5)
        n_users = 300
        signup_dates = pd.date_range("2023-01-01", periods=6, freq="MS").repeat(50)
        records = []
        for i, (uid, signup) in enumerate(zip(range(n_users), signup_dates)):
            for mo in range(7):
                if rng.random() < max(0.05, 0.75 - mo * 0.1):
                    records.append({"user_id": uid, "cohort_period": signup, "period_number": mo})

        df = pd.DataFrame(records).drop_duplicates()
        matrix = compute_retention_matrix(df)
        print(matrix.to_string())
    else:
        main()
