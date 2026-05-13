"""
dash_app/data/db.py
───────────────────
DuckDB / MotherDuck data layer with Dask parallel-fetch helpers.

Connection resolution (in priority order):
  1. MOTHERDUCK_TOKEN env var  →  "md:<DUCKDB_DATABASE>"  (cloud)
  2. DUCKDB_PATH env var        →  path on disk
  3. default                    →  "nyc_mission_control.db"

Thread safety
  • One DuckDB connection per thread (threading.local)
  • Write operations serialised with a module-level Lock
  • MotherDuck connections are read/write by default
"""

from __future__ import annotations

import os
import threading
from typing import Any

import duckdb
import pandas as pd
from dask import delayed
import dask

# ── Environment ───────────────────────────────────────────────────────────────
_MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN", "")
_DB_NAME          = os.getenv("DUCKDB_DATABASE", "nyc_dash")
_DB_PATH          = os.getenv("DUCKDB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "nyc_dash.db"
))
_SOCRATA_TOKEN    = os.getenv("SOCRATA_APP_TOKEN", "")

# ── Connection management ─────────────────────────────────────────────────────
_local      = threading.local()
_write_lock = threading.Lock()


def _conn_string() -> str:
    if _MOTHERDUCK_TOKEN:
        return f"md:{_DB_NAME}?motherduck_token={_MOTHERDUCK_TOKEN}"
    return _DB_PATH


def get_conn() -> duckdb.DuckDBPyConnection:
    """Return a thread-local DuckDB connection (auto-reconnects if closed).
    Falls back to :memory: if the file is locked by another process.
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        path = _conn_string()
        try:
            _local.conn = duckdb.connect(path)
        except Exception as e:
            if "being used by another process" in str(e) or "Cannot open file" in str(e):
                import warnings
                warnings.warn(
                    f"[DuckDB] File '{path}' is locked — starting in :memory: mode. "
                    "Stop all other Python processes and restart for file persistence.",
                    RuntimeWarning, stacklevel=2,
                )
                _local.conn = duckdb.connect(":memory:")
            else:
                raise
    return _local.conn


def is_motherduck() -> bool:
    return bool(_MOTHERDUCK_TOKEN)


# ── Query helpers ─────────────────────────────────────────────────────────────

def query_df(sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    """Execute *sql* and return the result as a pandas DataFrame."""
    try:
        conn = get_conn()
        return conn.execute(sql, params or []).df()
    except Exception:
        return pd.DataFrame()


def query_scalar(sql: str, params: list[Any] | None = None) -> Any:
    """Execute *sql* and return the first cell of the first row."""
    try:
        conn = get_conn()
        result = conn.execute(sql, params or []).fetchone()
        return result[0] if result else None
    except Exception:
        return None


def execute(sql: str, params: list[Any] | None = None) -> None:
    """Execute a write statement (serialised with a lock)."""
    with _write_lock:
        conn = get_conn()
        conn.execute(sql, params or [])


def list_tables() -> list[str]:
    """Return names of all tables in the connected database."""
    try:
        rows = get_conn().execute("SHOW TABLES").fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def table_schema(table: str) -> pd.DataFrame:
    """Return DESCRIBE output for *table* as a DataFrame."""
    return query_df(f'DESCRIBE "{table}"')


def table_row_count(table: str) -> int:
    """Return row count for *table* (fast DuckDB COUNT)."""
    return query_scalar(f'SELECT COUNT(*) FROM "{table}"') or 0


def register_df(name: str, df: pd.DataFrame) -> None:
    """Register *df* as a virtual (in-memory) table named *name*."""
    get_conn().register(name, df)


def upsert_df(df: pd.DataFrame, table: str, pk: str | None = None) -> int:
    """
    Upsert *df* into DuckDB table *table*.
    Creates the table if it does not exist.
    Uses ON CONFLICT DO UPDATE if *pk* is supplied.
    """
    if df.empty:
        return 0
    with _write_lock:
        conn = get_conn()
        conn.register("_upsert_tmp", df)
        existing = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        if table not in existing:
            conn.execute(f'CREATE TABLE "{table}" AS SELECT * FROM _upsert_tmp')
        elif pk and pk in df.columns:
            conn.execute(
                f'INSERT INTO "{table}" SELECT * FROM _upsert_tmp '
                f'ON CONFLICT ({pk}) DO UPDATE SET *'
            )
        else:
            conn.execute(f'INSERT INTO "{table}" SELECT * FROM _upsert_tmp')
    return len(df)


# ── Dask parallel fetch helpers ───────────────────────────────────────────────

@delayed
def _fetch_socrata_page(
    base_url: str,
    limit: int,
    offset: int,
    extra_params: dict[str, str],
    token: str,
) -> pd.DataFrame:
    """Fetch a single page from a Socrata JSON endpoint (Dask delayed)."""
    import requests

    params: dict[str, Any] = {"$limit": limit, "$offset": offset, **extra_params}
    headers = {"X-App-Token": token} if token else {}
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def parallel_socrata_fetch(
    domain: str,
    fourfour: str,
    max_rows: int = 5000,
    page_size: int = 1000,
    token: str | None = None,
    extra_params: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Fetch up to *max_rows* records from a Socrata dataset in parallel using Dask.

    Uses the threaded Dask scheduler — no cluster required.  Each page
    is fetched concurrently, results are concatenated and returned as a
    single pandas DataFrame.
    """
    base_url = f"https://{domain}/resource/{fourfour}.json"
    tok = token or _SOCRATA_TOKEN
    params = extra_params or {}

    offsets = list(range(0, max_rows, page_size))
    tasks = [
        _fetch_socrata_page(base_url, page_size, off, params, tok)
        for off in offsets
    ]
    results: tuple[pd.DataFrame, ...] = dask.compute(*tasks, scheduler="threads")
    frames = [df for df in results if not df.empty]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    return combined.head(max_rows)


def df_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Return a lightweight summary dict for a DataFrame."""
    return {
        "rows":     len(df),
        "columns":  list(df.columns),
        "dtypes":   {c: str(df[c].dtype) for c in df.columns},
        "null_pct": {c: round(df[c].isnull().mean() * 100, 1) for c in df.columns},
        "numeric":  df.select_dtypes("number").columns.tolist(),
        "text":     df.select_dtypes("object").columns.tolist(),
        "date":     [c for c in df.columns if "date" in c.lower() or "time" in c.lower()],
    }
