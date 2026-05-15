# socrata_toolkit/analysis_helpers.py
"""Helper functions for database connection and environment management."""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

log = logging.getLogger("analysis_helpers")


# -----------------------------
# ENVIRONMENT
# -----------------------------


def load_env(env_path: str = ".env") -> dict[str, Any]:
    """
    Loads environment variables from a .env file if python-dotenv is available.
    Returns a dict of commonly used environment values.
    """
    try:
        from dotenv import load_dotenv  # optional dependency

        load_dotenv(env_path)
    except Exception:
        # Not fatal; environment may be set elsewhere
        log.debug("python-dotenv not available or failed to load %s", env_path, exc_info=True)

    return {
        "PG_DSN": os.getenv("PG_DSN"),
        "EXPORT_DIR": os.getenv("EXPORT_DIR", "analysis"),
        "MAPBOX_TOKEN": os.getenv("MAPBOX_TOKEN"),
    }


# -----------------------------
# DATABASE
# -----------------------------


def get_engine(pg_dsn: str | None) -> Engine | None:
    """
    Creates a SQLAlchemy engine for database access.
    Returns None if pg_dsn is falsy or engine creation fails.
    """
    if not pg_dsn:
        log.error("PG_DSN is missing.")
        return None

    try:
        engine = create_engine(pg_dsn)
        return engine
    except Exception as exc:
        log.error("Failed to create SQLAlchemy engine: %s", exc, exc_info=True)
        return None


def list_tables(engine: Engine) -> pd.DataFrame:
    """
    Returns a DataFrame of public base tables with columns: table_schema, table_name.
    Raises on failure so callers can decide how to handle it.
    """
    q = """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    return pd.read_sql_query(q, engine)


def candidate_sidewalk_tables(engine: Engine) -> list[str]:
    """
    Identifies potential sidewalk-related tables based on keywords.
    Returns a de-duplicated list of candidate table names.
    """
    try:
        tbls = list_tables(engine)
    except Exception as exc:
        log.warning("Could not list tables: %s", exc, exc_info=True)
        # Return sensible defaults if we cannot query the DB
        return [
            "inspections",
            "sidewalk_contracts",
            "sidewalk_progress",
            "permits",
            "contracts",
        ]

    if "table_name" not in tbls.columns:
        log.warning("Unexpected list_tables result columns: %s", tbls.columns.tolist())
        return []

    keywords = [
        "sidewalk",
        "inspection",
        "inspections",
        "ramp",
        "ada",
        "permit",
        "contract",
        "repair",
        "complaint",
    ]

    candidates = [
        t for t in tbls["table_name"].astype(str) if any(k in t.lower() for k in keywords)
    ]

    if not candidates:
        candidates = [
            "inspections",
            "sidewalk_contracts",
            "sidewalk_progress",
            "permits",
            "contracts",
        ]

    # preserve order and deduplicate
    return list(dict.fromkeys(candidates))


def safe_read_table(engine: Engine, table: str, limit: int = 2000) -> pd.DataFrame:
    """
    Safely reads a table with fallback quoting strategies.
    Validates the table name against information_schema to avoid SQL injection.
    Returns an empty DataFrame on failure.
    """
    try:
        tbls = list_tables(engine)
    except Exception as exc:
        log.error("Unable to fetch table list to validate table name: %s", exc, exc_info=True)
        return pd.DataFrame()

    valid_tables = set(tbls["table_name"].astype(str).tolist())
    if table not in valid_tables:
        log.error("Requested table %s not found in public schema", table)
        return pd.DataFrame()

    # Use a fully qualified, quoted identifier using the public schema
    q = text(f'SELECT * FROM public."{table}" LIMIT :limit')

    try:
        return pd.read_sql_query(q, engine, params={"limit": limit})
    except Exception as exc:
        log.warning("Primary query failed for table %s: %s", table, exc, exc_info=True)

    # Fallback: try without schema qualification (some DBs or views)
    q2 = text(f'SELECT * FROM "{table}" LIMIT :limit')
    try:
        return pd.read_sql_query(q2, engine, params={"limit": limit})
    except Exception as exc:
        log.warning("Fallback query failed for table %s: %s", table, exc, exc_info=True)

    log.error("Failed to read table: %s", table)
    return pd.DataFrame()


# -----------------------------
# GEO HELPERS
# -----------------------------


def find_latlon_columns(df: pd.DataFrame) -> tuple[str, str] | None:
    """
    Heuristically finds latitude and longitude columns in a DataFrame.
    Returns a tuple (lat_col, lon_col) or None if not found.
    """
    lat_candidates = [c for c in df.columns if c.lower() in ("latitude", "lat", "y")]
    lon_candidates = [c for c in df.columns if c.lower() in ("longitude", "lon", "lng", "x")]

    if lat_candidates and lon_candidates:
        return lat_candidates[0], lon_candidates[0]

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    for a in numeric_cols:
        for b in numeric_cols:
            if a == b:
                continue

            v1 = df[a].dropna()
            v2 = df[b].dropna()

            if v1.empty or v2.empty:
                continue

            lat_score = v1.between(-90, 90).mean()
            lon_score = v2.between(-180, 180).mean()

            if lat_score > 0.8 and lon_score > 0.8:
                return a, b

    return None


# -----------------------------
# KPI COMPUTATION
# -----------------------------


def compute_kpis_from_df(df: pd.DataFrame) -> dict[str, Any]:
    """
    Computes sidewalk-related KPIs from a DataFrame.
    Tries to delegate to dot_sidewalk.compute_sidewalk_kpis if available.
    Returns a dict of KPI values.
    """
    try:
        # optional specialized implementation
        from socrata_toolkit.dot_sidewalk import compute_sidewalk_kpis  # type: ignore

        k = compute_sidewalk_kpis(df)
        # If compute_sidewalk_kpis returns a dataclass or object, convert to dict
        if hasattr(k, "__dict__"):
            return dict(k.__dict__)
        if isinstance(k, dict):
            return k
    except ImportError:
        log.debug("dot_sidewalk.compute_sidewalk_kpis not available; using fallback KPIs")
    except Exception as exc:
        log.warning("Primary KPI computation failed: %s", exc, exc_info=True)

    total_defects = None
    if "violations" in df.columns:
        try:
            total_defects = df["violations"].fillna(0).astype(float).sum()
        except Exception:
            total_defects = df["violations"].fillna(0).sum()

    miles = None
    if "curb_miles" in df.columns:
        try:
            miles = df["curb_miles"].fillna(0).astype(float).sum()
        except Exception:
            miles = df["curb_miles"].fillna(0).sum()

    defect_density = None
    if total_defects is not None and miles not in (None, 0):
        try:
            defect_density = total_defects / miles
        except Exception:
            defect_density = None

    return {
        "defect_density": defect_density,
        "total_defects": total_defects,
        "curb_miles": miles,
    }
