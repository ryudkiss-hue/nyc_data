"""
Check referential integrity: verify that foreign key values in a child table
exist in the corresponding parent table.

Usage:
    python referential_integrity.py --child orders.csv --parent customers.csv \
           --child-key customer_id --parent-key id
"""

import argparse
import sys

import pandas as pd


def check_referential_integrity(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    child_key: str,
    parent_key: str,
) -> dict:
    child_vals = child_df[child_key].dropna()
    parent_vals = set(parent_df[parent_key].dropna())

    orphans = child_vals[~child_vals.isin(parent_vals)]
    orphan_count = len(orphans)
    total = len(child_vals)
    orphan_pct = round(orphan_count / total * 100, 2) if total > 0 else 0

    return {
        "child_key": child_key,
        "parent_key": parent_key,
        "total_child_rows": total,
        "orphan_count": orphan_count,
        "orphan_pct": orphan_pct,
        "orphan_values_sample": orphans.unique()[:10].tolist(),
        "status": "FAIL" if orphan_count > 0 else "PASS",
    }


def load(path: str) -> pd.DataFrame:
    return pd.read_csv(path) if path.endswith(".csv") else pd.read_parquet(path)


def main():
    parser = argparse.ArgumentParser(description="Check referential integrity between two tables.")
    parser.add_argument("--child", required=True, help="Path to child table (has the foreign key)")
    parser.add_argument("--parent", required=True, help="Path to parent table (has the primary key)")
    parser.add_argument("--child-key", required=True, help="Foreign key column in child table")
    parser.add_argument("--parent-key", required=True, help="Primary key column in parent table")
    args = parser.parse_args()

    child_df = load(args.child)
    parent_df = load(args.parent)
    result = check_referential_integrity(child_df, parent_df, args.child_key, args.parent_key)

    print(f"Referential integrity check: {result['child_key']} → {result['parent_key']}")
    print(f"  Total child rows:  {result['total_child_rows']:,}")
    print(f"  Orphan rows:       {result['orphan_count']:,} ({result['orphan_pct']}%)")
    print(f"  Status:            {result['status']}")
    if result["orphan_values_sample"]:
        print(f"  Sample orphan values: {result['orphan_values_sample']}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        parent = pd.DataFrame({"id": range(100)})
        child = pd.DataFrame({
            "order_id": range(150),
            "customer_id": list(range(80)) + [200, 201, 202, 203, 204] * 14,  # orphans
        })
        result = check_referential_integrity(child, parent, "customer_id", "id")
        print(f"Status: {result['status']} — {result['orphan_count']} orphans ({result['orphan_pct']}%)")
        print(f"Sample orphans: {result['orphan_values_sample'][:5]}")
    else:
        main()
