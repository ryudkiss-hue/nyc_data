from __future__ import annotations

from typing import Any


class SoQLBuilder:
    """Fluent interface for building Socrata Query Language (SoQL) strings."""

    def __init__(self) -> None:
        self._select: list[str] = []
        self._where: list[str] = []
        self._order: list[str] = []
        self._group: list[str] = []
        self._limit: int | None = None
        self._offset: int | None = None
        self._q: str | None = None
        self._having: list[str] = []
        self._variables: dict[str, Any] = {}

    def set_variable(self, name: str, value: Any) -> SoQLBuilder:
        """Set a variable for substitution."""
        self._variables[name] = value
        return self

    def select(self, *columns: str) -> SoQLBuilder:
        """Specify columns to return ($select)."""
        self._select.extend(columns)
        return self

    def where(self, *clauses: str) -> SoQLBuilder:
        """Add filtering conditions ($where)."""
        self._where.extend(clauses)
        return self

    def date_trunc(
        self, column: str, precision: str = "month", alias: str | None = None
    ) -> SoQLBuilder:
        """Add a date_trunc expression to the select clause."""
        expr = f"date_trunc_{precision}({column})"
        if alias:
            expr = f"{expr} AS {alias}"
        self._select.append(expr)
        return self

    def aggregate(self, func: str, column: str = "*", alias: str | None = None) -> SoQLBuilder:
        """Add an aggregation expression to the select clause."""
        expr = f"{func}({column})"
        if alias:
            expr = f"{expr} AS {alias}"
        self._select.append(expr)
        return self

    def order(self, column: str, desc: bool = False) -> SoQLBuilder:
        """Add ordering ($order)."""
        self._order.append(f"{column} {'DESC' if desc else 'ASC'}")
        return self

    def group(self, *columns: str) -> SoQLBuilder:
        """Add grouping ($group)."""
        self._group.extend(columns)
        return self

    def limit(self, value: int) -> SoQLBuilder:
        """Set row limit ($limit)."""
        self._limit = value
        return self

    def offset(self, value: int) -> SoQLBuilder:
        """Set row offset ($offset)."""
        self._offset = value
        return self

    def search(self, query: str) -> SoQLBuilder:
        """Full-text search ($q)."""
        self._q = query
        return self

    def having(self, *clauses: str) -> SoQLBuilder:
        """Add grouped filtering conditions ($having)."""
        self._having.extend(clauses)
        return self

    def _apply_variables(self, text: str) -> str:
        """Substitute {{var}} with values."""
        for k, v in self._variables.items():
            text = text.replace(f"{{{{{k}}}}}", str(v))
        return text

    def build(self) -> dict[str, str]:
        """Build the parameters dictionary for SocrataClient."""
        params: dict[str, str] = {}
        if self._select:
            params["select"] = self._apply_variables(", ".join(self._select))
        if self._where:
            params["where"] = self._apply_variables(" AND ".join(f"({c})" for c in self._where))
        if self._order:
            params["order"] = self._apply_variables(", ".join(self._order))
        if self._group:
            params["group"] = self._apply_variables(", ".join(self._group))
        if self._having:
            params["having"] = self._apply_variables(" AND ".join(f"({c})" for c in self._having))
        if self._limit:
            params["limit"] = str(self._limit)
        if self._offset is not None:
            params["offset"] = str(self._offset)
        if self._q:
            params["q"] = self._apply_variables(self._q)
        return params

    def build_query_string(self) -> str:
        """Build a raw SoQL query string ($query)."""
        parts = []
        if self._select:
            parts.append(f"SELECT {self._apply_variables(', '.join(self._select))}")
        if self._where:
            parts.append(
                f"WHERE {self._apply_variables(' AND '.join(f'({c})' for c in self._where))}"
            )
        if self._group:
            parts.append(f"GROUP BY {self._apply_variables(', '.join(self._group))}")
        if self._having:
            parts.append(
                f"HAVING {self._apply_variables(' AND '.join(f'({c})' for c in self._having))}"
            )
        if self._order:
            parts.append(f"ORDER BY {self._apply_variables(', '.join(self._order))}")
        if self._limit:
            parts.append(f"LIMIT {self._limit}")
        if self._offset:
            parts.append(f"OFFSET {self._offset}")
        return " ".join(parts)

    @staticmethod
    def between(column: str, start: str, end: str) -> str:
        """Helper for between(column, start, end)."""
        return f"{column} between '{start}' and '{end}'"

    @staticmethod
    def within_circle(column: str, lat: float, lon: float, radius_meters: float) -> str:
        """Helper for within_circle(column, lat, lon, radius)."""
        return f"within_circle({column}, {lat}, {lon}, {radius_meters})"

    @staticmethod
    def within_box(column: str, lat_nw: float, lon_nw: float, lat_se: float, lon_se: float) -> str:
        """Helper for within_box(column, lat_nw, lon_nw, lat_se, lon_se)."""
        return f"within_box({column}, {lat_nw}, {lon_nw}, {lat_se}, {lon_se})"

