"""Aggregated ingest of bicycle_pedestrian_counts (ct66-47at) — daily counts per
sensor/direction/mode, NOT the 20.5M raw rows. Server-side SoQL $group, paged.
Lands in local raw.bicycle_pedestrian_counts_daily. Geo joins via sensor_id ->
bicycle_and_pedestrian_count_sensors (6up2-gnw8) which has locations.
"""
import os
import time

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv("C:/Users/ryudk/Desktop/nyc_data/.env")
TOK = os.getenv("SOCRATA_APP_TOKEN", "")
from pathlib import Path

LOCAL = str(Path(__file__).resolve().parents[1] / "nyc_dot_analytics.duckdb")
NAME = "bicycle_pedestrian_counts_daily"
BASE = "https://data.cityofnewyork.us/resource/ct66-47at.json"
PAGE = 50000

con = duckdb.connect(LOCAL)
con.execute("CREATE SCHEMA IF NOT EXISTS raw")
offset = 0
total = 0
created = False
while True:
    params = {
        "$select": "sensor_id,direction,travelmode,date_trunc_ymd(timestamp) as day, sum(counts) as cnt",
        "$group": "sensor_id,direction,travelmode,day",
        "$order": "sensor_id,direction,travelmode,day",
        "$limit": PAGE, "$offset": offset,
    }
    if TOK:
        params["$$app_token"] = TOK
    rows = None
    for attempt in range(5):
        try:
            r = requests.get(BASE, params=params, timeout=180)
            r.raise_for_status()
            rows = r.json()
            break
        except Exception as e:
            print(f"  attempt {attempt+1} failed: {e!r}", flush=True)
            time.sleep(2 ** attempt)
    if rows is None:
        print("FATAL fetch", flush=True)
        raise SystemExit(1)
    if not rows:
        break
    df = pd.DataFrame(rows)
    con.register("_t", df)
    con.execute(f'CREATE OR REPLACE TABLE raw."{NAME}" AS SELECT * FROM _t' if not created
                else f'INSERT INTO raw."{NAME}" BY NAME SELECT * FROM _t')
    con.unregister("_t")
    created = True
    total += len(df)
    offset += PAGE
    print(f"  +{len(df):,} (total {total:,})", flush=True)
    if len(rows) < PAGE:
        break
    time.sleep(0.2)

n = con.execute(f'SELECT COUNT(*) FROM raw."{NAME}"').fetchone()[0]
con.close()
print(f"\nCT66_DAILY DONE: {n:,} daily rows\nDONE", flush=True)
