#!/usr/bin/env python3
"""
qa_runner.py — Automated pre-delivery quality checks for NYC DOT SIM analyses.

Checks a pandas DataFrame (loaded from CSV, Parquet, or DuckDB) against the
team's must-fix review standards. Prints a structured report and exits non-zero
if any must-fix issues are found.

Usage:
    python qa_runner.py --file analysis_output.csv --borough-col borough --rate-col completion_rate --count-col n
    python qa_runner.py --file violations_monthly.csv --borough-col borough --count-col n_violations
    python qa_runner.py --file output.parquet --borough-col borough --count-col n --min-n 30

Exit codes:
    0 — all checks passed
    1 — one or more must-fix issues found
    2 — file could not be loaded or arguments are invalid
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BOROUGH_CODES = {"MN", "BX", "BK", "QN", "SI"}
BOROUGH_FULL_TO_CODE = {
    "MANHATTAN": "MN",
    "BRONX": "BX",
    "BROOKLYN": "BK",
    "QUEENS": "QN",
    "STATEN ISLAND": "SI",
}
EXPECTED_BOROUGH_COUNT = 5


def load_file(path: str):
    try:
        import pandas as pd
    except ImportError:
        print("ERROR: pandas is required. Run: pip install pandas", file=sys.stderr)
        sys.exit(2)

    p = Path(path)
    if not p.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(2)

    if p.suffix == ".csv":
        return pd.read_csv(path)
    elif p.suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    elif p.suffix == ".xlsx":
        return pd.read_excel(path)
    else:
        print(
            f"ERROR: unsupported file type: {p.suffix}. Use .csv, .parquet, or .xlsx",
            file=sys.stderr,
        )
        sys.exit(2)


def check_borough_column(df, borough_col: str, findings: list[dict]) -> None:
    if borough_col not in df.columns:
        findings.append(
            {
                "tier": "must-fix",
                "check": "borough_column_exists",
                "detail": f"Column '{borough_col}' not found. Available: {list(df.columns)}",
            }
        )
        return

    values = df[borough_col].dropna().astype(str).str.strip().str.upper().unique().tolist()

    unknown = [v for v in values if v not in BOROUGH_CODES and v not in BOROUGH_FULL_TO_CODE]
    if unknown:
        findings.append(
            {
                "tier": "must-fix",
                "check": "borough_normalization",
                "detail": f"Unknown borough values detected: {unknown}. Normalize with upper(trim(borough)) and a CASE statement.",
            }
        )

    mixed = any(v in BOROUGH_FULL_TO_CODE for v in values) and any(
        v in BOROUGH_CODES for v in values
    )
    if mixed:
        findings.append(
            {
                "tier": "must-fix",
                "check": "borough_encoding_mixed",
                "detail": "Mix of full names and codes in borough column. Standardize to MN/BX/BK/QN/SI.",
            }
        )

    found_boroughs = {v for v in values if v in BOROUGH_CODES or v in BOROUGH_FULL_TO_CODE}
    if len(found_boroughs) < EXPECTED_BOROUGH_COUNT:
        missing = BOROUGH_CODES - {BOROUGH_FULL_TO_CODE.get(v, v) for v in found_boroughs}
        findings.append(
            {
                "tier": "should-fix",
                "check": "missing_boroughs",
                "detail": f"Boroughs missing from output: {sorted(missing)}. Confirm exclusion is intentional.",
            }
        )


def check_count_column(
    df, count_col: str, borough_col: str, min_n: int, findings: list[dict]
) -> None:
    if count_col not in df.columns:
        findings.append(
            {
                "tier": "must-fix",
                "check": "count_column_missing",
                "detail": f"Count column '{count_col}' not found. Every output table must include n=.",
            }
        )
        return

    small_n_rows = df[df[count_col] < min_n]
    if len(small_n_rows) > 0:
        if borough_col in df.columns:
            boroughs = small_n_rows[borough_col].tolist()
            detail = f"Rows with n < {min_n}: {boroughs}. Flag as 'insufficient sample' rather than suppress."
        else:
            detail = f"{len(small_n_rows)} rows have n < {min_n}. Flag as 'insufficient sample' rather than suppress."
        findings.append(
            {
                "tier": "must-fix",
                "check": "small_n_unflagged",
                "detail": detail,
            }
        )

    zero_n = df[df[count_col] == 0]
    if len(zero_n) > 0:
        findings.append(
            {
                "tier": "must-fix",
                "check": "zero_n_rows",
                "detail": f"{len(zero_n)} rows have n=0. Distinguish 'no matching rows' from 'zero events found'.",
            }
        )


def check_rate_column(df, rate_col: str, findings: list[dict]) -> None:
    if rate_col not in df.columns:
        return  # rate column is optional

    col = df[rate_col].dropna()

    # Detect if rates are in [0,1] instead of [0,100]
    if col.max() <= 1.0 and col.min() >= 0.0:
        findings.append(
            {
                "tier": "should-fix",
                "check": "rate_as_decimal",
                "detail": f"Column '{rate_col}' appears to be in [0,1] range. Team standard is percentage (0–100). Multiply by 100.",
            }
        )

    # Detect mixed precision
    decimals = col.apply(lambda x: len(str(x).split(".")[-1]) if "." in str(x) else 0)
    if decimals.max() > 2:
        findings.append(
            {
                "tier": "should-fix",
                "check": "rate_precision",
                "detail": f"Column '{rate_col}' has values with more than 2 decimal places. Round to 1 decimal.",
            }
        )


def print_report(findings: list[dict]) -> int:
    must_fix = [f for f in findings if f["tier"] == "must-fix"]
    should_fix = [f for f in findings if f["tier"] == "should-fix"]

    print("\n=== QA Runner Report ===\n")

    if not findings:
        print("All checks passed. No issues found.")
        return 0

    if must_fix:
        print(f"MUST-FIX ({len(must_fix)} issue(s)) — blocks delivery:\n")
        for f in must_fix:
            print(f"  [{f['check']}]")
            print(f"  {f['detail']}\n")

    if should_fix:
        print(f"SHOULD-FIX ({len(should_fix)} issue(s)) — quality issues:\n")
        for f in should_fix:
            print(f"  [{f['check']}]")
            print(f"  {f['detail']}\n")

    if must_fix:
        print(f"Result: FAIL — {len(must_fix)} must-fix issue(s) found.")
        return 1
    else:
        print(f"Result: PASS with warnings — {len(should_fix)} should-fix issue(s).")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run automated QA checks on an NYC DOT analysis output file."
    )
    parser.add_argument(
        "--file", required=True, help="Path to analysis output (.csv, .parquet, .xlsx)"
    )
    parser.add_argument(
        "--borough-col", default="borough", help="Name of the borough column (default: borough)"
    )
    parser.add_argument(
        "--count-col", default="n", help="Name of the count/sample-size column (default: n)"
    )
    parser.add_argument(
        "--rate-col", default="", help="Name of the rate column, if present (optional)"
    )
    parser.add_argument(
        "--min-n", type=int, default=30, help="Minimum acceptable sample size per row (default: 30)"
    )
    args = parser.parse_args()

    df = load_file(args.file)
    findings: list[dict] = []

    check_borough_column(df, args.borough_col, findings)
    check_count_column(df, args.count_col, args.borough_col, args.min_n, findings)
    if args.rate_col:
        check_rate_column(df, args.rate_col, findings)

    exit_code = print_report(findings)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
