#!/usr/bin/env python3
"""
null_profiler.py — Column-level null analysis for NYC DOT Socrata datasets.

Compares null rates against thresholds in references/quality_thresholds.md
and prints a ranked table of columns with violations.

Usage:
    python null_profiler.py --key inspection --rows 5000
    python null_profiler.py --key violations --rows 10000 --threshold-critical 5 --threshold-major 10
    python null_profiler.py --file data/cache/inspection.parquet
"""

import argparse
import sys

import pandas as pd

sys.path.insert(0, "src")

DATASET_KEYS = {
    "inspection": ("data.cityofnewyork.us", "dntt-gqwq"),
    "violations": ("data.cityofnewyork.us", "6kbp-uz6m"),
    "ramp_progress": ("data.cityofnewyork.us", "e7gc-ub6z"),
    "dismissals": ("data.cityofnewyork.us", "p4u2-3jgx"),
    "street_permits": ("data.cityofnewyork.us", "tqtj-sjs8"),
}

REQUIRED_FIELDS = {
    "inspection": {"objectid", "borough", "status", "inspection_date"},
    "violations": {"objectid", "borough", "status", "created_date"},
    "ramp_progress": {"objectid", "borough", "status"},
    "dismissals": {"objectid", "borough"},
    "street_permits": {"permit_si_no", "borough", "work_type"},
}


def load_dataset(args) -> tuple[pd.DataFrame, str]:
    if args.file:
        df = (
            pd.read_parquet(args.file) if args.file.endswith(".parquet") else pd.read_csv(args.file)
        )
        return df, "file"
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    domain, fourfour = DATASET_KEYS[args.key]
    client = SocrataClient(SocrataConfig())
    print(f"Fetching {args.rows} rows from {args.key}...", flush=True)
    return client.fetch_dataframe(domain, fourfour, max_rows=args.rows), args.key


def classify(null_pct: float, is_required: bool, crit_thresh: float, major_thresh: float) -> str:
    if is_required:
        if null_pct > crit_thresh:
            return "CRITICAL"
        if null_pct > 1.0:
            return "MAJOR"
        if null_pct > 0.0:
            return "MINOR"
        return "ok"
    else:
        if null_pct > major_thresh:
            return "MAJOR"
        if null_pct > 10.0:
            return "MINOR"
        return "ok"


def profile_nulls(
    df: pd.DataFrame, required: set[str], crit_thresh: float, major_thresh: float
) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = null_count / len(df) * 100
        is_req = col in required
        sev = classify(null_pct, is_req, crit_thresh, major_thresh)
        rows.append(
            {
                "column": col,
                "total_rows": len(df),
                "null_count": null_count,
                "null_pct": round(null_pct, 2),
                "required": "yes" if is_req else "no",
                "severity": sev,
            }
        )
    result = pd.DataFrame(rows)
    return result.sort_values(["severity", "null_pct"], ascending=[True, False])


def print_table(df: pd.DataFrame) -> None:
    SEVERITY_ORDER = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "ok": 3}
    df = df.copy()
    df["_sort"] = df["severity"].map(SEVERITY_ORDER)
    df = df.sort_values(["_sort", "null_pct"], ascending=[True, False]).drop(columns="_sort")

    header = f"{'Column':<35} {'Nulls':>8} {'Null %':>8} {'Required':<10} {'Severity':<10}"
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))
    for _, row in df.iterrows():
        flag = ""
        if row["severity"] == "CRITICAL":
            flag = " *** CRITICAL ***"
        elif row["severity"] == "MAJOR":
            flag = " ** MAJOR **"
        elif row["severity"] == "MINOR":
            flag = " * MINOR"
        print(
            f"{row['column']:<35} {row['null_count']:>8,} {row['null_pct']:>7.2f}% "
            f"{row['required']:<10} {row['severity']:<10}{flag}"
        )
    print("=" * len(header))

    critical = df[df["severity"] == "CRITICAL"]
    major = df[df["severity"] == "MAJOR"]
    minor = df[df["severity"] == "MINOR"]
    print(
        f"\nSummary: {len(critical)} critical  |  {len(major)} major  |  {len(minor)} minor  "
        f"|  {len(df) - len(critical) - len(major) - len(minor)} ok"
    )


def main():
    parser = argparse.ArgumentParser(description="Null profile for NYC DOT datasets")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", choices=list(DATASET_KEYS), help="Dataset registry key")
    group.add_argument("--file", help="Local Parquet or CSV file path")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument(
        "--threshold-critical",
        type=float,
        default=5.0,
        help="Null %% above which required field = CRITICAL (default 5)",
    )
    parser.add_argument(
        "--threshold-major",
        type=float,
        default=25.0,
        help="Null %% above which optional field = MAJOR (default 25)",
    )
    parser.add_argument("--csv-out", help="Save results to CSV at this path")
    args = parser.parse_args()

    df, source_key = load_dataset(args)
    required = REQUIRED_FIELDS.get(source_key, set())

    print(f"\nDataset: {source_key}  |  Rows: {len(df):,}  |  Columns: {len(df.columns)}")
    result = profile_nulls(df, required, args.threshold_critical, args.threshold_major)
    print_table(result)

    if args.csv_out:
        result.to_csv(args.csv_out, index=False)
        print(f"\nResults saved to {args.csv_out}")


if __name__ == "__main__":
    main()
