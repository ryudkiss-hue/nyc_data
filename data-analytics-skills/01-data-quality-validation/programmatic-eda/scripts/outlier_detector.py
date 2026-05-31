"""
Detect outliers in numeric columns using IQR and z-score methods.

Usage:
    python outlier_detector.py --input data.csv
    python outlier_detector.py --input data.csv --method iqr --output outliers.csv
"""

import argparse
import sys

import numpy as np
import pandas as pd


def detect_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < q1 - k * iqr) | (series > q3 + k * iqr)


def detect_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    z = (series - series.mean()) / series.std(ddof=1)
    return z.abs() > threshold


def detect_outliers(df: pd.DataFrame, method: str = "both", k: float = 1.5, z_thresh: float = 3.0) -> pd.DataFrame:
    numeric = df.select_dtypes(include="number").columns
    rows = []
    for col in numeric:
        s = df[col].dropna()
        iqr_mask = detect_iqr(s, k) if method in ("iqr", "both") else pd.Series(False, index=s.index)
        z_mask = detect_zscore(s, z_thresh) if method in ("zscore", "both") else pd.Series(False, index=s.index)
        combined = iqr_mask | z_mask
        rows.append({
            "column": col,
            "outlier_count": int(combined.sum()),
            "outlier_pct": round(combined.mean() * 100, 2),
            "min": s.min(),
            "max": s.max(),
            "mean": round(s.mean(), 4),
            "iqr_outliers": int(iqr_mask.sum()),
            "zscore_outliers": int(z_mask.sum()),
        })
    return pd.DataFrame(rows).sort_values("outlier_count", ascending=False)


def main():
    parser = argparse.ArgumentParser(description="Detect outliers via IQR and/or z-score.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--method", choices=["iqr", "zscore", "both"], default="both")
    parser.add_argument("--iqr-k", type=float, default=1.5, help="IQR multiplier (default 1.5)")
    parser.add_argument("--z-thresh", type=float, default=3.0, help="Z-score threshold (default 3)")
    parser.add_argument("--output", help="Optional CSV output path")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    result = detect_outliers(df, method=args.method, k=args.iqr_k, z_thresh=args.z_thresh)
    print(result.to_string(index=False))
    if args.output:
        result.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        rng = np.random.default_rng(2)
        demo = pd.DataFrame({
            "revenue": np.concatenate([rng.normal(100, 10, 95), [500, 600, 700, -200, 1000]]),
            "sessions": rng.poisson(20, 100),
            "age": np.concatenate([rng.integers(18, 65, 98), [120, 150]]),
        })
        print(detect_outliers(demo).to_string(index=False))
    else:
        main()
