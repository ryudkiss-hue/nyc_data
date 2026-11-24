"""SQL/SOQL to business logic explainer for NYC DOT SIM queries.

Parses a SQL or SOQL query and generates a structured plain-language explanation
covering data sources, filters, aggregations, joins, and output columns.
Flags potential issues (null propagation, fan-out, hardcoded dates).

Usage:
    python sql_explainer.py --sql "SELECT borough, count(*) AS total FROM violations WHERE status='OPEN' GROUP BY borough"

    python sql_explainer.py --file my_query.sql --audience executive --dataset violations

    python sql_explainer.py --file my_query.sql --format md --out explanation.md

    echo "SELECT ..." | python sql_explainer.py --stdin
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# NYC DOT SIM schema context for enriching explanations
COLUMN_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "inspection": {
        "objectid": "unique inspection record identifier",
        "borough": "NYC borough code (MN=Manhattan, BX=Bronx, BK=Brooklyn, QN=Queens, SI=Staten Island)",
        "status": "inspection outcome (PASS, FAIL, PENDING)",
        "inspection_date": "date the physical inspection was conducted",
        "created_date": "date the record was entered into the system (lags inspection_date by 0–45 days)",
        "unit_id": "SIM unit identifier — links to violations.unit_id and dismissals.unit_id",
        "defect_type": "classification of defect observed (CRACK, UNEVEN, OBSTRUCTION, TREE_DAMAGE, OTHER)",
        "material_type": "sidewalk surface material (CONCRETE, BRICK, ASPHALT, BLUESTONE, OTHER)",
        "the_geom": "WGS84 geographic point coordinates (~92% coverage)",
    },
    "violations": {
        "objectid": "unique violation record identifier",
        "borough": "borough where the violation was issued",
        "status": "violation status (OPEN, CLOSED, DISMISSED, IN PROGRESS)",
        "created_date": "date the violation was issued",
        "unit_id": "SIM unit identifier — foreign key to inspection.unit_id",
    },
    "ramp_progress": {
        "objectid": "unique ramp record identifier",
        "borough": "borough where the ramp is located",
        "status": "ramp status (COMPLETE, PENDING, IN PROGRESS, CANCELLED)",
        "the_geom": "ramp location (~88% coverage)",
    },
    "dismissals": {
        "objectid": "unique dismissal record identifier",
        "unit_id": "SIM unit — links to inspection and violations datasets",
    },
}

DATASET_NAMES: dict[str, str] = {
    "inspection": "Sidewalk Inspections (dntt-gqwq, ~398K rows)",
    "violations": "Sidewalk Violations (6kbp-uz6m, ~312K rows)",
    "ramp_progress": "Curb Ramp Progress (e7gc-ub6z, ~187K rows)",
    "dismissals": "Dismissed Violations (p4u2-3jgx, ~85K rows)",
    "ramp_complaints": "Ramp Complaints (jagj-gttd, ~6K rows)",
    "street_permits": "Street Permits (tqtj-sjs8, ~3.6M rows)",
    "tree_damage": "Tree Damage Reports (j6v2-6uxq, ~17K rows)",
}

POTENTIAL_ISSUES = [
    (
        r"\bIS\s+NULL\b",
        "null propagation",
        "Query filters on NULL values. Ensure null handling is intentional.",
    ),
    (
        r"\bLEFT\s+JOIN\b",
        "left join fan-out risk",
        "LEFT JOIN may produce more rows than expected if the right side has multiple matches.",
    ),
    (
        r"\bCROSS\s+JOIN\b",
        "cross join explosion",
        "CROSS JOIN produces all combinations of rows. Verify this is intentional.",
    ),
    (
        r"'\d{4}-\d{2}-\d{2}'",
        "hardcoded date",
        "Query contains a hardcoded date. Use a parameter or relative date if this runs regularly.",
    ),
    (
        r"\bDISTINCT\b",
        "distinct usage",
        "DISTINCT may mask duplicate rows from fan-out joins. Investigate if unexpectedly slow.",
    ),
    (
        r"/\s*\w+\b(?!\s*\*)",
        "division without null guard",
        "Division detected. Ensure denominator is never zero or NULL (use NULLIF).",
    ),
    (
        r"\bSELECT\s+\*\b",
        "select star",
        "SELECT * fetches all columns. Prefer explicit column selection for performance and clarity.",
    ),
]


def _describe_column(col: str, dataset: str | None) -> str:
    col_lower = col.lower().strip()
    if dataset and dataset in COLUMN_DESCRIPTIONS:
        desc = COLUMN_DESCRIPTIONS[dataset].get(col_lower)
        if desc:
            return f"{col}: {desc}"
    generic = {
        "borough": "NYC borough code",
        "status": "current record status",
        "created_date": "date record was created",
        "objectid": "unique record identifier",
        "unit_id": "SIM unit identifier",
        "the_geom": "geographic coordinates",
        "count(*)": "total row count",
        "count(objectid)": "count of non-null objectid values",
    }
    return f"{col}: {generic.get(col_lower, 'computed or output value')}"


def _extract_section(sql: str, keyword: str) -> str | None:
    pattern = rf"\b{keyword}\b\s+(.+?)(?=\b(?:FROM|WHERE|GROUP|HAVING|ORDER|LIMIT|$)\b)"
    m = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


def _extract_tables(sql: str) -> list[str]:
    tables = re.findall(r'\bFROM\s+([`"\w.]+)|JOIN\s+([`"\w.]+)', sql, re.IGNORECASE)
    flat = [t for pair in tables for t in pair if t]
    return [t.strip('`"') for t in flat]


def _extract_where(sql: str) -> str | None:
    m = re.search(
        r"\bWHERE\b\s+(.+?)(?=\bGROUP\b|\bHAVING\b|\bORDER\b|\bLIMIT\b|$)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else None


def _extract_group_by(sql: str) -> str | None:
    m = re.search(
        r"\bGROUP\s+BY\b\s+(.+?)(?=\bHAVING\b|\bORDER\b|\bLIMIT\b|$)",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else None


def _extract_select(sql: str) -> list[str]:
    m = re.search(r"\bSELECT\b\s+(.+?)\s+\bFROM\b", sql, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    raw = m.group(1).strip()
    return [c.strip() for c in raw.split(",")]


def _check_issues(sql: str) -> list[tuple[str, str]]:
    found = []
    for pattern, issue_name, message in POTENTIAL_ISSUES:
        if re.search(pattern, sql, re.IGNORECASE):
            found.append((issue_name, message))
    return found


def _translate_filter(clause: str) -> str:
    """Best-effort translation of WHERE clauses to plain English."""
    clause = clause.strip()
    translations = [
        (
            r"upper\s*\(\s*borough\s*\)\s*=\s*'(\w+)'",
            lambda m: f"borough is {m.group(1)} (case-insensitive match)",
        ),
        (r"borough\s*=\s*'(\w+)'", lambda m: f"borough equals '{m.group(1)}'"),
        (r"status\s*=\s*'(\w+)'", lambda m: f"status is '{m.group(1)}'"),
        (r"status\s+IN\s*\((.+?)\)", lambda m: f"status is one of: {m.group(1)}"),
        (r"(\w+_date)\s*>\s*'(.+?)'", lambda m: f"{m.group(1)} is after {m.group(2)}"),
        (r"(\w+_date)\s*>=\s*'(.+?)'", lambda m: f"{m.group(1)} is on or after {m.group(2)}"),
        (r"(\w+_date)\s*<\s*'(.+?)'", lambda m: f"{m.group(1)} is before {m.group(2)}"),
        (r"(\w+)\s+IS\s+NULL", lambda m: f"{m.group(1)} has no value (null)"),
        (r"(\w+)\s+IS\s+NOT\s+NULL", lambda m: f"{m.group(1)} has a value (not null)"),
    ]
    for pattern, fn in translations:
        m = re.search(pattern, clause, re.IGNORECASE)
        if m:
            return fn(m)
    return clause  # fall back to raw clause


def explain(
    sql: str,
    dataset: str | None = None,
    business_question: str | None = None,
    audience: str = "analyst",
) -> str:
    sql_clean = " ".join(sql.split())

    tables = _extract_tables(sql_clean)
    where_clause = _extract_where(sql_clean)
    group_by = _extract_group_by(sql_clean)
    select_cols = _extract_select(sql_clean)
    issues = _check_issues(sql_clean)

    primary_table = tables[0] if tables else (dataset or "unknown")
    extra_tables = tables[1:] if len(tables) > 1 else []

    lines = ["# SQL Business Logic Explanation", ""]

    if business_question:
        lines += [f"**Business question:** {business_question}", ""]

    lines += ["## What this query does", ""]
    lines.append(
        f"This query reads from the **{DATASET_NAMES.get(primary_table, primary_table)}** dataset"
        + (f" joined with {', '.join(extra_tables)}" if extra_tables else "")
        + "."
    )

    if where_clause:
        conditions = [
            c.strip() for c in re.split(r"\bAND\b|\bOR\b", where_clause, flags=re.IGNORECASE)
        ]
        lines += ["", "**Filters applied (business rules):**"]
        for cond in conditions:
            lines.append(f"- {_translate_filter(cond)}")

    if group_by:
        lines += [
            "",
            f"**Results are grouped by:** {group_by}",
            "Each output row represents one combination of these grouping values.",
        ]

    if select_cols:
        lines += ["", "## Output columns", ""]
        for col in select_cols:
            lines.append(f"- `{col}` — {_describe_column(col, primary_table)}")

    if group_by:
        agg_cols = [
            c for c in select_cols if re.search(r"\b(COUNT|SUM|AVG|MIN|MAX)\s*\(", c, re.IGNORECASE)
        ]
        if agg_cols:
            lines += ["", "## Aggregations", ""]
            for agg in agg_cols:
                lines.append(f"- `{agg}` — computed once per {group_by} grouping")

    if audience == "executive":
        lines += [
            "",
            "## Plain-language summary",
            "",
            f"This report shows {'borough-by-borough' if 'borough' in (group_by or '') else 'aggregate'} "
            f"data from the {DATASET_NAMES.get(primary_table, primary_table)} dataset"
            + (
                f" limited to records where {_translate_filter(where_clause)}"
                if where_clause
                else ""
            )
            + ".",
        ]

    if issues:
        lines += ["", "## Potential issues to review", ""]
        for name, msg in issues:
            lines.append(f"- **{name}:** {msg}")

    lines += [
        "",
        "## Validation questions",
        "",
        "- Does the row count match expectations? (Run `SELECT COUNT(*) ...` first)",
        "- Are there nulls in the grouping columns that should be excluded?",
        "- Does this query reflect the correct date range?",
        f"- Is `{primary_table}` fresh? (Check: `socrata dataset health --key {primary_table}`)",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="SQL/SOQL to business logic explainer")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--sql", help="SQL string to explain")
    src.add_argument("--file", help="Path to .sql file")
    src.add_argument("--stdin", action="store_true", help="Read SQL from stdin")
    parser.add_argument(
        "--dataset", help="Primary dataset key for schema context (e.g. violations)"
    )
    parser.add_argument("--question", help="Business question this query answers")
    parser.add_argument("--audience", choices=["analyst", "executive"], default="analyst")
    parser.add_argument("--format", choices=["md", "text"], default="md")
    parser.add_argument("--out", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if args.sql:
        sql = args.sql
    elif args.file:
        sql = Path(args.file).read_text()
    else:
        sql = sys.stdin.read()

    result = explain(
        sql.strip(), dataset=args.dataset, business_question=args.question, audience=args.audience
    )

    if args.out:
        Path(args.out).write_text(result)
        print(f"Written to: {args.out}")
    else:
        print(result)


if __name__ == "__main__":
    main()
