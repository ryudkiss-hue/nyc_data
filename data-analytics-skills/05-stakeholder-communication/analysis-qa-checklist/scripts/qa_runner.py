"""
Automated pre-delivery QA checks for analysis output files.

Checks performed:
  - Row count > 0
  - No fully-null columns
  - Numeric columns: no infinity values, detect suspicious rounding (all zeros after decimal)
  - Date columns: no future dates beyond tomorrow
  - Duplicate rows detection
  - Column name hygiene (spaces, special characters)

Usage:
    python qa_runner.py --input results.csv
    python qa_runner.py --input results.csv --output qa_report.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

import pandas as pd


def run_qa(df: pd.DataFrame) -> list[dict]:
    checks = []

    def add(name, status, detail=""):
        checks.append({"check": name, "status": status, "detail": detail})

    # Row count
    if len(df) == 0:
        add("row_count", "FAIL", "No rows in dataset")
    else:
        add("row_count", "PASS", f"{len(df):,} rows")

    # Fully-null columns
    null_cols = [c for c in df.columns if df[c].isna().all()]
    if null_cols:
        add("fully_null_columns", "FAIL", f"Columns with 100% nulls: {null_cols}")
    else:
        add("fully_null_columns", "PASS")

    # Duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        pct = dup_count / len(df) * 100
        add("duplicate_rows", "WARN", f"{dup_count} duplicate rows ({pct:.1f}%)")
    else:
        add("duplicate_rows", "PASS")

    # Column name hygiene
    bad_names = [c for c in df.columns if " " in c or not c.replace("_", "").isalnum()]
    if bad_names:
        add("column_names", "WARN", f"Non-standard column names: {bad_names}")
    else:
        add("column_names", "PASS")

    # Numeric checks
    num_cols = df.select_dtypes(include="number").columns.tolist()
    for col in num_cols:
        inf_count = (~df[col].isna() & df[col].abs().eq(float("inf"))).sum()
        if inf_count > 0:
            add(f"infinity_{col}", "FAIL", f"{inf_count} infinity values in '{col}'")

        non_null = df[col].dropna()
        if len(non_null) > 10:
            all_integer = (non_null % 1 == 0).all()
            if not all_integer:
                pass  # mixed decimals are fine
            # Suspicious: non-integer column where >95% of values are round numbers
            round_pct = (non_null % 1 == 0).mean()
            if round_pct > 0.95 and round_pct < 1.0:
                add(f"suspicious_rounding_{col}", "WARN",
                    f"'{col}': {round_pct:.0%} of values are whole numbers — verify no truncation")

    # Date checks: no future dates > tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    for col in df.columns:
        parsed = pd.to_datetime(df[col], errors="coerce", utc=False)
        if parsed.notna().sum() > len(df) * 0.5:
            future = (parsed > tomorrow).sum()
            if future > 0:
                add(f"future_dates_{col}", "WARN",
                    f"'{col}': {future} values are in the future (>{tomorrow.date()})")

    return checks


def main():
    parser = argparse.ArgumentParser(description="Run automated QA checks on an analysis output file.")
    parser.add_argument("--input", required=True, help="CSV or Parquet file to check")
    parser.add_argument("--output", help="Optional path to write JSON report")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    checks = run_qa(df)

    fails = [c for c in checks if c["status"] == "FAIL"]
    warns = [c for c in checks if c["status"] == "WARN"]

    print(f"\nQA Results: {len(checks)} checks | {len(fails)} FAIL | {len(warns)} WARN")
    for c in checks:
        icon = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}.get(c["status"], "?")
        detail = f"  — {c['detail']}" if c["detail"] else ""
        print(f"  [{icon}] {c['check']}{detail}")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(checks, f, indent=2)
        print(f"\nReport written to {args.output}")

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import io
        demo_csv = """order_id,revenue,created_at,status
1,100.0,2024-01-01,active
2,200.0,2024-01-02,active
2,200.0,2024-01-02,active
3,,2024-01-03,active
4,-Inf,2024-01-04,active"""
        df = pd.read_csv(io.StringIO(demo_csv))
        checks = run_qa(df)
        fails = sum(1 for c in checks if c["status"] == "FAIL")
        warns = sum(1 for c in checks if c["status"] == "WARN")
        print(f"Demo QA: {len(checks)} checks | {fails} FAIL | {warns} WARN")
        for c in checks:
            if c["status"] != "PASS":
                print(f"  [{c['status']}] {c['check']}: {c['detail']}")
    else:
        main()
