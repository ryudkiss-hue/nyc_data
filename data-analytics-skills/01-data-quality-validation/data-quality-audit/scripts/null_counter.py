"""
Count nulls per column and classify against configurable thresholds.
Produces a per-column report with pass/warn/fail status.

Usage:
    python null_counter.py --input data.csv
    python null_counter.py --input data.csv --thresholds '{"revenue": 0, "email": 10}'
"""

import argparse
import json
import sys

import pandas as pd


DEFAULT_WARN_PCT = 5.0
DEFAULT_FAIL_PCT = 20.0


def count_nulls(
    df: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
    default_warn: float = DEFAULT_WARN_PCT,
    default_fail: float = DEFAULT_FAIL_PCT,
) -> pd.DataFrame:
    thresholds = thresholds or {}
    rows = []
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = null_count / len(df) * 100 if len(df) > 0 else 0
        fail_thresh = thresholds.get(col, default_fail)
        warn_thresh = min(thresholds.get(col, default_warn), fail_thresh)

        if null_pct >= fail_thresh:
            status = "FAIL"
        elif null_pct >= warn_thresh:
            status = "WARN"
        else:
            status = "PASS"

        rows.append({
            "column": col,
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_pct": round(null_pct, 2),
            "warn_threshold": warn_thresh,
            "fail_threshold": fail_thresh,
            "status": status,
        })
    return pd.DataFrame(rows).sort_values("null_pct", ascending=False)


def main():
    parser = argparse.ArgumentParser(description="Audit null counts per column.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--thresholds", default="{}", help="JSON dict of column -> max acceptable null %")
    parser.add_argument("--warn-pct", type=float, default=DEFAULT_WARN_PCT)
    parser.add_argument("--fail-pct", type=float, default=DEFAULT_FAIL_PCT)
    parser.add_argument("--output", help="Optional CSV output path")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    thresholds = json.loads(args.thresholds)
    result = count_nulls(df, thresholds=thresholds, default_warn=args.warn_pct, default_fail=args.fail_pct)

    print(result.to_string(index=False))
    fails = result[result["status"] == "FAIL"]
    if not fails.empty:
        print(f"\n⚠ {len(fails)} FAIL(s):")
        for _, row in fails.iterrows():
            print(f"  {row['column']}: {row['null_pct']}% nulls (threshold {row['fail_threshold']}%)")

    if args.output:
        result.to_csv(args.output, index=False)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(10)
        demo = pd.DataFrame({
            "order_id": range(200),
            "customer_id": [None if rng.random() < 0.02 else i for i in range(200)],
            "revenue": [None if rng.random() < 0.07 else rng.normal(100, 20) for _ in range(200)],
            "product_code": [None if rng.random() < 0.30 else "SKU-001" for _ in range(200)],
        })
        thresholds = {"order_id": 0, "customer_id": 1}
        print(count_nulls(demo, thresholds=thresholds).to_string(index=False))
    else:
        main()
