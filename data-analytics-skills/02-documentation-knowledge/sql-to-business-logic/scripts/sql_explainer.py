"""
SQL to Business Logic Explainer

Parses a SQL SELECT query and produces a structured plain-language explanation.
Handles: SELECT columns, FROM/JOIN sources, WHERE conditions, GROUP BY, ORDER BY.

Usage:
    python sql_explainer.py --input query.sql
    python sql_explainer.py --sql "SELECT customer_id, SUM(amount) FROM orders WHERE status='completed' GROUP BY 1"
    python sql_explainer.py --input query.sql --output explanation.md
"""

import argparse
import re
import sys


# ---- Simple pattern-based SQL parser ----------------------------------------

AGGREGATION_LABELS = {
    "COUNT(DISTINCT": "Count distinct",
    "COUNT(": "Count of",
    "SUM(": "Sum of",
    "AVG(": "Average",
    "MAX(": "Maximum",
    "MIN(": "Minimum",
    "DATE_TRUNC": "Truncate date to",
    "COALESCE": "First non-null of",
}

OPERATOR_LABELS = {
    ">=": "on or after",
    "<=": "on or before",
    "!=": "is not",
    "<>": "is not",
    "=": "equals",
    ">": "greater than",
    "<": "less than",
    " IN ": "is one of",
    " LIKE ": "matches pattern",
    " IS NOT NULL": "is not empty",
    " IS NULL": "is empty",
    " BETWEEN ": "is between",
}

JOIN_LABELS = {
    "INNER JOIN": "combines with (keeps only matching rows)",
    "LEFT JOIN": "combines with (keeps all left-side rows)",
    "RIGHT JOIN": "combines with (keeps all right-side rows)",
    "FULL OUTER JOIN": "combines with (keeps all rows from both sides)",
    "CROSS JOIN": "cross-combines every row with",
    "JOIN": "combines with (inner join — keeps only matching rows)",
}


def _strip_alias(token: str) -> str:
    """Remove AS alias from a token."""
    return re.split(r"\s+[Aa][Ss]\s+", token)[0].strip()


def translate_select_col(col: str) -> str:
    col = col.strip()
    alias = None
    if re.search(r"\s+[Aa][Ss]\s+", col):
        parts = re.split(r"\s+[Aa][Ss]\s+", col, maxsplit=1)
        alias = parts[1].strip()
        col = parts[0].strip()

    label = col
    for pattern, replacement in AGGREGATION_LABELS.items():
        if pattern in col.upper():
            inner = re.search(r"\((.+?)\)", col)
            inner_text = inner.group(1) if inner else col
            label = f"{replacement} {inner_text}"
            break

    return f"{label} (as {alias})" if alias else label


def translate_where_condition(cond: str) -> str:
    cond = cond.strip()
    for op, label in OPERATOR_LABELS.items():
        if op.upper() in cond.upper():
            idx = cond.upper().find(op.upper())
            left = cond[:idx].strip()
            right = cond[idx + len(op):].strip().strip("'\"")
            return f"{left} {label} {right}".strip()
    return cond


def explain_sql(sql: str) -> str:
    sql_upper = sql.upper()
    lines = []

    # --- SELECT columns ---
    select_match = re.search(r"SELECT\s+(.+?)\s+FROM\s+", sql, re.IGNORECASE | re.DOTALL)
    if select_match:
        cols_raw = select_match.group(1)
        # Split on commas not inside parentheses
        cols = re.split(r",(?![^()]*\))", cols_raw)
        lines.append("### What is being calculated (SELECT)")
        for col in cols:
            lines.append(f"- {translate_select_col(col)}")

    # --- FROM / JOIN ---
    from_match = re.search(r"FROM\s+(\S+)", sql, re.IGNORECASE)
    if from_match:
        lines.append("\n### Data source (FROM)")
        lines.append(f"- Start with: {from_match.group(1)}")

    for join_keyword, join_label in JOIN_LABELS.items():
        for match in re.finditer(rf"{re.escape(join_keyword)}\s+(\S+)\s+ON\s+(.+?)(?=WHERE|JOIN|GROUP|ORDER|HAVING|$)",
                                  sql, re.IGNORECASE | re.DOTALL):
            joined_table = match.group(1)
            join_cond = match.group(2).strip()
            lines.append(f"- {join_label}: {joined_table} (on {join_cond})")

    # --- WHERE ---
    where_match = re.search(r"WHERE\s+(.+?)(?=GROUP BY|ORDER BY|HAVING|LIMIT|$)", sql, re.IGNORECASE | re.DOTALL)
    if where_match:
        lines.append("\n### Filters applied (WHERE)")
        raw = where_match.group(1).strip()
        conditions = re.split(r"\s+AND\s+", raw, flags=re.IGNORECASE)
        for cond in conditions:
            lines.append(f"- {translate_where_condition(cond)}")

    # --- GROUP BY ---
    group_match = re.search(r"GROUP BY\s+(.+?)(?=ORDER BY|HAVING|LIMIT|$)", sql, re.IGNORECASE | re.DOTALL)
    if group_match:
        lines.append("\n### Grouping (GROUP BY)")
        groups = [g.strip() for g in group_match.group(1).split(",")]
        lines.append(f"- Calculate separately for each: {', '.join(groups)}")

    # --- ORDER BY ---
    order_match = re.search(r"ORDER BY\s+(.+?)(?=LIMIT|$)", sql, re.IGNORECASE | re.DOTALL)
    if order_match:
        lines.append("\n### Sorting (ORDER BY)")
        lines.append(f"- Sort by: {order_match.group(1).strip()}")

    lines.append("\n### Validation questions")
    lines.append("- Are these the correct filter conditions for the intended population?")
    lines.append("- Does the GROUP BY grain match what a single row should represent?")
    lines.append("- Are NULL values handled explicitly in aggregations?")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Explain a SQL query in plain language.")
    parser.add_argument("--input", help="Path to .sql file")
    parser.add_argument("--sql", help="Inline SQL string")
    parser.add_argument("--output", help="Output .md file")
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            sql = f.read()
    elif args.sql:
        sql = args.sql
    else:
        parser.error("Provide --input or --sql")

    explanation = explain_sql(sql)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"# SQL Explanation\n\n```sql\n{sql}\n```\n\n{explanation}\n")
        print(f"Explanation written to {args.output}")
    else:
        print(explanation)


if __name__ == "__main__":
    demo_sql = """
    SELECT
        DATE_TRUNC('month', order_date) AS month,
        COUNT(DISTINCT customer_id) AS unique_customers,
        SUM(total_amount) AS revenue
    FROM orders
    WHERE status = 'completed'
      AND order_date >= '2024-01-01'
    GROUP BY 1
    ORDER BY 1 DESC
    """
    print("SQL:", demo_sql.strip())
    print()
    print(explain_sql(demo_sql))
