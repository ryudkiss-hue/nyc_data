"""
Profile null / missing values across all columns and flag those exceeding thresholds.

Usage:
    python null_profiler.py --input data.csv
    python null_profiler.py --input data.csv --warn-pct 5 --fail-pct 30
"""

import argparse
import sys

import pandas as pd


def profile_nulls(df: pd.DataFrame, warn_pct: float = 5.0, fail_pct: float = 30.0) -> pd.DataFrame:
    result = pd.DataFrame({
        "null_count": df.isna().sum(),
        "null_pct": (df.isna().mean() * 100).round(2),
    })
    result["status"] = "OK"
    result.loc[result["null_pct"] >= warn_pct, "status"] = "WARN"
    result.loc[result["null_pct"] >= fail_pct, "status"] = "FAIL"
    return result.sort_values("null_pct", ascending=False)


def main():
    parser = argparse.ArgumentParser(description="Profile nulls and flag threshold breaches.")
    parser.add_argument("--input", required=True, help="Path to CSV, Parquet, or Excel file")
    parser.add_argument("--warn-pct", type=float, default=5.0, help="% null to trigger WARN (default 5)")
    parser.add_argument("--fail-pct", type=float, default=30.0, help="% null to trigger FAIL (default 30)")
    parser.add_argument("--output", help="Optional CSV output path")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    result = profile_nulls(df, warn_pct=args.warn_pct, fail_pct=args.fail_pct)
    print(result.to_string())

    fails = result[result["status"] == "FAIL"]
    if not fails.empty:
        print(f"\n{len(fails)} column(s) exceed the FAIL threshold ({args.fail_pct}%):")
        print(fails.index.tolist())

    if args.output:
        result.to_csv(args.output)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(1)
        demo = pd.DataFrame({
            "id": range(100),
            "email": [None if rng.random() < 0.03 else f"u{i}@x.com" for i in range(100)],
            "revenue": [None if rng.random() < 0.08 else rng.normal(50, 10) for _ in range(100)],
            "segment": [None if rng.random() < 0.45 else "A" for _ in range(100)],
        })
        print(profile_nulls(demo).to_string())
    else:
        main()
