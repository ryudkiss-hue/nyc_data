"""
Helper functions for database connection and environment management.
"""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

log = logging.getLogger("analysis_helpers")

def load_env(env_path: str = ".env") -> Dict[str, Any]:
    """
    Loads environment variables from a .env file.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except (ImportError, Exception): # pylint: disable=broad-exception-caught
        log.warning("Could not load .env file; using system environment.")

    # Return a dictionary to satisfy the 'dict' return type requirement
    return {
        "PG_DSN": os.getenv("PG_DSN"),
        "EXPORT_DIR": os.getenv("EXPORT_DIR", "analysis"),
        "MAPBOX_TOKEN": os.getenv("MAPBOX_TOKEN_PUBLIC"),
        "SOCRATA_APP_TOKEN": os.getenv("SOCRATA_APP_TOKEN"),
    }

def get_engine(pg_dsn: str | None):
    """
    Creates a database engine using SQLAlchemy or Psycopg.
    """
    if not pg_dsn:
        log.error("PG_DSN is missing.")
        return None
        
    try:
        import sqlalchemy as sa # pylint: disable=import-outside-toplevel
        return sa.create_engine(pg_dsn)
    except (ImportError, Exception): # pylint: disable=broad-exception-caught
        try:
            import psycopg # pylint: disable=import-outside-toplevel
            return psycopg.connect(pg_dsn)
        except (ImportError, Exception): # pylint: disable=broad-exception-caught
            log.error("Failed to connect to database.")
            return None

def list_tables(con) -> pd.DataFrame:
    """Returns a list of all public base tables in the database."""
    q = """SELECT table_schema, table_name
           FROM information_schema.tables
           WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
           ORDER BY table_name"""
    return pd.read_sql_query(q, con)

def candidate_sidewalk_tables(con) -> List[str]:
    """Identifies potential sidewalk-related tables based on keywords."""
    tbls = list_tables(con)
    keywords = [
        "sidewalk", "inspection", "inspections", "ramp", "ada",
        "permit", "contract", "repair", "complaint",
    ]
    candidates = [t for t in tbls.table_name if any(k in t.lower() for k in keywords)]
    if not candidates:
        candidates = ["inspections", "sidewalk_contracts", "sidewalk_progress", "permits", "contracts"]
    return list(dict.fromkeys(candidates))

def safe_read_table(con, table: str, limit: int = 2000) -> pd.DataFrame:
    """Attempts to read a table with a fallback for schema-less queries."""
    q = f'SELECT * FROM public."{table}" LIMIT {limit}'
    try:
        return pd.read_sql_query(q, con)
    except Exception: # pylint: disable=broad-exception-caught
        return pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT {limit}', con)

def find_latlon_columns(df: pd.DataFrame) -> Optional[tuple]:
    """Heuristically finds latitude and longitude columns in a DataFrame."""
    lat_candidates = [c for c in df.columns if c.lower() in ("latitude", "lat", "y")]
    lon_candidates = [c for c in df.columns if c.lower() in ("longitude", "lon", "lng", "x")]
    if lat_candidates and lon_candidates:
        return lat_candidates[0], lon_candidates[0]
    
    floats = [c for c in df.columns if pd.api.types.is_float_dtype(df[c]) or pd.api.types.is_integer_dtype(df[c])]
    for a in floats:
        for b in floats:
            if a == b: continue
            v1, v2 = df[a].dropna(), df[b].dropna()
            if not v1.empty and not v2.empty:
                if v1.between(-90, 90).mean() > 0.7 and v2.between(-180, 180).mean() > 0.7:
                    return a, b
    return None

def compute_kpis_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Computes sidewalk defect KPIs from the provided DataFrame."""
    try:
        from socrata_toolkit.dot_sidewalk import compute_sidewalk_kpis # pylint: disable=import-outside-toplevel
        k = compute_sidewalk_kpis(df)
        return k.__dict__
    except (ImportError, Exception): # pylint: disable=broad-exception-caught
        total_defects = df.get("violations", pd.Series(dtype="float")).fillna(0).sum() if "violations" in df.columns else None
        miles = df.get("curb_miles", pd.Series(dtype="float")).fillna(0).sum() if "curb_miles" in df.columns else None
        defect_density = (total_defects / miles) if (total_defects is not None and miles) else None
        return {"defect_density": defect_density}
