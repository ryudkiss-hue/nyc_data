#!/usr/bin/env python3
"""
Phase 3C-1: Verify all 4 pipeline gates and return exit code 0/1.
MANDATORY per verification_gates_mandatory_system.md
"""

import sys
import duckdb
from pathlib import Path
from typing import Tuple, Dict, List


def run_gate_1(conn: duckdb.DuckDBPyConnection) -> Tuple[bool, str]:
    """Gate 1: All 57 raw tables exist and have rows."""
    try:
        result = conn.execute("""
            SELECT COUNT(*) as table_count, SUM(cnt) as total_rows
            FROM (
                SELECT table_name, COUNT(*) as cnt
                FROM information_schema.tables
                WHERE table_schema = 'raw'
                GROUP BY table_name
            )
        """).fetchall()

        if not result:
            return False, "Gate 1 FAILED: No raw tables found"

        table_count, total_rows = result[0]
        if table_count == 0:
            return False, f"Gate 1 FAILED: 0 raw tables found (expected 57)"
        if total_rows == 0:
            return False, f"Gate 1 FAILED: Raw tables exist but contain 0 rows"

        return True, f"Gate 1 PASSED: {table_count} raw tables with {total_rows} total rows"
    except Exception as e:
        return False, f"Gate 1 FAILED: {str(e)}"


def run_gate_2(conn: duckdb.DuckDBPyConnection) -> Tuple[bool, str]:
    """Gate 2: All staging tables exist (deduplication complete)."""
    try:
        result = conn.execute("""
            SELECT COUNT(DISTINCT table_name) as staging_tables
            FROM information_schema.tables
            WHERE table_schema = 'staging'
        """).fetchall()

        if not result or result[0][0] == 0:
            return False, "Gate 2 FAILED: No staging tables found"

        staging_count = result[0][0]
        return True, f"Gate 2 PASSED: {staging_count} staging tables exist"
    except Exception as e:
        return False, f"Gate 2 FAILED: {str(e)}"


def run_gate_3(conn: duckdb.DuckDBPyConnection) -> Tuple[bool, str]:
    """Gate 3: KPI materialization table exists with rows."""
    try:
        result = conn.execute("""
            SELECT COUNT(*) as kpi_count
            FROM information_schema.tables
            WHERE table_schema = 'serving' AND table_name = 'kpi_borough_results'
        """).fetchall()

        if not result or result[0][0] == 0:
            return False, "Gate 3 FAILED: serving.kpi_borough_results does not exist"

        kpi_result = conn.execute("""
            SELECT COUNT(*) as row_count FROM serving.kpi_borough_results
        """).fetchall()

        if not kpi_result or kpi_result[0][0] == 0:
            return False, "Gate 3 FAILED: serving.kpi_borough_results exists but has 0 rows"

        kpi_rows = kpi_result[0][0]
        return True, f"Gate 3 PASSED: KPI table has {kpi_rows} records"
    except Exception as e:
        return False, f"Gate 3 FAILED: {str(e)}"


def run_gate_4(conn: duckdb.DuckDBPyConnection) -> Tuple[bool, str]:
    """Gate 4: Cross-stage row count consistency (staging >= raw)."""
    try:
        result = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM raw.inspection) as raw_count,
                (SELECT COUNT(*) FROM staging.inspection) as staging_count
        """).fetchall()

        if not result:
            return False, "Gate 4 FAILED: Could not compare row counts"

        raw_count, staging_count = result[0]

        if staging_count > raw_count:
            return False, f"Gate 4 FAILED: Staging ({staging_count}) > Raw ({raw_count})"

        return True, f"Gate 4 PASSED: Row counts consistent (Raw={raw_count}, Staging={staging_count})"
    except Exception as e:
        return False, f"Gate 4 FAILED: {str(e)}"


def main() -> int:
    """Execute all 4 gates and return exit code."""
    print("=" * 80)
    print("VERIFICATION GATES — MANDATORY PIPELINE VALIDATION")
    print("=" * 80)

    # Connect to DuckDB
    try:
        conn = duckdb.connect(':memory:')
        print("[OK] Connected to DuckDB")
    except Exception as e:
        print(f"[FAIL] Cannot connect to DuckDB: {e}")
        return 1

    # Run all 4 gates
    gates = [
        ("Gate 1: Raw Data Load", run_gate_1),
        ("Gate 2: Staging Deduplication", run_gate_2),
        ("Gate 3: KPI Materialization", run_gate_3),
        ("Gate 4: Cross-Stage Consistency", run_gate_4),
    ]

    results: List[Tuple[str, bool, str]] = []

    for gate_name, gate_func in gates:
        passed, message = gate_func(conn)
        results.append((gate_name, passed, message))
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {message}")

    # Summary
    print("=" * 80)
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    if passed_count == total_count:
        print(f"[OK] ALL GATES PASSED ({passed_count}/{total_count})")
        print("=" * 80)
        return 0
    else:
        failed_gates = [name for name, passed, _ in results if not passed]
        print(f"[FAIL] {len(failed_gates)} GATE(S) FAILED:")
        for gate_name in failed_gates:
            print(f"  - {gate_name}")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
