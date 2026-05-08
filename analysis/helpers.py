from __future__ import annotations
import os
import logging
from typing import Optional, List, Dict, Any

import pandas as pd

log = logging.getLogger("analysis_helpers")
logging.basicConfig(level=logging.INFO)


def load_env(env_path: str = ".env") -> dict:
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


def get_engine(pg_dsn: str):
    try:
        import sqlalchemy as sa

        return sa.create_engine(pg_dsn)
    except Exception:
        import psycopg

        return psycopg.connect(pg_dsn)


def list_tables(con) -> pd.DataFrame:
    q = """SELECT table_schema, table_name
           FROM information_schema.tables
           WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
           ORDER BY table_name"""
    return pd.read_sql_query(q, con)


def candidate_sidewalk_tables(con) -> List[str]:
    tbls = list_tables(con)
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
    candidates = [t for t in tbls.table_name if any(k in t.lower() for k in keywords)]
    if not candidates:
        candidates = [
            "inspections",
            "sidewalk_contracts",
            "sidewalk_progress",
            "permits",
            "contracts",
        ]
    # preserve order, remove duplicates
    return list(dict.fromkeys(candidates))


def safe_read_table(con, table: str, limit: int = 2000) -> pd.DataFrame:
    q = f'SELECT * FROM public."{table}" LIMIT {limit}'
    try:
        return pd.read_sql_query(q, con)
    except Exception:
        return pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT {limit}', con)


def find_latlon_columns(df: pd.DataFrame) -> Optional[tuple]:
    lat_candidates = [c for c in df.columns if c.lower() in ("latitude", "lat", "y")]
    lon_candidates = [c for c in df.columns if c.lower() in ("longitude", "lon", "lng", "x")]
    if lat_candidates and lon_candidates:
        return lat_candidates[0], lon_candidates[0]
    floats = [
        c
        for c in df.columns
        if pd.api.types.is_float_dtype(df[c]) or pd.api.types.is_integer_dtype(df[c])
    ]
    for a in floats:
        for b in floats:
            if a == b:
                continue
            v1 = df[a].dropna()
            v2 = df[b].dropna()
            if v1.empty or v2.empty:
                continue
            if v1.between(-90, 90).mean() > 0.7 and v2.between(-180, 180).mean() > 0.7:
                return a, b
    return None


def compute_kpis_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    try:
        from socrata_toolkit.dot_sidewalk import compute_sidewalk_kpis

        k = compute_sidewalk_kpis(df)
        return k.__dict__
    except Exception:
        total_defects = (
            df.get("violations", pd.Series(dtype="float")).fillna(0).sum()
            if "violations" in df.columns
            else None
        )
        miles = (
            df.get("curb_miles", pd.Series(dtype="float")).fillna(0).sum()
            if "curb_miles" in df.columns
            else None
        )
        defect_density = (total_defects / miles) if (total_defects is not None and miles) else None
        return {"defect_density": defect_density}
