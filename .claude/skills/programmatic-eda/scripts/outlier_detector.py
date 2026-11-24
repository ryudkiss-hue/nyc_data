#!/usr/bin/env python3
"""
outlier_detector.py — IQR + z-score outlier detection on NYC DOT datasets.

Runs on all numeric columns. Outputs flagged row indices and summary stats.

Usage:
    python outlier_detector.py --key inspection --rows 10000
    python outlier_detector.py --key violations --method zscore --z-threshold 3.5
    python outlier_detector.py --file data/cache/inspection.parquet --output outliers.csv
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

DATASET_KEYS = {
    "inspection": ("data.cityofnewyork.us", "dntt-gqwq"),
    "violations": ("data.cityofnewyork.us", "6kbp-uz6m"),
    "ramp_progress": ("data.cityofnewyork.us", "e7gc-ub6z"),
    "dismissals": ("data.cityofnewyork.us", "p4u2-3jgx"),
    "street_permits": ("data.cityofnewyork.us", "tqtj-sjs8"),
}

# Columns to skip (IDs, flags, binary) — extend as needed
SKIP_COLUMNS = {
    "objectid",
    "unique_key",
    "permit_si_no",
    "x_coord",
    "y_coord",
    "census_tract",
    "bin",
    "bbl",
    "nta",
}


def load_dataset(args) -> pd.DataFrame:
    if args.file:
        return (
            pd.read_parquet(args.file) if args.file.endswith(".parquet") else pd.read_csv(args.file)
        )
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    domain, fourfour = DATASET_KEYS[args.key]
    client = SocrataClient(SocrataConfig())
    print(f"Fetching {args.rows} rows from {args.key}...", flush=True)
    return client.fetch_dataframe(domain, fourfour, max_rows=args.rows)


def detect_iqr(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (series < lower) | (series > upper)


def detect_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    mean = series.mean()
    std = series.std()
    if std == 0:
        return pd.Series(False, index=series.index)
    z = (series - mean).abs() / std
    return z > threshold


def run_detection(df: pd.DataFrame, method: str, iqr_mult: float, z_thresh: float) -> pd.DataFrame:
    numeric_cols = [
        c
        for c in df.select_dtypes(include=[np.number]).columns
        if c.lower() not in SKIP_COLUMNS and df[c].notna().sum() >= 10
    ]

    summary_rows = []
    for col in numeric_cols:
        series = df[col].dropna()
        if method == "iqr":
            flags = detect_iqr(series, iqr_mult)
        elif method == "zscore":
            flags = detect_zscore(series, z_thresh)
        else:  # both
            flags = detect_iqr(series, iqr_mult) | detect_zscore(series, z_thresh)

        count = int(flags.sum())
        pct = count / len(series) * 100
        summary_rows.append(
            {
                "column": col,
                "n_non_null": len(series),
                "outlier_count": count,
                "outlier_pct": round(pct, 2),
                "min": round(float(series.min()), 4),
                "p25": round(float(series.quantile(0.25)), 4),
                "median": round(float(series.median()), 4),
                "p75": round(float(series.quantile(0.75)), 4),
                "max": round(float(series.max()), 4),
                "mean": round(float(series.mean()), 4),
                "std": round(float(series.std()), 4),
                "decision": "INVESTIGATE" if pct > 5 else ("REVIEW" if pct > 1 else "ok"),
            }
        )

    return pd.DataFrame(summary_rows).sort_values("outlier_pct", ascending=False)


def print_results(result: pd.DataFrame) -> None:
    print(
        f"\n{'Column':<30} {'Outliers':>10} {'Outlier%':>9} {'Median':>12} {'Max':>12} {'Decision':<12}"
    )
    print("-" * 90)
    for _, row in result.iterrows():
        print(
            f"{row['column']:<30} {row['outlier_count']:>10,} {row['outlier_pct']:>8.2f}% "
            f"{row['median']:>12.2f} {row['max']:>12.2f} {row['decision']:<12}"
        )

    investigate = result[result["decision"] == "INVESTIGATE"]
    review = result[result["decision"] == "REVIEW"]
    print(
        f"\nSummary: {len(investigate)} columns to INVESTIGATE  |  {len(review)} to REVIEW  "
        f"|  {len(result) - len(investigate) - len(review)} ok"
    )


def main():
    parser = argparse.ArgumentParser(description="Outlier detection for NYC DOT datasets")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", choices=list(DATASET_KEYS))
    group.add_argument("--file", help="Local Parquet or CSV path")
    parser.add_argument("--rows", type=int, default=10000)
    parser.add_argument("--method", choices=["iqr", "zscore", "both"], default="both")
    parser.add_argument("--iqr-multiplier", type=float, default=1.5)
    parser.add_argument("--z-threshold", type=float, default=3.0)
    parser.add_argument("--output", help="Save summary CSV to this path")
    args = parser.parse_args()

    df = load_dataset(args)
    print(f"Rows: {len(df):,}  |  Columns: {len(df.columns)}  |  Method: {args.method}")

    result = run_detection(df, args.method, args.iqr_multiplier, args.z_threshold)
    print_results(result)

    if args.output:
        result.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
