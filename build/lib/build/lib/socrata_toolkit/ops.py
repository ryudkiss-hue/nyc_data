from __future__ import annotations

"""Operational automation helpers.

This module contains helper functions to implement Grace Period tracking,
permit look-aheads, burndown (workload forecasting), and SQL generator helpers
for trigger-based priority flagging.

All functions include detailed docstrings and sample SQL to help you adapt
them to a PostGIS-backed production database.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import pandas as pd


def apply_grace_period_updates(
    df: pd.DataFrame,
    issued_date_col: str = "issued_date",
    grace_days_col: str = "GRACE_PD",
    status_col: str = "status",
    override_days: Optional[int] = 75,
) -> pd.DataFrame:
    """Apply Grace Period logic to a DataFrame of violations.

    This function computes the elapsed days since `issued_date` and updates the
    `status_col` to `City-Initiated` when the grace period has elapsed. The
    `grace_days_col` may be NULL; `override_days` is a safety-default used when
    no explicit GRACE_PD is provided.

    Returns a copy of the DataFrame with two extra columns: `_days_elapsed`
    and `_grace_trigger` (boolean).
    """
    df = df.copy()
    now = datetime.now(timezone.utc)

    def _parse_date(v: Any) -> Optional[datetime]:
        if pd.isna(v):
            return None
        if isinstance(v, datetime):
            return v
        try:
            return pd.to_datetime(v).to_pydatetime()
        except Exception:
            return None

    issued = df[issued_date_col].apply(_parse_date)
    df["_days_elapsed"] = issued.apply(lambda d: (now - d).days if d else None)

    def _should_trigger(row):
        days = row.get("_days_elapsed")
        grace = row.get(grace_days_col)
        if grace is None or pd.isna(grace):
            grace = override_days
        try:
            return days is not None and days >= int(grace)
        except Exception:
            return False

    df["_grace_trigger"] = df.apply(_should_trigger, axis=1)
    # update status where triggered
    df.loc[df["_grace_trigger"] & (df[status_col] == "Pending Repair"), status_col] = "City-Initiated"
    return df


def permit_lookahead_sql(proposed_table: str, permit_table: str, days: int = 90, proposed_geom_col: str = "geom", permit_geom_col: str = "geom") -> str:
    """Generate SQL that finds permits starting in the next `days` days that spatially intersect proposed work.

    This returns a parameterized SQL snippet intended for use with psycopg/psycopg2.
    Adjust field names and date logic to match local schemas.
    """
    sql = f"""
    SELECT p.*, prm.permit_id, prm.start_date
    FROM {proposed_table} p
    JOIN {permit_table} prm
      ON ST_DWithin(p.{proposed_geom_col}::geography, prm.{permit_geom_col}::geography, 50)
    WHERE prm.start_date >= now()::date
      AND prm.start_date <= (now()::date + interval '{days} days')
    """
    return sql


def generate_burndown(contract_df: pd.DataFrame, daily_capacity_sqft: float = 1000.0) -> Dict[str, Any]:
    """Generate a simple burndown forecast for a contract.

    `contract_df` should contain an area estimate column named `area_sqft`.
    Returns estimated days to completion and a time series projection (coarse).
    """
    df = contract_df.copy()
    if "area_sqft" not in df.columns:
        raise ValueError("contract_df must include 'area_sqft'")
    remaining = float(df["area_sqft"].sum())
    days = int(max(1, remaining / daily_capacity_sqft))
    projection = {"days_to_complete": days, "remaining_sqft": remaining}
    return projection


def flag_high_priority_trigger_sql(table_name: str, geom_col: str = "geom", corridor_table: str = "smart_spine", corridor_geom: str = "geom") -> str:
    """Return a SQL template for a trigger that flags high-priority complaints.

    The returned SQL creates a trigger function that sets `is_high_priority` and
    inserts a row into `alerts` when a record intersects a known high-pedestrian corridor.
    """
    sql = f"""
    CREATE OR REPLACE FUNCTION flag_high_priority_{table_name}()
    RETURNS trigger AS $$
    BEGIN
      IF (NEW.{geom_col} IS NOT NULL AND EXISTS(SELECT 1 FROM {corridor_table} s WHERE ST_Intersects(NEW.{geom_col}, s.{corridor_geom}))) THEN
        NEW.is_high_priority := TRUE;
        INSERT INTO alerts (severity, message, payload) VALUES ('critical', 'SmartSpine conflict', to_jsonb(NEW));
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_flag_high_priority_{table_name}
    BEFORE INSERT OR UPDATE ON {table_name}
    FOR EACH ROW EXECUTE FUNCTION flag_high_priority_{table_name}();
    """
    return sql
