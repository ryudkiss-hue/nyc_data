"""PostGIS spatial query service for enterprise NYC DOT datasets.

Optional — requires psycopg (psycopg3) and a PostGIS-enabled PostgreSQL database.
Install: pip install psycopg[binary]

The service mirrors the Socrata fetch_dataset() interface so callers can
swap data sources without changing their analysis code.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import psycopg

    HAS_PSYCOPG = True
except ImportError:
    psycopg = None  # type: ignore[assignment]
    HAS_PSYCOPG = False


@dataclass
class PostGISConfig:
    """Connection configuration for a PostGIS database."""

    host: str = "localhost"
    port: int = 5432
    dbname: str = "nyc_dot"
    user: str = "postgres"
    password: str = ""
    schema: str = "public"
    connect_timeout: int = 10

    @property
    def conninfo(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password} "
            f"connect_timeout={self.connect_timeout}"
        )


@dataclass
class SpatialQueryResult:
    """Result of a PostGIS spatial query."""

    df: pd.DataFrame
    row_count: int
    query: str
    warnings: list[str] = field(default_factory=list)


class PostGISService:
    """Thin wrapper around psycopg for running PostGIS spatial queries.

    Usage:
        cfg = PostGISConfig(host="...", dbname="nyc_dot", user="...", password="...")
        svc = PostGISService(cfg)
        if svc.test_connection():
            result = svc.query_within_circle("inspections", lat=40.73, lon=-73.93, radius_m=500)
    """

    def __init__(self, config: PostGISConfig):
        self.config = config
        self._conn = None

    def _require_psycopg(self) -> None:
        if not HAS_PSYCOPG:
            raise ImportError(
                "psycopg (psycopg3) is required for PostGIS integration. "
                "Install with: pip install 'psycopg[binary]'"
            )

    def test_connection(self) -> tuple[bool, str]:
        """Test connectivity to the PostGIS database.

        Returns:
            (success: bool, message: str)
        """
        self._require_psycopg()
        try:
            with psycopg.connect(self.config.conninfo, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT PostGIS_Version()")
                    version = cur.fetchone()[0]
            return True, f"PostGIS {version}"
        except Exception as exc:
            return False, str(exc)

    def run_query(self, sql: str, params: tuple = ()) -> SpatialQueryResult:
        """Execute a raw SQL query and return results as a DataFrame.

        Args:
            sql: SQL string (may use %s placeholders).
            params: Query parameters.

        Returns:
            SpatialQueryResult with .df and .row_count.
        """
        self._require_psycopg()
        with psycopg.connect(self.config.conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.description:
                    cols = [d.name for d in cur.description]
                    rows = cur.fetchall()
                    df = pd.DataFrame(rows, columns=cols)
                else:
                    df = pd.DataFrame()
        return SpatialQueryResult(df=df, row_count=len(df), query=sql)

    def query_within_circle(
        self,
        table: str,
        lat: float,
        lon: float,
        radius_m: float,
        geom_col: str = "geom",
        columns: str = "*",
        limit: int = 10_000,
    ) -> SpatialQueryResult:
        """Return rows within a given radius of a point.

        Uses ST_DWithin on a geography column for accurate meter-based distance.
        """
        sql = f"""
            SELECT {columns}
            FROM {self.config.schema}.{table}
            WHERE ST_DWithin(
                {geom_col}::geography,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                %s
            )
            LIMIT %s
        """
        return self.run_query(sql, (lon, lat, radius_m, limit))

    def query_within_borough(
        self,
        table: str,
        borough: str,
        borough_col: str = "borough",
        columns: str = "*",
        limit: int = 50_000,
    ) -> SpatialQueryResult:
        """Return rows where the borough column matches (case-insensitive)."""
        sql = f"""
            SELECT {columns}
            FROM {self.config.schema}.{table}
            WHERE upper({borough_col}) = upper(%s)
            LIMIT %s
        """
        return self.run_query(sql, (borough, limit))

    def query_intersects(
        self,
        table: str,
        wkt_polygon: str,
        geom_col: str = "geom",
        columns: str = "*",
        limit: int = 10_000,
    ) -> SpatialQueryResult:
        """Return rows whose geometry intersects a WKT polygon."""
        sql = f"""
            SELECT {columns}
            FROM {self.config.schema}.{table}
            WHERE ST_Intersects(
                {geom_col},
                ST_GeomFromText(%s, 4326)
            )
            LIMIT %s
        """
        return self.run_query(sql, (wkt_polygon, limit))

    def list_tables(self) -> list[str]:
        """List spatial tables (those with a geometry column) in the schema."""
        sql = """
            SELECT f_table_name
            FROM geometry_columns
            WHERE f_table_schema = %s
            ORDER BY f_table_name
        """
        result = self.run_query(sql, (self.config.schema,))
        if result.df.empty:
            return []
        return result.df["f_table_name"].tolist()

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
