"""
Schema Comparison Tool

Compare two schemas (source and target) to find direct column matches,
type mismatches, unmapped source columns, and target columns with no source.

Usage:
    python schema_compare.py --source source_schema.csv --target target_schema.csv
    python schema_compare.py --source source_schema.csv --target target_schema.csv \
        --output mapping.md
"""

import argparse
import csv
import sys
from io import StringIO


def load_schema(filepath: str) -> list[dict]:
    """
    Load a schema CSV with columns: column_name, data_type, nullable, description.
    Returns list of dicts.
    """
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip().lower(): v.strip() for k, v in row.items()})
    return rows


def compare_schemas(source: list[dict], target: list[dict]) -> dict:
    """
    Compare source and target schemas.

    Returns:
        direct_matches: target cols with same name in source
        type_mismatches: matched by name but different types
        unmapped_source: source cols not in target
        unmapped_target: target cols not in source
    """
    source_map = {row["column_name"]: row for row in source}
    target_map = {row["column_name"]: row for row in target}

    direct_matches = []
    type_mismatches = []
    unmapped_source = []
    unmapped_target = []

    for col_name, t_row in target_map.items():
        if col_name in source_map:
            s_row = source_map[col_name]
            if s_row.get("data_type", "").lower() == t_row.get("data_type", "").lower():
                direct_matches.append({"column": col_name, "type": t_row.get("data_type")})
            else:
                type_mismatches.append({
                    "column": col_name,
                    "source_type": s_row.get("data_type"),
                    "target_type": t_row.get("data_type"),
                })
        else:
            unmapped_target.append({"column": col_name, "type": t_row.get("data_type"),
                                     "description": t_row.get("description", "")})

    for col_name, s_row in source_map.items():
        if col_name not in target_map:
            unmapped_source.append({"column": col_name, "type": s_row.get("data_type"),
                                     "description": s_row.get("description", "")})

    return {
        "direct_matches": direct_matches,
        "type_mismatches": type_mismatches,
        "unmapped_source": unmapped_source,
        "unmapped_target": unmapped_target,
    }


def format_report(result: dict) -> str:
    out = StringIO()

    def section(title, rows, cols):
        out.write(f"\n## {title} ({len(rows)})\n\n")
        if not rows:
            out.write("None.\n")
            return
        header = " | ".join(cols)
        sep = " | ".join(["---"] * len(cols))
        out.write(f"| {header} |\n| {sep} |\n")
        for row in rows:
            values = " | ".join(str(row.get(c, "")) for c in cols)
            out.write(f"| {values} |\n")

    out.write("# Schema Comparison Report\n")
    section("Direct Matches (same name, same type)", result["direct_matches"], ["column", "type"])
    section("Type Mismatches (same name, different type)", result["type_mismatches"],
            ["column", "source_type", "target_type"])
    section("Unmapped Source Columns (in source, not in target)", result["unmapped_source"],
            ["column", "type", "description"])
    section("Target Columns With No Source (need derivation or default)", result["unmapped_target"],
            ["column", "type", "description"])

    out.write("\n## Summary\n\n")
    out.write(f"- Direct matches: {len(result['direct_matches'])}\n")
    out.write(f"- Type mismatches requiring a CAST: {len(result['type_mismatches'])}\n")
    out.write(f"- Source columns dropped or deferred: {len(result['unmapped_source'])}\n")
    out.write(f"- Target columns needing derivation: {len(result['unmapped_target'])}\n")

    return out.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Compare source and target schemas.")
    parser.add_argument("--source", required=True, help="Source schema CSV")
    parser.add_argument("--target", required=True, help="Target schema CSV")
    parser.add_argument("--output", default=None, help="Write report to file")
    args = parser.parse_args()

    source = load_schema(args.source)
    target = load_schema(args.target)
    result = compare_schemas(source, target)
    report = format_report(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    unmapped = len(result["unmapped_target"]) + len(result["type_mismatches"])
    sys.exit(1 if unmapped > 0 else 0)


if __name__ == "__main__":
    # Demo with in-memory schemas
    source_rows = [
        {"column_name": "order_id",    "data_type": "VARCHAR",  "nullable": "NO",  "description": "Order PK"},
        {"column_name": "customer_id", "data_type": "INTEGER",  "nullable": "NO",  "description": "FK to customers"},
        {"column_name": "amount_cents","data_type": "INTEGER",  "nullable": "NO",  "description": "Amount in cents"},
        {"column_name": "order_ts",    "data_type": "TIMESTAMP","nullable": "NO",  "description": "Order timestamp"},
        {"column_name": "legacy_flag", "data_type": "BOOLEAN",  "nullable": "YES", "description": "Deprecated field"},
    ]
    target_rows = [
        {"column_name": "order_id",    "data_type": "VARCHAR",  "nullable": "NO",  "description": "Order PK"},
        {"column_name": "customer_id", "data_type": "INTEGER",  "nullable": "NO",  "description": "FK to customers"},
        {"column_name": "amount_usd",  "data_type": "DECIMAL",  "nullable": "NO",  "description": "Amount in USD (derived)"},
        {"column_name": "order_ts",    "data_type": "TIMESTAMP","nullable": "NO",  "description": "Order timestamp"},
        {"column_name": "order_date",  "data_type": "DATE",     "nullable": "NO",  "description": "Date only (derived)"},
    ]
    result = compare_schemas(source_rows, target_rows)
    print(format_report(result))
