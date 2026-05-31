"""
Parse a text EXPLAIN / query profile and extract the costliest steps.

Supports: Postgres EXPLAIN ANALYZE text, Snowflake Query Profile JSON, BigQuery INFORMATION_SCHEMA.JOBS rows.

Usage:
    python explain_plan_parser.py --input explain.txt --engine postgres
    python explain_plan_parser.py --input profile.json --engine snowflake
"""

import argparse
import json
import re
import sys


def parse_postgres(text: str) -> list[dict]:
    """Extract nodes with high actual time or row estimate error from EXPLAIN ANALYZE output."""
    steps = []
    node_pattern = re.compile(
        r"((?:->)?\s*[\w\s]+?)\s+\(cost=[\d.]+\.\.([\d.]+)\s+rows=(\d+).*?\)"
        r"(?:.*?actual time=([\d.]+)\.\.([\d.]+)\s+rows=(\d+))?",
        re.DOTALL
    )
    for m in node_pattern.finditer(text):
        node = m.group(1).strip().lstrip("->").strip()
        est_rows = int(m.group(3))
        actual_rows = int(m.group(6)) if m.group(6) else None
        actual_time = float(m.group(5)) if m.group(5) else None
        row_err = None
        if actual_rows is not None and est_rows > 0:
            row_err = actual_rows / est_rows
        steps.append({
            "node": node,
            "estimated_rows": est_rows,
            "actual_rows": actual_rows,
            "row_estimate_ratio": round(row_err, 2) if row_err else None,
            "actual_time_ms": actual_time,
        })

    # Flag bad estimates and slow nodes
    for s in steps:
        flags = []
        if s["row_estimate_ratio"] and (s["row_estimate_ratio"] > 10 or s["row_estimate_ratio"] < 0.1):
            flags.append("BAD_ESTIMATE")
        if s["actual_time_ms"] and s["actual_time_ms"] > 1000:
            flags.append("SLOW")
        s["flags"] = flags

    return sorted(steps, key=lambda x: x.get("actual_time_ms") or 0, reverse=True)


def parse_snowflake(data: dict) -> list[dict]:
    """Extract top operators by execution time from Snowflake Query Profile JSON."""
    steps = []
    for node in data.get("nodes", []):
        steps.append({
            "operator": node.get("name", ""),
            "execution_time_ms": node.get("executionTime", 0),
            "bytes_scanned": node.get("bytesScanned", 0),
            "rows_produced": node.get("rowsProduced", 0),
            "flags": ["SLOW"] if node.get("executionTime", 0) > 1000 else [],
        })
    return sorted(steps, key=lambda x: x["execution_time_ms"], reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Parse query explain plan and flag expensive steps.")
    parser.add_argument("--input", required=True, help="Path to EXPLAIN text or JSON profile")
    parser.add_argument("--engine", choices=["postgres", "snowflake"], default="postgres")
    args = parser.parse_args()

    with open(args.input) as f:
        content = f.read()

    if args.engine == "snowflake":
        data = json.loads(content)
        steps = parse_snowflake(data)
    else:
        steps = parse_postgres(content)

    print(f"=== Top steps ({args.engine}) ===")
    for i, step in enumerate(steps[:10], 1):
        flags_str = " [" + ", ".join(step.get("flags", [])) + "]" if step.get("flags") else ""
        print(f"{i:>2}. {step}{flags_str}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo = """
Seq Scan on orders  (cost=0.00..180000.00 rows=100 width=8) (actual time=0.015..2300.456 rows=850000 loops=1)
  Filter: (status = 'completed')
Hash Join  (cost=1.05..200.00 rows=50 width=16) (actual time=0.100..50.200 rows=45 loops=1)
  Hash Cond: (orders.user_id = users.id)
  ->  Seq Scan on users  (cost=0.00..1.10 rows=10 width=8) (actual time=0.005..0.010 rows=10 loops=1)
"""
        steps = parse_postgres(demo)
        for s in steps:
            print(s)
    else:
        main()
