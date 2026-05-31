"""
Find full-row and key-level duplicates in a dataset.

Usage:
    python duplicate_finder.py --input data.csv --key order_id
    python duplicate_finder.py --input data.csv --key customer_id,product_id --show-examples
"""

import argparse
import sys

import pandas as pd


def find_duplicates(df: pd.DataFrame, key_cols: list[str] | None = None) -> dict:
    n = len(df)

    # Full-row duplicates
    full_row_dupes = df.duplicated()
    full_row_count = int(full_row_dupes.sum())

    results = {
        "total_rows": n,
        "full_row_duplicates": full_row_count,
        "full_row_duplicate_pct": round(full_row_count / n * 100, 2) if n > 0 else 0,
        "full_row_status": "FAIL" if full_row_count > 0 else "PASS",
        "key_results": [],
    }

    # Key-level duplicates
    if key_cols:
        for key in key_cols if isinstance(key_cols[0], list) else [key_cols]:
            key_label = ", ".join(key) if isinstance(key, list) else key
            key_list = key if isinstance(key, list) else [key]
            valid_keys = [k for k in key_list if k in df.columns]
            if not valid_keys:
                continue
            key_dupes = df.duplicated(subset=valid_keys, keep=False)
            key_dupe_count = int(key_dupes.sum())
            results["key_results"].append({
                "key": key_label,
                "key_duplicate_rows": key_dupe_count,
                "key_duplicate_pct": round(key_dupe_count / n * 100, 2) if n > 0 else 0,
                "duplicate_entities": int(df[key_dupes][valid_keys].drop_duplicates().shape[0]),
                "status": "FAIL" if key_dupe_count > 0 else "PASS",
            })

    return results


def main():
    parser = argparse.ArgumentParser(description="Find full-row and key-level duplicates.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--key", help="Comma-separated column names for key duplicate check")
    parser.add_argument("--show-examples", action="store_true", help="Print sample duplicate rows")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    key_cols = [k.strip() for k in args.key.split(",")] if args.key else None

    results = find_duplicates(df, key_cols=key_cols)

    print(f"Total rows: {results['total_rows']:,}")
    print(f"Full-row duplicates: {results['full_row_duplicates']:,} ({results['full_row_duplicate_pct']}%) [{results['full_row_status']}]")

    for kr in results["key_results"]:
        print(f"Key [{kr['key']}] duplicates: {kr['key_duplicate_rows']:,} rows ({kr['duplicate_entities']:,} entities) [{kr['status']}]")

    if args.show_examples and key_cols:
        dupe_mask = df.duplicated(subset=key_cols, keep=False)
        if dupe_mask.any():
            print("\nSample duplicate rows:")
            print(df[dupe_mask].sort_values(key_cols).head(10).to_string())


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(11)
        base_ids = list(range(180)) + [5, 10, 15, 20, 30]  # intentional dupes
        demo = pd.DataFrame({
            "order_id": base_ids,
            "customer_id": rng.integers(1, 50, 185),
            "amount": rng.normal(100, 20, 185),
        })
        results = find_duplicates(demo, key_cols=["order_id"])
        print(f"Full-row dupes: {results['full_row_duplicates']} [{results['full_row_status']}]")
        for kr in results["key_results"]:
            print(f"Key dupes: {kr['key_duplicate_rows']} rows ({kr['duplicate_entities']} entities) [{kr['status']}]")
    else:
        main()
