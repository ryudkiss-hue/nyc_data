"""SQL Integration for DOT Sidewalk Toolkit.

Cross-database SQL generation and data management:
- Generate CREATE TABLE, INSERT, and UPSERT statements from DataFrames
- Build analytical queries (aggregations, window functions, CTEs)
- Schema management (migrations, drift detection SQL)
- Export DataFrames as SQL files for import into any RDBMS
- Parameterized query builder for safe ad-hoc queries

Supports PostgreSQL, SQLite, and generic SQL dialects.

Example::

    from socrata_toolkit.integrations.sql import (
        SQLQueryBuilder,
        dataframe_to_create_table,
        dataframe_to_insert_sql,
        generate_analytics_view,
    )

    create_sql = dataframe_to_create_table(df, "sidewalk_inspections")
    insert_sql = dataframe_to_insert_sql(df, "sidewalk_inspections")
    builder = SQLQueryBuilder("sidewalk_inspections")
    query = builder.select("borough", "COUNT(*) as cnt").group_by("borough").build()
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import pandas as pd


# ---------------------------------------------------------------------------
# Type Mapping
# ---------------------------------------------------------------------------

_PD_TO_SQL: Dict[str, Dict[str, str]] = {
    "postgres": {
        "int64": "BIGINT", "int32": "INTEGER", "float64": "DOUBLE PRECISION",
        "float32": "REAL", "bool": "BOOLEAN", "datetime64[ns]": "TIMESTAMPTZ",
        "datetime64[ns, UTC]": "TIMESTAMPTZ", "object": "TEXT",
    },
    "sqlite": {
        "int64": "INTEGER", "int32": "INTEGER", "float64": "REAL",
        "float32": "REAL", "bool": "INTEGER", "datetime64[ns]": "TEXT",
        "object": "TEXT",
    },
    "generic": {
        "int64": "BIGINT", "int32": "INTEGER", "float64": "DOUBLE PRECISION",
        "float32": "FLOAT", "bool": "BOOLEAN", "datetime64[ns]": "TIMESTAMP",
        "object": "VARCHAR(255)",
    },
}


def _sql_type(dtype: str, dialect: str = "postgres") -> str:
    mapping = _PD_TO_SQL.get(dialect, _PD_TO_SQL["generic"])
    return mapping.get(str(dtype), "TEXT")


# ---------------------------------------------------------------------------
# DDL Generation
# ---------------------------------------------------------------------------

def dataframe_to_create_table(
    df: pd.DataFrame,
    table_name: str,
    dialect: str = "postgres",
    primary_key: Optional[str] = None,
    if_not_exists: bool = True,
) -> str:
    """Generate a CREATE TABLE statement from a DataFrame's schema.

    Args:
        df: Source DataFrame.
        table_name: Target table name.
        dialect: 'postgres', 'sqlite', or 'generic'.
        primary_key: Column to designate as PRIMARY KEY.
        if_not_exists: Add IF NOT EXISTS clause.
    """
    exists = "IF NOT EXISTS " if if_not_exists else ""
    cols = []
    for col in df.columns:
        sql_type = _sql_type(df[col].dtype, dialect)
        pk = " PRIMARY KEY" if col == primary_key else ""
        safe_col = col.replace('"', '')
        cols.append(f'    "{safe_col}" {sql_type}{pk}')
    col_defs = ",\n".join(cols)
    return f'CREATE TABLE {exists}"{table_name}" (\n{col_defs}\n);'


def dataframe_to_insert_sql(
    df: pd.DataFrame,
    table_name: str,
    batch_size: int = 100,
) -> str:
    """Generate INSERT statements from a DataFrame's data.

    Returns multi-row INSERT statements in batches.
    """
    if df.empty:
        return f"-- No data to insert into {table_name}"

    cols = [c.replace('"', '') for c in df.columns]
    col_list = ", ".join(f'"{c}"' for c in cols)
    statements = []

    for start in range(0, len(df), batch_size):
        batch = df.iloc[start:start + batch_size]
        value_rows = []
        for _, row in batch.iterrows():
            vals = []
            for c in df.columns:
                v = row[c]
                if pd.isna(v):
                    vals.append("NULL")
                elif isinstance(v, str):
                    vals.append("'" + v.replace("'", "''") + "'")
                elif isinstance(v, bool):
                    vals.append("TRUE" if v else "FALSE")
                else:
                    vals.append(str(v))
            value_rows.append("(" + ", ".join(vals) + ")")
        values = ",\n    ".join(value_rows)
        statements.append(f'INSERT INTO "{table_name}" ({col_list}) VALUES\n    {values};')

    return "\n\n".join(statements)


def dataframe_to_upsert_sql(
    df: pd.DataFrame,
    table_name: str,
    conflict_column: str,
    dialect: str = "postgres",
) -> str:
    """Generate UPSERT (INSERT ... ON CONFLICT) SQL from a DataFrame.

    Currently supports PostgreSQL dialect. SQLite uses INSERT OR REPLACE.
    """
    if df.empty:
        return f"-- No data to upsert into {table_name}"

    cols = [c.replace('"', '') for c in df.columns]
    col_list = ", ".join(f'"{c}"' for c in cols)
    update_cols = [c for c in cols if c != conflict_column]
    updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)

    if dialect == "sqlite":
        return dataframe_to_insert_sql(df, table_name).replace("INSERT INTO", "INSERT OR REPLACE INTO")

    # PostgreSQL
    placeholders = ", ".join(["%s"] * len(cols))
    if updates:
        return f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})\nON CONFLICT ("{conflict_column}") DO UPDATE SET {updates};'
    return f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})\nON CONFLICT ("{conflict_column}") DO NOTHING;'


# ---------------------------------------------------------------------------
# Analytics SQL Generation
# ---------------------------------------------------------------------------

def generate_analytics_view(
    table_name: str,
    view_name: str,
    group_cols: List[str],
    agg_expressions: Dict[str, str],
) -> str:
    """Generate a CREATE VIEW for common analytics aggregations.

    Args:
        table_name: Source table.
        view_name: Name for the view.
        group_cols: Columns to GROUP BY.
        agg_expressions: Mapping of alias -> SQL expression
            (e.g., {"total_violations": "SUM(violations)"}).
    """
    selects = [f'"{c}"' for c in group_cols]
    selects.extend(f'{expr} AS "{alias}"' for alias, expr in agg_expressions.items())
    select_clause = ",\n    ".join(selects)
    group_clause = ", ".join(f'"{c}"' for c in group_cols)
    return f'CREATE OR REPLACE VIEW "{view_name}" AS\nSELECT\n    {select_clause}\nFROM "{table_name}"\nGROUP BY {group_clause};'


def generate_window_query(
    table_name: str,
    partition_col: str,
    order_col: str,
    value_col: str,
    window_functions: Optional[List[str]] = None,
) -> str:
    """Generate a query with window functions for trend analysis.

    Default window functions: ROW_NUMBER, running SUM, and LAG.
    """
    fns = window_functions or [
        f'ROW_NUMBER() OVER (PARTITION BY "{partition_col}" ORDER BY "{order_col}") AS row_num',
        f'SUM("{value_col}") OVER (PARTITION BY "{partition_col}" ORDER BY "{order_col}" ROWS UNBOUNDED PRECEDING) AS running_total',
        f'LAG("{value_col}", 1) OVER (PARTITION BY "{partition_col}" ORDER BY "{order_col}") AS prev_value',
        f'"{value_col}" - LAG("{value_col}", 1) OVER (PARTITION BY "{partition_col}" ORDER BY "{order_col}") AS delta',
    ]
    fn_clause = ",\n    ".join(fns)
    return f'SELECT *,\n    {fn_clause}\nFROM "{table_name}"\nORDER BY "{partition_col}", "{order_col}";'


def generate_cte_summary(
    table_name: str,
    borough_col: str = "borough",
    status_col: str = "status",
    value_col: str = "violations",
) -> str:
    """Generate a CTE-based summary query for DOT sidewalk data."""
    return f"""WITH borough_stats AS (
    SELECT
        "{borough_col}",
        COUNT(*) AS total_records,
        SUM("{value_col}") AS total_violations,
        AVG("{value_col}") AS avg_violations,
        COUNT(*) FILTER (WHERE "{status_col}" = 'Pending Repair') AS pending_count
    FROM "{table_name}"
    GROUP BY "{borough_col}"
),
ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY total_violations DESC) AS violation_rank,
        ROUND(pending_count::numeric / NULLIF(total_records, 0) * 100, 2) AS pending_pct
    FROM borough_stats
)
SELECT * FROM ranked ORDER BY violation_rank;"""


# ---------------------------------------------------------------------------
# SQL Query Builder (fluent API)
# ---------------------------------------------------------------------------

class SQLQueryBuilder:
    """Fluent SQL query builder for ad-hoc analytical queries.

    Example::

        q = (SQLQueryBuilder("inspections")
            .select("borough", "COUNT(*) as cnt", "AVG(severity) as avg_sev")
            .where("status = 'Pending Repair'")
            .group_by("borough")
            .having("COUNT(*) > 10")
            .order_by("cnt DESC")
            .limit(20)
            .build())
    """

    def __init__(self, table: str) -> None:
        self._table = table
        self._selects: List[str] = []
        self._joins: List[str] = []
        self._wheres: List[str] = []
        self._groups: List[str] = []
        self._havings: List[str] = []
        self._orders: List[str] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def select(self, *cols: str) -> "SQLQueryBuilder":
        self._selects.extend(cols)
        return self

    def join(self, table: str, on: str, join_type: str = "INNER") -> "SQLQueryBuilder":
        self._joins.append(f"{join_type} JOIN {table} ON {on}")
        return self

    def where(self, *conditions: str) -> "SQLQueryBuilder":
        self._wheres.extend(conditions)
        return self

    def group_by(self, *cols: str) -> "SQLQueryBuilder":
        self._groups.extend(cols)
        return self

    def having(self, *conditions: str) -> "SQLQueryBuilder":
        self._havings.extend(conditions)
        return self

    def order_by(self, *cols: str) -> "SQLQueryBuilder":
        self._orders.extend(cols)
        return self

    def limit(self, n: int) -> "SQLQueryBuilder":
        self._limit = n
        return self

    def offset(self, n: int) -> "SQLQueryBuilder":
        self._offset = n
        return self

    def build(self) -> str:
        parts = []
        select_clause = ", ".join(self._selects) if self._selects else "*"
        parts.append(f"SELECT {select_clause}")
        parts.append(f'FROM "{self._table}"')
        for j in self._joins:
            parts.append(j)
        if self._wheres:
            parts.append("WHERE " + " AND ".join(self._wheres))
        if self._groups:
            parts.append("GROUP BY " + ", ".join(self._groups))
        if self._havings:
            parts.append("HAVING " + " AND ".join(self._havings))
        if self._orders:
            parts.append("ORDER BY " + ", ".join(self._orders))
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")
        if self._offset is not None:
            parts.append(f"OFFSET {self._offset}")
        return "\n".join(parts) + ";"


# ---------------------------------------------------------------------------
# Export DataFrame as SQL file
# ---------------------------------------------------------------------------

def export_as_sql_file(
    df: pd.DataFrame,
    table_name: str,
    path: str,
    dialect: str = "postgres",
    include_create: bool = True,
    primary_key: Optional[str] = None,
) -> str:
    """Export a DataFrame as a complete SQL file with DDL and DML.

    Generates a file that can be loaded into any database via ``psql``,
    ``sqlite3``, or similar CLI tools.
    """
    from pathlib import Path as P
    p = P(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    parts = [f"-- Generated SQL for table: {table_name}", f"-- Rows: {len(df)}", ""]
    if include_create:
        parts.append(dataframe_to_create_table(df, table_name, dialect=dialect, primary_key=primary_key))
        parts.append("")
    parts.append(dataframe_to_insert_sql(df, table_name))

    p.write_text("\n".join(parts), encoding="utf-8")
    return str(p)
