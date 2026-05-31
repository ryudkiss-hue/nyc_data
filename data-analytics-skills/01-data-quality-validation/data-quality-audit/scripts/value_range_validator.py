"""
Validate column values against configurable business rules (min/max/allowed values).

Rules are passed as JSON:
  {
    "revenue":     {"min": 0},
    "age":         {"min": 0, "max": 120},
    "status":      {"allowed": ["active", "churned", "trial"]},
    "created_at":  {"min": "2020-01-01", "max": "today"}
  }

Usage:
    python value_range_validator.py --input data.csv --rules rules.json
    python value_range_validator.py --input data.csv --rules '{"revenue": {"min": 0}}'
"""

import argparse
import json
import sys
from datetime import date

import pandas as pd


def validate_column(series: pd.Series, rule: dict) -> dict:
    issues = []
    non_null = series.dropna()

    if "min" in rule:
        min_val = rule["min"]
        if min_val == "today":
            min_val = str(date.today())
        try:
            violations = (non_null.astype(str) < str(min_val)).sum() if series.dtype == "object" else (non_null < min_val).sum()
        except Exception:
            violations = 0
        if violations > 0:
            issues.append(f"{violations} values below min ({min_val})")

    if "max" in rule:
        max_val = rule["max"]
        if max_val == "today":
            max_val = str(date.today())
        try:
            violations = (non_null.astype(str) > str(max_val)).sum() if series.dtype == "object" else (non_null > max_val).sum()
        except Exception:
            violations = 0
        if violations > 0:
            issues.append(f"{violations} values above max ({max_val})")

    if "allowed" in rule:
        unexpected = ~non_null.isin(rule["allowed"])
        count = int(unexpected.sum())
        if count > 0:
            sample = non_null[unexpected].unique()[:5].tolist()
            issues.append(f"{count} unexpected values (sample: {sample})")

    pct = round(len(non_null[non_null.isin(rule.get("allowed", non_null.unique()))]) / max(len(series), 1) * 100, 1)
    return {
        "issues": issues,
        "status": "FAIL" if issues else "PASS",
    }


def validate_ranges(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    rows = []
    for col, rule in rules.items():
        if col not in df.columns:
            rows.append({"column": col, "status": "SKIP", "issues": "Column not found in dataset"})
            continue
        result = validate_column(df[col], rule)
        rows.append({
            "column": col,
            "rule": json.dumps(rule),
            "status": result["status"],
            "issues": "; ".join(result["issues"]) if result["issues"] else "None",
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Validate column values against business rules.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--rules", required=True, help="JSON string or path to rules JSON file")
    parser.add_argument("--output", help="Optional CSV output")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)

    try:
        rules = json.loads(args.rules)
    except json.JSONDecodeError:
        with open(args.rules) as f:
            rules = json.load(f)

    result = validate_ranges(df, rules)
    print(result.to_string(index=False))

    if args.output:
        result.to_csv(args.output, index=False)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(12)
        demo = pd.DataFrame({
            "revenue": list(rng.normal(100, 20, 95)) + [-50, -100, -200, 500, 1000],
            "age": list(rng.integers(18, 65, 98)) + [130, 150],
            "status": rng.choice(["active", "trial", "churned", "UNKNOWN", "deleted"], 100),
        })
        rules = {
            "revenue": {"min": 0},
            "age": {"min": 0, "max": 120},
            "status": {"allowed": ["active", "trial", "churned"]},
        }
        print(validate_ranges(demo, rules).to_string(index=False))
    else:
        main()
