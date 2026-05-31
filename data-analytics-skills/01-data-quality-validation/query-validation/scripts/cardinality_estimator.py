"""
Estimate result cardinality for SQL joins given table stats, and flag fan-out risk.

Provide table sizes and join keys; the script estimates the output row count and
compares it against a threshold to warn about potential Cartesian-product-like blowups.

Usage:
    python cardinality_estimator.py --tables '{"orders": 1000000, "users": 50000}' \
                                    --joins '[{"left": "orders", "right": "users", "key": "user_id", "left_unique": false, "right_unique": true}]'
"""

import argparse
import json
import sys


def estimate_join(left_rows: int, right_rows: int, left_unique: bool, right_unique: bool) -> dict:
    """
    Simple cardinality heuristic for a single join.
    - Many-to-one (left non-unique, right unique): output ≈ left rows
    - One-to-many (left unique, right non-unique): output ≈ right rows
    - Many-to-many: can fan-out; estimate = left * right / max(left, right) with a warning
    """
    if left_unique and right_unique:
        est = min(left_rows, right_rows)
        risk = "LOW"
    elif not left_unique and right_unique:
        est = left_rows
        risk = "LOW"
    elif left_unique and not right_unique:
        est = right_rows
        risk = "LOW"
    else:
        est = left_rows * right_rows // max(left_rows, right_rows)
        risk = "HIGH" if est > left_rows * 2 else "MEDIUM"

    return {
        "estimated_output_rows": est,
        "fan_out_risk": risk,
        "notes": "Many-to-many join — verify join key uniqueness" if risk == "HIGH" else "",
    }


def main():
    parser = argparse.ArgumentParser(description="Estimate join output cardinality and flag fan-out risk.")
    parser.add_argument("--tables", required=True,
                        help='JSON dict of table_name → row_count, e.g. \'{"orders": 1000000}\'')
    parser.add_argument("--joins", required=True,
                        help='JSON list of join specs: [{left, right, key, left_unique, right_unique}]')
    args = parser.parse_args()

    tables = json.loads(args.tables)
    joins = json.loads(args.joins)

    for j in joins:
        left = j["left"]
        right = j["right"]
        left_rows = tables.get(left, 0)
        right_rows = tables.get(right, 0)
        result = estimate_join(
            left_rows=left_rows,
            right_rows=right_rows,
            left_unique=j.get("left_unique", False),
            right_unique=j.get("right_unique", True),
        )
        print(f"\nJoin: {left} ⋈ {right} on {j.get('key', '?')}")
        print(f"  Left rows:           {left_rows:,}")
        print(f"  Right rows:          {right_rows:,}")
        print(f"  Estimated output:    {result['estimated_output_rows']:,}")
        print(f"  Fan-out risk:        {result['fan_out_risk']}")
        if result["notes"]:
            print(f"  Note: {result['notes']}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Demo: orders (1M rows) JOIN users (50K rows) on user_id")
        tables = {"orders": 1_000_000, "users": 50_000}
        result = estimate_join(left_rows=1_000_000, right_rows=50_000, left_unique=False, right_unique=True)
        print(f"  Estimated output:  {result['estimated_output_rows']:,}")
        print(f"  Fan-out risk:      {result['fan_out_risk']}")

        print("\nDemo: events (5M rows) JOIN sessions (3M rows) — both non-unique")
        result2 = estimate_join(left_rows=5_000_000, right_rows=3_000_000, left_unique=False, right_unique=False)
        print(f"  Estimated output:  {result2['estimated_output_rows']:,}")
        print(f"  Fan-out risk:      {result2['fan_out_risk']}")
        print(f"  Note: {result2['notes']}")
    else:
        main()
