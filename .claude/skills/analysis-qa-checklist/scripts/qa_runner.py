"""
qa_runner.py — Automated pre-delivery QA checks for NYC DOT Socrata Toolkit analyses.

Flags numeric anomalies, null rates, out-of-range values, and structural issues
in CSV or JSON outputs before they reach stakeholders.

Usage:
    python qa_runner.py --file results.csv --question "Ramp completion by borough" --audience "DOT Commissioner"
    python qa_runner.py --file results.json --format json --threshold-null 0.05
"""

import argparse
import json
import sys
from pathlib import Path

BOROUGH_CODES = {"MN", "BX", "BK", "QN", "SI"}
VALID_RATE_COLUMNS = {"completion_rate", "closure_rate", "sla_compliance", "quality_score"}
MAX_QUALITY_SCORE = 100
MAX_RATE = 1.0  # proportions must be 0–1


def load_csv(path: Path) -> list[dict]:
    import csv

    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def check_nulls(rows: list[dict], threshold: float) -> list[str]:
    flags = []
    if not rows:
        return ["CRITICAL: file contains zero rows"]
    columns = rows[0].keys()
    for col in columns:
        null_count = sum(1 for r in rows if r.get(col) in (None, "", "NULL", "null"))
        rate = null_count / len(rows)
        if rate > threshold:
            flags.append(
                f"HIGH NULL RATE — '{col}': {rate:.1%} null ({null_count}/{len(rows)} rows)"
            )
    return flags


def check_rate_columns(rows: list[dict]) -> list[str]:
    flags = []
    columns = rows[0].keys() if rows else []
    for col in columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ("rate", "pct", "percent", "ratio", "score")):
            values = []
            for r in rows:
                v = r.get(col)
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass
            if not values:
                continue
            if max(values) > MAX_RATE and "score" not in col_lower:
                if max(values) <= 100:
                    flags.append(
                        f"RANGE CHECK — '{col}' max={max(values):.2f}: "
                        f"looks like percentage (0–100) but rate columns should be 0–1. "
                        f"Confirm units before delivery."
                    )
                else:
                    flags.append(
                        f"OUT OF RANGE — '{col}' max={max(values):.2f}: "
                        f"exceeds expected 0–1 range for a rate column."
                    )
            if min(values) < 0:
                flags.append(
                    f"NEGATIVE VALUE — '{col}' min={min(values):.4f}: rates cannot be negative."
                )
    return flags


def check_borough_coverage(rows: list[dict]) -> list[str]:
    flags = []
    columns = {k.lower() for k in (rows[0].keys() if rows else [])}
    borough_col = (
        next((c for c in rows[0].keys() if c.lower() in ("borough", "boro", "boro_code")), None)
        if rows
        else None
    )
    if borough_col:
        found = {r[borough_col].upper() for r in rows if r.get(borough_col)}
        missing = BOROUGH_CODES - found
        if missing:
            flags.append(
                f"MISSING BOROUGHS — '{borough_col}' is missing: {sorted(missing)}. "
                "Confirm these boroughs have no data vs. were filtered out."
            )
    return flags


def check_duplicate_keys(rows: list[dict], key_col: str | None) -> list[str]:
    flags = []
    if not key_col or not rows:
        return flags
    if key_col not in rows[0]:
        flags.append(f"KEY COLUMN '{key_col}' not found in data.")
        return flags
    values = [r[key_col] for r in rows]
    dupes = len(values) - len(set(values))
    if dupes > 0:
        flags.append(
            f"DUPLICATE KEYS — '{key_col}' has {dupes} duplicate value(s). "
            "Aggregation may have produced double-counting."
        )
    return flags


def check_zero_rows(rows: list[dict]) -> list[str]:
    if not rows:
        return [
            "CRITICAL: output has 0 rows — confirm this is expected (true empty) not a query error."
        ]
    return []


def run_qa(
    file_path: Path,
    fmt: str,
    question: str,
    audience: str,
    null_threshold: float,
    key_col: str | None,
) -> dict:
    if fmt == "csv":
        rows = load_csv(file_path)
    else:
        rows = load_json(file_path)

    flags = []
    flags += check_zero_rows(rows)
    flags += check_nulls(rows, null_threshold)
    flags += check_rate_columns(rows)
    flags += check_borough_coverage(rows)
    flags += check_duplicate_keys(rows, key_col)

    result = {
        "file": str(file_path),
        "rows_checked": len(rows),
        "question": question,
        "audience": audience,
        "flags": flags,
        "pass": len(flags) == 0,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Pre-delivery QA runner for NYC DOT analyses")
    parser.add_argument("--file", required=True, help="Path to CSV or JSON output file")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", dest="fmt")
    parser.add_argument("--question", default="(not specified)", help="Original analysis question")
    parser.add_argument("--audience", default="(not specified)", help="Intended audience")
    parser.add_argument(
        "--threshold-null",
        type=float,
        default=0.05,
        help="Null rate threshold above which a column is flagged (default 0.05 = 5%%)",
    )
    parser.add_argument(
        "--key-col", default=None, help="Primary key column to check for duplicates"
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    result = run_qa(path, args.fmt, args.question, args.audience, args.threshold_null, args.key_col)

    print(f"\n{'=' * 60}")
    print("NYC DOT Analysis QA Report")
    print(f"{'=' * 60}")
    print(f"File:      {result['file']}")
    print(f"Rows:      {result['rows_checked']}")
    print(f"Question:  {result['question']}")
    print(f"Audience:  {result['audience']}")
    print(f"{'=' * 60}")

    if result["pass"]:
        print("RESULT: PASS — no automated flags raised.")
    else:
        print(f"RESULT: {len(result['flags'])} FLAG(S) FOUND — review before delivery:\n")
        for i, flag in enumerate(result["flags"], 1):
            print(f"  [{i}] {flag}")

    print(f"{'=' * 60}\n")
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
