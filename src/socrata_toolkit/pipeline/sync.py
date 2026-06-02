"""Incremental Socrata → DuckDB sync."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from ..core import (
    COL_AT_ID,
    COL_ID,
    DuckDBManager,
    DuckDBRepository,
    SocrataClient,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def sync_dataset(
    domain: str,
    fourfour: str,
    db_path: str,
    table_name: str,
    updated_col: str,
    token: str = "",
) -> int:
    """Incrementally sync a Socrata dataset into a local DuckDB table."""
    manager = DuckDBManager(db_path)
    client = SocrataClient()
    if token:
        client.config.app_token = token

    last_updated = None
    try:
        res = manager.query(f'SELECT max("{updated_col}") FROM "{table_name}"').fetchone()
        if res and res[0]:
            last_updated = res[0]
            if hasattr(last_updated, "isoformat"):
                last_updated = last_updated.isoformat()
    except Exception:
        logger.info("Initializing table %s for first-time sync.", table_name)

    where = f"{updated_col} > '{last_updated}'" if last_updated else None
    order = f"{updated_col} ASC"

    total_to_fetch = None
    if tqdm:
        try:
            import requests

            count_params = {"$select": "count(*)"}
            if where:
                count_params["$where"] = where
            url = f"https://{domain}/resource/{fourfour}.json"
            resp = requests.get(url, params=count_params, headers=client._headers(), timeout=10)
            if resp.status_code == 200:
                total_to_fetch = int(resp.json()[0]["count"])
        except Exception:
            pass

    pbar = None
    if tqdm and (total_to_fetch is None or total_to_fetch > 0):
        bar_fmt = (
            "{desc} {percentage:3.0f}% │{bar}│ {n_fmt}/{total_fmt} rows [ETA: {remaining}, {rate_fmt}]"
            if total_to_fetch
            else "{desc}: {n_fmt} rows [{elapsed}, {rate_fmt}]"
        )
        pbar = tqdm(
            total=total_to_fetch,
            desc=f"Streaming {fourfour}",
            unit="rows",
            bar_format=bar_fmt,
        )

    repo = DuckDBRepository(manager, table_name)
    pk = None
    table_initialized = False
    count = 0

    try:
        for batch in client.fetch_json(domain, fourfour, where=where, order=order):
            if not batch:
                continue
            df_batch = pd.DataFrame(batch)

            if not table_initialized:
                pk = (
                    COL_ID
                    if COL_ID in df_batch.columns
                    else (COL_AT_ID if COL_AT_ID in df_batch.columns else None)
                )
                table_initialized = True

            if pk:
                repo.upsert_dataframe(df_batch, pk)
            else:
                existing_tables = manager.conn.execute("SHOW TABLES").fetchall()
                table_exists = any(t[0] == table_name for t in existing_tables)
                manager.conn.register("temp_df", df_batch)
                if table_exists:
                    manager.query(f'INSERT INTO "{table_name}" SELECT * FROM temp_df')
                else:
                        # Sanitize identifier: strip embedded quotes before quoting
                    safe_table = table_name.replace('"', '')
                    manager.conn.execute(f'CREATE TABLE "{safe_table}" AS SELECT * FROM temp_df')

            count += len(batch)
            if pbar:
                pbar.update(len(batch))
                rate = pbar.format_dict.get("rate")
                if rate:
                    if rate > 2000:
                        pbar.colour = "#10b981"
                    elif rate > 500:
                        pbar.colour = "#f59e0b"
                    else:
                        pbar.colour = "#ef4444"

    except (Exception, KeyboardInterrupt) as e:
        logger.exception("Sync fetch failed: %s", e)
        if pbar:
            pbar.close()
        manager.close()
        return count

    if pbar:
        pbar.close()
    manager.close()
    return count
