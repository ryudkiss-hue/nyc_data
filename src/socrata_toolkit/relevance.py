from __future__ import annotations

"""Relevance ranking helpers for combined FTS + spatial + SLA scoring.

These helpers generate SQL snippets for Postgres that combine `ts_rank` with
operational signals (age, spatial priority) into a single `final_rank` value.
"""

from collections.abc import Iterable


def build_weighted_rank_sql(text_columns: Iterable[str], text_query_param: str = "%s", weight_text: float = 1.0, weight_geo: float = 1.0, weight_age: float = 1.0) -> str:
    """Return a SQL fragment that computes a `final_rank` from text, geo, and age.

    `text_columns` are columns combined into a `to_tsvector()` expression.
    `text_query_param` is the placeholder used by your DB driver (e.g. `%s` for psycopg).
    """
    cols = list(text_columns)
    if not cols:
        raise ValueError("At least one text column is required")
    concat = " || ' ' || ".join(f"COALESCE({c}, '')" for c in cols)
    sql = f"( (ts_rank(to_tsvector('english', {concat}), to_tsquery({text_query_param})) * {weight_text}) + (COALESCE(spatial_priority,0) * {weight_geo}) + ((GREATEST(0, date_part('day', now()::date - COALESCE(inspection_date, now()::date))) / 30.0) * {weight_age}) ) AS final_rank"
    return sql


def websearch_to_tsquery_sql(param: str = "%s") -> str:
    """Return SQL expression that converts a websearch-style query to a tsquery.

    Use in your WHERE clause as: `to_tsvector(...) @@ ({websearch_sql})`.
    """
    return f"websearch_to_tsquery({param})"
