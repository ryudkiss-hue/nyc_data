"""
Helper functions for database connection and environment management.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List

import pandas as pd
from sqlalchemy import create_engine, text

log = logging.getLogger("analysis_helpers")


# -----------------------------
# ENVIRONMENT
# -----------------------------

def load_env(env_path: str = ".env") -> Dict[str, Any]:
    """
    Loads environment variables from a .env file.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        pass

    return {
        "PG_DSN": os.getenv("PG_DSN"),
        "EXPORT_DIR": os.getenv("EXPORT_DIR", "analysis"),
        "MAPBOX_TOKEN": os.getenv("MAPBOX_TOKEN"),
    }


# -----------------------------
# DATABASE
# -----------------------------

def get_engine(pg_dsn: str | None):
    """
    Creates a SQLAlchemy engine for database access.
    """
    if not pg_dsn:
        log.error("PG_DSN is missing.")
        return None

    try:
        return create_engine(pg_dsn)
    except Exception as e:
        log.error("Failed to create SQLAlchemy engine: %s", e)
        return None


def list_tables(engine) -> pd.DataFrame:
    """
    Returns a list of all public base tables in the database.
    """
    q = """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    return pd.read_sql_query(q, engine)


def candidate_sidewalk_tables(engine) -> List[str]:
    """
    Identifies potential sidewalk-related tables based on keywords.
    """
    tbls = list_tables(engine)

    keywords = [
        "sidewalk", "inspection", "inspections", "ramp", "ada",
        "permit", "contract", "repair", "complaint",
    ]

    candidates = [
        t for t in tbls.table_name
        if any(k in t.lower() for k in keywords)
    ]

    if not candidates:
        candidates = [
            "inspections",
            "sidewalk_contracts",
            "sidewalk_progress",
            "permits",
            "contracts",
        ]

    return list(dict.fromkeys(candidates))


def safe_read_table(engine, table: str, limit: int = 2000) -> pd.DataFrame:
    """
    Safely reads a table with fallback quoting strategies.
    """
    queries = [
        text(f'SELECT * FROM public."{table}" LIMIT :limit'),
        text(f'SELECT * FROM "{table}" LIMIT :limit'),
    ]

    for q in queries:
        try:
            return pd.read_sql_query(q, engine, params={"limit": limit})
        except Exception as e:
            log.warning("Query failed for table %s: %s", table, e)

    log.error("Failed to read table: %s", table)
    return pd.DataFrame()


# -----------------------------
# GEO HELPERS
# -----------------------------

def find_latlon_columns(df: pd.DataFrame) -> Optional[tuple]:
    """
    Heuristically finds latitude and longitude columns in a DataFrame.
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

def compute_kpis_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes sidewalk-related KPIs from a DataFrame.
    """
    try:
        from socrata_toolkit.dot_sidewalk import compute_sidewalk_kpis
        k = compute_sidewalk_kpis(df)
        return k.__dict__
    except ImportError:
        pass  # fallback only
    except Exception as e:
        log.warning("Primary KPI computation failed: %s", e)

    total_defects = (
        df["violations"].fillna(0).sum()
        if "violations" in df.columns
        else None
    )

    miles = (
        df["curb_miles"].fillna(0).sum()
        if "curb_miles" in df.columns
        else None
    )

    defect_density = (
        total_defects / miles
        if total_defects is not None and miles not in (None, 0)
        else None
    )

    return {
        "defect_density": defect_density,
        "total_defects": total_defects,
        "curb_miles": miles,
    }