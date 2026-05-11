from __future__ import annotations

from typing import Iterable, Any


def _quote_value(v: Any) -> str:
    """Safely quote a single value for SoQL -- minimal sanitizer.

    Strings are single-quoted with inner single-quotes doubled. Numbers and booleans
    are returned as-is. None becomes NULL.
    """
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    s = s.replace("'", "''")
    return f"'{s}'"


def in_clause(column: str, values: Iterable[Any]) -> str:
    """Build a safe IN(...) clause for SoQL.

    Example: in_clause('id', [1,2,3]) -> "id IN (1,2,3)"
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return "FALSE"
    quoted = ",".join(_quote_value(v) for v in vals)
    return f"{column} IN ({quoted})"


def like_clause(column: str, pattern: str) -> str:
    """Build a LIKE clause with safe quoting.

    Note: SoQL supports LIKE; this quotes the pattern safely.
    """
    return f"{column} LIKE {_quote_value(pattern)}"


def equals_clause(column: str, value: Any) -> str:
    return f"{column} = {_quote_value(value)}"


def and_join(clauses: Iterable[str]) -> str:
    return " AND ".join([c for c in clauses if c])


def or_join(clauses: Iterable[str]) -> str:
    return " OR ".join([c for c in clauses if c])
