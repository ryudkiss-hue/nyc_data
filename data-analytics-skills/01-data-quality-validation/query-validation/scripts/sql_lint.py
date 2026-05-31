"""
Lint a SQL query for syntax errors and dialect-specific issues using sqlglot.

Usage:
    python sql_lint.py --input query.sql --dialect snowflake
    python sql_lint.py --sql "SELECT * FROM users" --dialect bigquery
"""

import argparse
import sys


def lint_sql(sql: str, dialect: str = "ansi") -> list[dict]:
    try:
        import sqlglot
        import sqlglot.errors
    except ImportError:
        return [{"severity": "ERROR", "message": "sqlglot not installed — run: pip install sqlglot"}]

    issues = []

    # Parse and collect syntax errors
    try:
        expressions = sqlglot.parse(sql, dialect=dialect, error_level=sqlglot.errors.ErrorLevel.WARN)
        for expr in expressions:
            if expr is None:
                issues.append({"severity": "ERROR", "message": "Query produced no parse tree — possible syntax error"})
    except sqlglot.errors.ParseError as e:
        for err in e.errors:
            issues.append({"severity": "ERROR", "message": str(err)})
        return issues

    sql_upper = sql.upper()

    # Style / best-practice checks
    if "SELECT *" in sql_upper and "SELECT * EXCEPT" not in sql_upper:
        issues.append({"severity": "WARN", "message": "SELECT * in use — enumerate columns explicitly for stability"})

    if "WHERE" not in sql_upper and "LIMIT" not in sql_upper:
        issues.append({"severity": "WARN", "message": "No WHERE or LIMIT clause — full table scan likely"})

    if sql_upper.count("SELECT") > 5:
        issues.append({"severity": "INFO", "message": f"Query has {sql_upper.count('SELECT')} SELECT statements — consider breaking into CTEs for readability"})

    if "DISTINCT" in sql_upper:
        issues.append({"severity": "INFO", "message": "DISTINCT in use — verify it's needed; may indicate an unintended join fan-out"})

    if not issues:
        issues.append({"severity": "OK", "message": "No issues found"})

    return issues


def main():
    parser = argparse.ArgumentParser(description="Lint SQL query for syntax and style issues.")
    parser.add_argument("--input", help="Path to .sql file")
    parser.add_argument("--sql", help="SQL string inline")
    parser.add_argument("--dialect", default="ansi",
                        choices=["ansi", "snowflake", "bigquery", "postgres", "redshift", "mysql"],
                        help="SQL dialect for parsing (default: ansi)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            sql = f.read()
    elif args.sql:
        sql = args.sql
    else:
        print("Provide --input or --sql")
        sys.exit(1)

    issues = lint_sql(sql, dialect=args.dialect)
    for issue in issues:
        print(f"[{issue['severity']}] {issue['message']}")

    has_errors = any(i["severity"] == "ERROR" for i in issues)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        demo_sql = """
        SELECT *
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE CAST(o.created_at AS DATE) = '2024-01-01'
        """
        print("Demo query:")
        print(demo_sql)
        print("\nLint results:")
        for issue in lint_sql(demo_sql, dialect="snowflake"):
            print(f"  [{issue['severity']}] {issue['message']}")
    else:
        main()
