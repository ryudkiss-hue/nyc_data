"""
Print a structural overview of a tabular dataset: shape, dtypes, memory, and sample rows.

Usage:
    python data_overview.py --input data.csv
    python data_overview.py --input data.parquet --sample 10
"""

import argparse
import sys

import pandas as pd


def overview(df: pd.DataFrame, sample_n: int = 5) -> None:
    print(f"Shape:   {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"Memory:  {df.memory_usage(deep=True).sum() / 1_048_576:.2f} MB\n")

    print("Column types:")
    type_counts = df.dtypes.value_counts()
    for dtype, count in type_counts.items():
        print(f"  {str(dtype):<15} {count}")

    print("\nPer-column info:")
    info = pd.DataFrame({
        "dtype": df.dtypes,
        "non_null": df.notna().sum(),
        "null_pct": (df.isna().mean() * 100).round(2),
        "unique": df.nunique(),
        "sample": [df[c].dropna().iloc[0] if df[c].notna().any() else None for c in df.columns],
    })
    print(info.to_string())

    print(f"\nSample ({sample_n} rows):")
    print(df.sample(min(sample_n, len(df)), random_state=42).to_string(index=False))


def load(path: str) -> pd.DataFrame:
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    elif path.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    else:
        return pd.read_csv(path)


def main():
    parser = argparse.ArgumentParser(description="Print dataset structural overview.")
    parser.add_argument("--input", required=True, help="Path to CSV, Parquet, or Excel file")
    parser.add_argument("--sample", type=int, default=5, help="Number of sample rows to show")
    args = parser.parse_args()

    df = load(args.input)
    overview(df, sample_n=args.sample)


if __name__ == "__main__":
    # Demo: run against a synthetic dataset when no args supplied
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(0)
        demo = pd.DataFrame({
            "user_id": range(200),
            "revenue": rng.normal(50, 15, 200),
            "country": rng.choice(["US", "UK", "DE", None], 200),
            "signup_date": pd.date_range("2023-01-01", periods=200, freq="D"),
        })
        demo.loc[::20, "revenue"] = None  # inject nulls
        overview(demo)
    else:
        main()
