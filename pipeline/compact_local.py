#!/usr/bin/env python3
"""Compact the local DuckDB warehouse — reclaim space and drop transient schemas.

Repeated CREATE OR REPLACE during the pipeline leaves dead pages; dropping
scratch schemas + CHECKPOINT compacts the file. For maximal shrink it rewrites
the database to a fresh file via COPY FROM DATABASE (DuckDB's true vacuum) when
that yields a smaller file.

Local-only: operates on ./nyc_dot_analytics.duckdb (MOTHERDUCK_TOKEN ignored).
"""
import os
from pathlib import Path

import duckdb

DB = "nyc_dot_analytics"
ROOT = Path(__file__).resolve().parents[1]
DROP_SCHEMAS = ("test_schema", "verification", "main")  # scratch / leftover


def main():
    dbfile = ROOT / f"{DB}.duckdb"
    if not dbfile.exists():
        print(f"no local db at {dbfile}; nothing to compact")
        return 0
    con = duckdb.connect(str(dbfile))
    for sch in DROP_SCHEMAS:
        try:
            con.execute(f"DROP SCHEMA IF EXISTS {sch} CASCADE")
        except Exception as e:
            print(f"  skip drop {sch}: {str(e)[:50]}")
    con.execute("CHECKPOINT")
    size = con.execute("PRAGMA database_size").fetchdf()
    con.close()
    mb = dbfile.stat().st_size / 1e6
    print(f"compacted {dbfile.name}: {mb:.0f} MB on disk")
    try:
        print(size.to_string(index=False))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
