#!/usr/bin/env python3
"""
sql_lint.py — Syntax check and anti-pattern detection for NYC DOT SOQL / SQL queries.

Uses sqlglot to parse and validate SQL. For Socrata SOQL, transpiles to standard SQL
first so sqlglot can parse it. Checks against known anti-patterns for DuckDB and Socrata.

Usage:
    python sql_lint.py --query "SELECT borough, COUNT(*) FROM violations GROUP BY borough"
    python sql_lint.py --file query.sql --engine duckdb
    python sql_lint.py --query "SELECT * FROM violations" --engine socrata
    echo "SELECT * FROM v" | python sql_lint.py --stdin --engine duckdb
"""

import argparse
import sys

try:
    import sqlglot
    import sqlglot.errors

    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False


# Anti-patterns: (pattern_name, description, severity, check_fn)
# check_fn receives the lowercased SQL string, returns True if pattern is found
ANTI_PATTERNS = [
    (
        "SELECT_STAR",
        "SELECT * fetches all columns — wastes bandwidth on wide Socrata datasets.",
        "major",
        lambda sql: "select *" in sql and "select * exclude" not in sql,
    ),
    (
        "NO_LIMIT_LARGE_TABLE",
        "No LIMIT / $limit on a query against a large dataset (violations, inspection, complaints_311).",
        "major",
        lambda sql: (
            "limit" not in sql
            and "$limit" not in sql
            and any(
                t in sql
                for t in ["violations", "inspection", "complaints_311", "street_construction"]
            )
        ),
    ),
    (
        "OR_IN_WHERE",
        "OR conditions in WHERE can prevent index use; consider IN (...) or UNION ALL.",
        "minor",
        lambda sql: " or " in sql,
    ),
    (
        "NOT_IN_SUBQUERY",
        "NOT IN with a subquery returns no rows if subquery contains NULLs. Use NOT EXISTS.",
        "major",
        lambda sql: "not in (select" in sql.replace("\n", " "),
    ),
    (
        "IMPLICIT_CAST_DATE",
        "Date comparison without explicit cast may silently fail on Socrata string dates.",
        "major",
        lambda sql: (
            any(op in sql for op in ["> '20", "< '20", ">= '20", "<= '20"])
            and "::date" not in sql
            and "date_trunc" not in sql
        ),
    ),
    (
        "CROSS_JOIN",
        "Explicit or implicit CROSS JOIN detected — verify row multiplication is intended.",
        "critical",
        lambda sql: "cross join" in sql or (", " in sql.split("from")[-1].split("where")[0]),
    ),
    (
        "MISSING_BOROUGH_UPPER",
        "Borough comparison without upper() may miss mixed-case values from Socrata.",
        "minor",
        lambda sql: "borough =" in sql and "upper(" not in sql,
    ),
    (
        "SOQL_RELATIVE_DATE",
        "Relative date expressions are not supported by Socrata SOQL; use ISO 8601 timestamps.",
        "critical",
        lambda sql: any(
            r in sql for r in ["now()", "current_date", "today()", "interval", "getdate()"]
        ),
    ),
    (
        "COUNT_DISTINCT_WITHOUT_KEY",
        "COUNT(DISTINCT ...) on a non-key column may be slow on large datasets; verify intent.",
        "minor",
        lambda sql: "count(distinct" in sql and "objectid" not in sql,
    ),
]


def parse_sql(sql: str, engine: str) -> list[str]:
    if not HAS_SQLGLOT:
        return ["sqlglot not installed — syntax checking skipped. Run: pip install sqlglot"]
    errors = []
    dialect = {"socrata": "duckdb", "duckdb": "duckdb", "postgres": "postgres"}.get(
        engine, "duckdb"
    )
    try:
        sqlglot.parse(sql, dialect=dialect, error_level=sqlglot.errors.ErrorLevel.RAISE)
    except sqlglot.errors.SqlglotError as e:
        errors.append(f"SYNTAX ERROR: {e}")
    return errors


def check_anti_patterns(sql: str) -> list[dict]:
    findings = []
    sql_lower = sql.lower()
    for name, desc, severity, check_fn in ANTI_PATTERNS:
        try:
            if check_fn(sql_lower):
                findings.append({"pattern": name, "description": desc, "severity": severity})
        except Exception:
            pass
    return findings


def render_results(syntax_errors: list[str], findings: list[dict], sql: str) -> None:
    print("\n" + "=" * 60)
    print("SQL LINT REPORT")
    print("=" * 60)
    print(f"Query ({len(sql)} chars):")
    print(f"  {sql[:200]}{'...' if len(sql) > 200 else ''}")
    print()

    if syntax_errors:
        print("SYNTAX ERRORS:")
        for e in syntax_errors:
            print(f"  [CRITICAL] {e}")
    else:
        print("  Syntax: OK")

    print()
    if findings:
        print("ANTI-PATTERN FINDINGS:")
        for f in sorted(
            findings, key=lambda x: {"critical": 0, "major": 1, "minor": 2}[x["severity"]]
        ):
            sev = f["severity"].upper()
            print(f"  [{sev}] {f['pattern']}")
            print(f"         {f['description']}")
    else:
        print("  Anti-patterns: none detected")

    print()
    critical = [f for f in findings if f["severity"] == "critical"] + syntax_errors
    major = [f for f in findings if f["severity"] == "major"]
    minor = [f for f in findings if f["severity"] == "minor"]
    verdict = "PASS" if not critical and not major else ("FAIL" if critical else "WARN")
    print(
        f"Overall: {verdict}  |  {len(critical)} critical  {len(major)} major  {len(minor)} minor"
    )
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="SQL lint for NYC DOT queries")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--query", help="SQL string to lint")
    source.add_argument("--file", help="Path to .sql file")
    source.add_argument("--stdin", action="store_true", help="Read SQL from stdin")
    parser.add_argument(
        "--engine",
        default="duckdb",
        choices=["duckdb", "socrata", "postgres"],
        help="Target engine (affects dialect checks)",
    )
    args = parser.parse_args()

    if args.query:
        sql = args.query
    elif args.file:
        with open(args.file) as f:
            sql = f.read()
    else:
        sql = sys.stdin.read()

    syntax_errors = parse_sql(sql, args.engine)
    findings = check_anti_patterns(sql)
    render_results(syntax_errors, findings, sql)

    critical_count = len([f for f in findings if f["severity"] == "critical"]) + len(syntax_errors)
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == "__main__":
    main()
