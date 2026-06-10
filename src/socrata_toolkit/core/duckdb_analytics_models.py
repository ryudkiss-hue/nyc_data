"""Pre-computed analytics marts materialized from staging tables.

Each ``create_*`` function reads from staging tables (primarily
``staging.inspections``), drops and recreates its ``analytics.<name>`` table
(idempotent), and returns a scheduler-safe status dict::

    {"status": "success", "table": "analytics.<name>", "row_count": N}
    {"status": "error", "error": "...", "table": "analytics.<name>"}

Functions never raise — the scheduler calls them with no arguments and
aggregates the dicts.

Column discovery is defensive: staging tables carry whatever columns the raw
Socrata data had (no guaranteed schema), so each mart picks columns from
candidate lists via ``_pick_column`` and degrades gracefully (omitting a
metric and adding a ``"note"`` key) when a column is absent.
"""

import logging

from socrata_toolkit.core import duckdb_pipeline as dp
from socrata_toolkit.core.duckdb_pipeline import (
    _existing_columns,
    _pick_column,
    _table_exists,
)

logger = logging.getLogger(__name__)

_BOROUGH_CANDIDATES = ["borough", "boro", "borough_code", "borough_name"]
_DATE_CANDIDATES = [
    "created_date",
    "inspection_date",
    "status_date",
    ":updated_at",
]
_MATERIAL_CANDIDATES = ["material_type", "material", "sidewalk_material"]
_LAT_CANDIDATES = ["latitude", "lat", "point_y"]
_LON_CANDIDATES = ["longitude", "lon", "lng", "point_x"]
_GEOM_CANDIDATES = ["the_geom", "geom", "geometry", "location"]
_ID_CANDIDATES = ["objectid", "object_id", "id"]
_VIOLATION_METRIC = "violation_count"

_STAGING_INSPECTIONS = "staging.inspections"


def _get_conn():
    return dp.get_duckdb_connection(dp._connection_path or dp.DEFAULT_DB_PATH)


def _drop_target(conn, table: str) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    # Earlier versions of this module created VIEWs under the same names, and
    # DuckDB's DROP TABLE/VIEW IF EXISTS errors on a type mismatch.
    name = table.split(".", 1)[1]
    row = conn.execute(
        "SELECT table_type FROM information_schema.tables "
        "WHERE table_schema = 'analytics' AND table_name = ?",
        [name],
    ).fetchone()
    if row is not None:
        kind = "VIEW" if row[0] == "VIEW" else "TABLE"
        conn.execute(f"DROP {kind} IF EXISTS {table}")


def _materialize(conn, table: str, select_sql: str) -> int:
    _drop_target(conn, table)
    conn.execute(f"CREATE TABLE {table} AS {select_sql}")
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _create_empty(conn, table: str, columns_sql: str) -> None:
    _drop_target(conn, table)
    conn.execute(f"CREATE TABLE {table} ({columns_sql})")


def _staging_error(table: str) -> dict:
    return {
        "status": "error",
        "error": f"{_STAGING_INSPECTIONS} does not exist; run staging first",
        "table": table,
    }


def _result(table: str, row_count: int, notes: list[str]) -> dict:
    result = {"status": "success", "table": table, "row_count": row_count}
    if notes:
        result["note"] = "; ".join(notes)
    return result


def _month_expr(date_col: str) -> str:
    return f"DATE_TRUNC('month', TRY_CAST(\"{date_col}\" AS TIMESTAMP))"


def create_borough_summary() -> dict:
    """Borough-level counts and violation aggregates from staging.inspections."""
    table = "analytics.borough_summary"
    try:
        conn = _get_conn()
        if not _table_exists(conn, "staging", "inspections"):
            return _staging_error(table)
        cols = _existing_columns(conn, _STAGING_INSPECTIONS)
        borough = _pick_column(cols, _BOROUGH_CANDIDATES)
        if borough is None:
            return {
                "status": "error",
                "error": (
                    "no borough column found in staging.inspections "
                    f"(candidates: {_BOROUGH_CANDIDATES})"
                ),
                "table": table,
            }
        notes: list[str] = []
        metrics = ["COUNT(*) AS record_count"]
        if _VIOLATION_METRIC in cols:
            metrics.append(
                f'SUM(TRY_CAST("{_VIOLATION_METRIC}" AS BIGINT)) AS total_violations'
            )
            metrics.append(
                f'AVG(TRY_CAST("{_VIOLATION_METRIC}" AS DOUBLE)) AS avg_violations'
            )
        else:
            notes.append("violation_count not in staging data; violation metrics omitted")
        date_col = _pick_column(cols, _DATE_CANDIDATES)
        if date_col:
            metrics.append(
                f'MAX(TRY_CAST("{date_col}" AS TIMESTAMP)) AS latest_record_date'
            )
        sql = (
            f'SELECT UPPER(CAST("{borough}" AS VARCHAR)) AS borough, '
            f"{', '.join(metrics)} FROM {_STAGING_INSPECTIONS} GROUP BY 1"
        )
        row_count = _materialize(conn, table, sql)
        return _result(table, row_count, notes)
    except Exception as e:
        logger.error(f"Failed to create {table}: {e}")
        return {"status": "error", "error": str(e), "table": table}


def create_time_series_snapshots() -> dict:
    """Monthly snapshots (month x borough) from staging.inspections."""
    table = "analytics.time_series_snapshots"
    try:
        conn = _get_conn()
        if not _table_exists(conn, "staging", "inspections"):
            return _staging_error(table)
        cols = _existing_columns(conn, _STAGING_INSPECTIONS)
        date_col = _pick_column(cols, _DATE_CANDIDATES)
        if date_col is None:
            return {
                "status": "error",
                "error": (
                    "no date column found in staging.inspections "
                    f"(candidates: {_DATE_CANDIDATES})"
                ),
                "table": table,
            }
        notes: list[str] = []
        month = _month_expr(date_col)
        select = [f"{month} AS month"]
        group = ["1"]
        borough = _pick_column(cols, _BOROUGH_CANDIDATES)
        if borough:
            select.append(f'UPPER(CAST("{borough}" AS VARCHAR)) AS borough')
            group.append("2")
        else:
            notes.append("no borough column; snapshots grouped by month only")
        select.append("COUNT(*) AS record_count")
        if _VIOLATION_METRIC in cols:
            select.append(
                f'SUM(TRY_CAST("{_VIOLATION_METRIC}" AS BIGINT)) AS total_violations'
            )
        else:
            notes.append("violation_count not in staging data; violation metrics omitted")
        sql = (
            f"SELECT {', '.join(select)} FROM {_STAGING_INSPECTIONS} "
            f"WHERE {month} IS NOT NULL GROUP BY {', '.join(group)}"
        )
        row_count = _materialize(conn, table, sql)
        return _result(table, row_count, notes)
    except Exception as e:
        logger.error(f"Failed to create {table}: {e}")
        return {"status": "error", "error": str(e), "table": table}


def create_material_analysis_mart() -> dict:
    """Per-material aggregates; empty table with note if no material column."""
    table = "analytics.material_analysis_mart"
    try:
        conn = _get_conn()
        if not _table_exists(conn, "staging", "inspections"):
            return _staging_error(table)
        cols = _existing_columns(conn, _STAGING_INSPECTIONS)
        material = _pick_column(cols, _MATERIAL_CANDIDATES)
        if material is None:
            _create_empty(
                conn,
                table,
                "material VARCHAR, record_count BIGINT, "
                "total_violations BIGINT, avg_violations DOUBLE",
            )
            return {
                "status": "success",
                "table": table,
                "row_count": 0,
                "note": "no material column in staging data",
            }
        notes: list[str] = []
        metrics = ["COUNT(*) AS record_count"]
        if _VIOLATION_METRIC in cols:
            metrics.append(
                f'SUM(TRY_CAST("{_VIOLATION_METRIC}" AS BIGINT)) AS total_violations'
            )
            metrics.append(
                f'AVG(TRY_CAST("{_VIOLATION_METRIC}" AS DOUBLE)) AS avg_violations'
            )
        else:
            notes.append("violation_count not in staging data; violation metrics omitted")
        sql = (
            f'SELECT CAST("{material}" AS VARCHAR) AS material, '
            f"{', '.join(metrics)} FROM {_STAGING_INSPECTIONS} "
            f'WHERE "{material}" IS NOT NULL GROUP BY 1'
        )
        row_count = _materialize(conn, table, sql)
        return _result(table, row_count, notes)
    except Exception as e:
        logger.error(f"Failed to create {table}: {e}")
        return {"status": "error", "error": str(e), "table": table}


def create_clustering_features() -> dict:
    """Per-record numeric feature matrix for unsupervised clustering."""
    table = "analytics.clustering_features"
    try:
        conn = _get_conn()
        if not _table_exists(conn, "staging", "inspections"):
            return _staging_error(table)
        cols = _existing_columns(conn, _STAGING_INSPECTIONS)
        notes: list[str] = []
        id_col = _pick_column(cols, _ID_CANDIDATES)
        if id_col:
            select = [f'"{id_col}" AS record_id']
        else:
            select = ["ROW_NUMBER() OVER () AS record_id"]
            notes.append("no id column; record_id synthesized via ROW_NUMBER")
        if _VIOLATION_METRIC in cols:
            select.append(
                f'COALESCE(TRY_CAST("{_VIOLATION_METRIC}" AS BIGINT), 0) '
                "AS violation_count"
            )
            select.append(
                f'CASE WHEN COALESCE(TRY_CAST("{_VIOLATION_METRIC}" AS BIGINT), 0) > 0 '
                "THEN 1 ELSE 0 END AS has_violations"
            )
        else:
            select.append("0 AS violation_count")
            select.append("0 AS has_violations")
            notes.append("violation_count not in staging data; defaulted to 0")
        lat = _pick_column(cols, _LAT_CANDIDATES)
        lon = _pick_column(cols, _LON_CANDIDATES)
        geom = _pick_column(cols, _GEOM_CANDIDATES)
        if lat and lon:
            select.append(f'TRY_CAST("{lat}" AS DOUBLE) AS latitude')
            select.append(f'TRY_CAST("{lon}" AS DOUBLE) AS longitude')
        elif geom:
            select.append(f'CAST("{geom}" AS VARCHAR) AS geom')
            notes.append(
                "only geometry column available; stored as-is, coordinate "
                "extraction deferred (spatial extension availability varies)"
            )
        else:
            notes.append("no geo columns in staging data; geo features skipped")
        sql = f"SELECT {', '.join(select)} FROM {_STAGING_INSPECTIONS}"
        row_count = _materialize(conn, table, sql)
        return _result(table, row_count, notes)
    except Exception as e:
        logger.error(f"Failed to create {table}: {e}")
        return {"status": "error", "error": str(e), "table": table}


def create_geo_animation_mart() -> dict:
    """Month x borough x avg lat/lon aggregates for animated maps."""
    table = "analytics.geo_animation_mart"
    empty_schema = (
        "month TIMESTAMP, borough VARCHAR, avg_latitude DOUBLE, "
        "avg_longitude DOUBLE, record_count BIGINT, total_violations BIGINT"
    )
    try:
        conn = _get_conn()
        if not _table_exists(conn, "staging", "inspections"):
            return _staging_error(table)
        cols = _existing_columns(conn, _STAGING_INSPECTIONS)
        lat = _pick_column(cols, _LAT_CANDIDATES)
        lon = _pick_column(cols, _LON_CANDIDATES)
        geom = _pick_column(cols, _GEOM_CANDIDATES)
        if not (lat and lon):
            _create_empty(conn, table, empty_schema)
            note = (
                "only geometry column available; coordinate extraction deferred "
                "(spatial extension availability varies)"
                if geom
                else "no lat/lon columns in staging data"
            )
            return {"status": "success", "table": table, "row_count": 0, "note": note}
        date_col = _pick_column(cols, _DATE_CANDIDATES)
        if date_col is None:
            return {
                "status": "error",
                "error": (
                    "no date column found in staging.inspections "
                    f"(candidates: {_DATE_CANDIDATES})"
                ),
                "table": table,
            }
        notes: list[str] = []
        month = _month_expr(date_col)
        select = [f"{month} AS month"]
        group = ["1"]
        borough = _pick_column(cols, _BOROUGH_CANDIDATES)
        if borough:
            select.append(f'UPPER(CAST("{borough}" AS VARCHAR)) AS borough')
            group.append("2")
        else:
            notes.append("no borough column; aggregated by month only")
        select.append(f'AVG(TRY_CAST("{lat}" AS DOUBLE)) AS avg_latitude')
        select.append(f'AVG(TRY_CAST("{lon}" AS DOUBLE)) AS avg_longitude')
        select.append("COUNT(*) AS record_count")
        if _VIOLATION_METRIC in cols:
            select.append(
                f'SUM(TRY_CAST("{_VIOLATION_METRIC}" AS BIGINT)) AS total_violations'
            )
        else:
            notes.append("violation_count not in staging data; violation metrics omitted")
        sql = (
            f"SELECT {', '.join(select)} FROM {_STAGING_INSPECTIONS} "
            f"WHERE {month} IS NOT NULL GROUP BY {', '.join(group)}"
        )
        row_count = _materialize(conn, table, sql)
        return _result(table, row_count, notes)
    except Exception as e:
        logger.error(f"Failed to create {table}: {e}")
        return {"status": "error", "error": str(e), "table": table}


def refresh_all_analytics_views(conn=None) -> dict:
    """Refresh all analytics marts.

    The ``conn`` argument is deprecated and ignored — the create_* functions
    use the module-level pipeline connection (kept for backwards compatibility
    with the legacy ``DuckDBPipeline`` class).
    """
    if conn is not None:
        logger.warning(
            "refresh_all_analytics_views(conn) is deprecated; the conn argument "
            "is ignored and the module-level connection is used"
        )
    results = {
        "borough_summary": create_borough_summary(),
        "time_series_snapshots": create_time_series_snapshots(),
        "material_analysis_mart": create_material_analysis_mart(),
        "clustering_features": create_clustering_features(),
        "geo_animation_mart": create_geo_animation_mart(),
    }
    success_count = sum(1 for r in results.values() if r.get("status") == "success")
    logger.info(f"Refreshed {success_count}/{len(results)} analytics marts")
    return results
