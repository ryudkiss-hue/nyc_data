"""Publish the small serving layer LOCAL -> MotherDuck (the only cloud write).

"Build local, serve light": the heavy ~5 GB warehouse stays local; this pushes
just the curated serving outputs (Metric catalog, borough/time-series, spatial
metrics) + the lightweight geo attribute dims (~50 MB) to MotherDuck so the Dash
dashboard reads from the cloud. Read-serving only — never hits the compute limit.

Skips gracefully if MOTHERDUCK_TOKEN is unset (offline) so the nightly stays green.
Uses the token from .env on purpose (this stage IS the intended cloud touch).
"""
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

DB = "nyc_dot_analytics"
ROOT = Path(__file__).resolve().parents[1]
LOCAL = str(ROOT / f"{DB}.duckdb")


def main():
    load_dotenv(ROOT / ".env")
    load_dotenv()
    tok = os.getenv("MOTHERDUCK_TOKEN")
    if not tok:
        print("publish_serving: MOTHERDUCK_TOKEN unset — skipping cloud publish")
        return 0
    if not Path(LOCAL).exists():
        print(f"publish_serving: no local DB at {LOCAL} — skipping")
        return 0

    con = duckdb.connect(f"md:{DB}?token={tok}")
    con.execute(f"ATTACH '{LOCAL}' AS localdb (READ_ONLY)")

    pushed = 0
    # serving tables (exclude heavy geometry dims *_geom) + geo attribute dims
    serving = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_catalog='localdb' AND table_schema='serving' "
        "AND table_name NOT LIKE '%\\_geom' ESCAPE '\\'").fetchall()]
    geo = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_catalog='localdb' AND table_schema='geo'").fetchall()]

    con.execute(f"CREATE SCHEMA IF NOT EXISTS {DB}.serving")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {DB}.geo")
    for t in serving:
        con.execute(f'CREATE OR REPLACE TABLE {DB}.serving."{t}" AS SELECT * FROM localdb.serving."{t}"')
        pushed += 1
        print(f"  serving.{t}", flush=True)
    for t in geo:
        con.execute(f'CREATE OR REPLACE TABLE {DB}.geo."{t}" AS SELECT * FROM localdb.geo."{t}"')
        pushed += 1
        print(f"  geo.{t}", flush=True)
    con.close()
    print(f"PUBLISH DONE: {pushed} tables -> MotherDuck serving/geo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
