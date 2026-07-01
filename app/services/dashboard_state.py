"""
Dashboard State Adapter

This module provides the DashboardStateAdapter, a centralized interface for
Dash callbacks to retrieve fully materialized and filtered DataFrames.
It encapsulates global filter parsing, dataset routing, and data caching,
providing a clean seam between the UI triggers and the data/analytics logic.
"""

import logging
from typing import Any, Dict, List, Optional

import geopandas as gpd
import pandas as pd

from app.data_manager import DataManager
from app.services.analytics_service import (
    get_dataset,
    get_metric_metrics,
    get_spatial_data,
    get_timeseries_data,
)

logger = logging.getLogger(__name__)

# Map a dashboard dataset key to its raw warehouse table name where they differ.
_WAREHOUSE_ALIASES = {"lot_info": "lot_info", "tree_damage": "tree_damage"}
_WAREHOUSE_CACHE: dict[str, pd.DataFrame] = {}

# Pre-warm the warehouse cache at import time for the two charts visible on the
# initial dashboard view. This prevents concurrent callback race conditions where
# both viz-velocity and viz-inspections try to open DuckDB simultaneously on first
# page load. Each call takes ~2s; sequencing them here keeps startup deterministic.
def _prewarm_warehouse():
    """Sequentially load all primary dashboard datasets into _WAREHOUSE_CACHE."""
    for key in (
        "built", "inspection", "violations",
        "dismissals", "ramp_progress", "ramp_complaints",
        "lot_info", "sidewalk_planimetric", "tree_damage",
        "complaints_311", "capital_budget",
    ):
        if key not in _WAREHOUSE_CACHE:
            try:
                _read_warehouse_table(key)
            except Exception as _e:
                logger.debug(f"Pre-warm skipped for {key}: {_e}")

# The dataset MultiSelect values are warehouse table names (the new filter system
# uses value=table_name directly).  Legacy 4-item values kept for backward compat.
_UI_DATASET_TO_TABLE: dict[str, str] = {
    # Legacy mappings (old 4-item hardcoded list)
    "capital_projects":   "capital_projects_dashboard",
    "street_paving":      "dot_in_house_street_resurfacing_projects",
    "vision_zero":        "vision_zero_base_report",
    "311_complaints":     "complaints_311",
}

# Every borough may appear as a 2-letter code, a full name, a single letter, or a
# numeric code across the 118 raw tables. Match tolerantly (uppercased).
_BORO_FORMS = {
    "MN": {"MN", "MANHATTAN", "M", "NEW YORK", "1"},
    "BK": {"BK", "BROOKLYN", "B", "KINGS", "3"},
    "BX": {"BX", "BRONX", "X", "2"},
    "QN": {"QN", "QUEENS", "Q", "4"},
    "SI": {"SI", "STATEN ISLAND", "S", "RICHMOND", "5"},
}


def _borough_filter(df: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    """Keep rows whose borough column matches any selected code, tolerant of the
    many encodings used across raw tables. A table without a borough column is
    returned unchanged (the filter simply doesn't apply)."""
    if not codes or "ALL" in codes:
        return df
    boro_cols = [c for c in df.columns if "boro" in c.lower()]
    if not boro_cols:
        return df
    accept = set()
    for c in codes:
        accept |= {v.upper() for v in _BORO_FORMS.get(c.upper(), {c.upper()})}
    col = boro_cols[0]
    series = df[col].astype("string").str.strip().str.upper()
    return df[series.isin(accept)]


def _date_filter(
    df: pd.DataFrame,
    start: str | None,
    end: str | None,
    date_field: str | None = None,
) -> pd.DataFrame:
    """Filter by the selected or first plausible date column. Best-effort."""
    if not start and not end:
        return df
    # Use the analyst-selected date field if it exists in this table; otherwise
    # fall back to the first column whose name contains a date keyword.
    col: str | None = None
    if date_field and date_field in df.columns:
        col = date_field
    else:
        candidates = [c for c in df.columns
                      if any(k in c.lower() for k in ("date", "_dt", "created", "crash"))]
        col = candidates[0] if candidates else None
    if col is None:
        return df
    parsed = pd.to_datetime(df[col], errors="coerce")
    mask = parsed.notna()
    if start:
        mask &= parsed >= pd.to_datetime(start, errors="coerce")
    if end:
        mask &= parsed <= pd.to_datetime(end, errors="coerce")
    return df[mask]


# Status column names and value sets across the raw tables.
_STATUS_COLUMNS = ["cancel", "flag", "status", "violationstatus", "result", "inspectionresult"]
_STATUS_OPEN      = {"OPEN", "ACTIVE", "PENDING", "Y"}
_STATUS_CLOSED    = {"CLOSED", "COMPLETED", "RESOLVED", "N", "C"}
_STATUS_DISMISSED = {"DISMISSED", "D", "X", "VOID"}
_STATUS_IN_PROGRESS = {"IN PROGRESS", "IN-PROGRESS", "INPROGRESS", "P"}


def _status_filter(df: pd.DataFrame, status: str | None) -> pd.DataFrame:
    """Keep rows matching the requested status. 'all' is a no-op."""
    if not status or status == "all":
        return df
    status_col = next((c for c in df.columns if c.lower() in _STATUS_COLUMNS), None)
    if status_col is None:
        return df  # table has no status column; don't drop rows
    values = df[status_col].astype("string").str.strip().str.upper()
    if status == "open":
        return df[values.isin(_STATUS_OPEN)]
    if status == "closed":
        return df[values.isin(_STATUS_CLOSED)]
    if status == "dismissed":
        return df[values.isin(_STATUS_DISMISSED)]
    if status == "in_progress":
        return df[values.isin(_STATUS_IN_PROGRESS)]
    return df


def _community_district_filter(df: pd.DataFrame, cds: list[str] | None) -> pd.DataFrame:
    """Keep rows matching selected community districts (e.g. '101' for MN CD1)."""
    if not cds:
        return df
    # Community district stored as e.g. '101', '201', ... or '1', '2', ...
    cd_col = next((c for c in df.columns if "cb" == c.lower() or "cd" == c.lower()
                   or c.lower() in ("community_board", "communityboard", "cb_num")), None)
    if cd_col is None:
        return df
    series = df[cd_col].astype("string").str.strip()
    return df[series.isin(cds)]


def _read_warehouse_table(key: str, limit: int = 50000) -> pd.DataFrame:
    """Read raw.<key> from the local DuckDB warehouse (cached per process).

    Best-effort: returns an empty frame if the warehouse or table is absent so
    the caller can degrade gracefully.
    """
    if key in _WAREHOUSE_CACHE:
        return _WAREHOUSE_CACHE[key]
    import os
    from pathlib import Path

    db = os.getenv("DUCKDB_PATH") or str(
        Path(__file__).resolve().parents[2] / "nyc_dot_analytics.duckdb")
    if not os.path.isabs(db):
        db = str((Path(__file__).resolve().parents[2] / db).resolve())
    table = _WAREHOUSE_ALIASES.get(key, key)
    df = pd.DataFrame()
    if Path(db).exists():
        try:
            import duckdb
            con = duckdb.connect(db, read_only=True)
            try:
                exists = con.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='raw' AND table_name=?", [table]).fetchone()
                if exists:
                    df = con.execute(f'SELECT * FROM raw."{table}" LIMIT {int(limit)}').fetchdf()
            finally:
                con.close()
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"Warehouse fallback failed for {key}: {e}")
    _WAREHOUSE_CACHE[key] = df
    return df


# Trigger pre-warm now that _read_warehouse_table is defined.
_prewarm_warehouse()


class DashboardStateAdapter:
    """
    Adapter to encapsulate state retrieval and data filtering for the dashboard.

    Provides a unified interface for callbacks to request filtered datasets
    without needing to manually concatenate, cache, or parse global filters.
    """

    def __init__(self, data_manager: DataManager, filters: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter with a DataManager instance and the current global filters.

        Args:
            data_manager: The singleton DataManager instance to fetch cached data.
            filters: The current global filters from the Dash store.
        """
        self.dm = data_manager
        self.filters = filters or {}

    def get_boroughs(self) -> List[str]:
        boroughs = self.filters.get("boroughs", ["MN", "BK", "BX", "QN", "SI"])
        return [boroughs] if isinstance(boroughs, str) else boroughs

    def get_limit(self) -> Optional[int]:
        limit_str = self.filters.get("data_limit", "none")
        return None if limit_str == "none" else int(limit_str)

    def get_selected_datasets(self) -> List[str]:
        return self.filters.get("datasets", ["inspection", "built", "violations", "lot_info"])

    def get_date_range(self) -> tuple[Optional[str], Optional[str]]:
        return self.filters.get("date_start"), self.filters.get("date_end")

    def get_date_field(self) -> Optional[str]:
        return self.filters.get("date_field")

    def get_status(self) -> Optional[str]:
        return self.filters.get("status", "all")

    def get_community_districts(self) -> List[str]:
        return self.filters.get("community_districts", []) or []

    def _apply_all_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all active filters to a dataframe."""
        df = _borough_filter(df, self.get_boroughs())
        df = _community_district_filter(df, self.get_community_districts())
        df = _date_filter(df, *self.get_date_range(), date_field=self.get_date_field())
        df = _status_filter(df, self.get_status())
        return df

    def get_combined_dataset(self, export_cap: Optional[int] = None) -> pd.DataFrame:
        """
        Get a fully materialized and filtered DataFrame containing all selected datasets.

        Args:
            export_cap: When set, limits total rows by capping each dataset slice at
                ``export_cap // n_datasets`` rows before concatenation — keeps the hot
                path fast for interactive exports without touching the ingestion layer.

        Returns:
            pd.DataFrame: Concatenated DataFrame with a '_source_dataset' identifier column.
        """
        datasets = self.get_selected_datasets()
        limit = self.get_limit()
        boroughs = self.get_boroughs()
        start, end = self.get_date_range()

        # Per-dataset slice cap: spread the export budget evenly so we don't read
        # 4× as many rows as needed before the global trim in the caller.
        per_ds_cap: Optional[int] = None
        if export_cap is not None and datasets:
            per_ds_cap = max(1, export_cap // len(datasets))

        combined_df = pd.DataFrame()

        for ds in datasets:
            try:
                ds_key = _UI_DATASET_TO_TABLE.get(ds, ds)
                df_part = self.dm.get_cached_dataset(ds_key)
                if df_part is None or df_part.empty:
                    df_part = _read_warehouse_table(ds_key, limit=per_ds_cap or 50_000)

                if df_part is not None and not df_part.empty:
                    df_part = df_part.copy()
                    df_part = self._apply_all_filters(df_part)
                    if per_ds_cap is not None:
                        df_part = df_part.head(per_ds_cap)
                    elif limit is not None:
                        df_part = df_part.head(limit)
                    df_part["_source_dataset"] = ds
                    combined_df = pd.concat([combined_df, df_part], ignore_index=True)
            except Exception as e:
                logger.warning(f"Error fetching dataset {ds}: {e}")

        return combined_df

    def get_dataset_by_key(self, dataset_key: str) -> pd.DataFrame:
        """Get a specific cached dataset by key, properly filtered.

        Falls back to the local warehouse (raw.<key>) when the in-memory Socrata
        cache is cold — so the visualization panels render real ingested data in a
        local-first run instead of empty figures.
        """
        table_key = _UI_DATASET_TO_TABLE.get(dataset_key, dataset_key)
        df = self.dm.get_cached_dataset(table_key)
        if df is None or df.empty:
            df = _read_warehouse_table(table_key)
        if df is None or df.empty:
            return pd.DataFrame()

        df = self._apply_all_filters(df)
        limit = self.get_limit()
        if limit is not None:
            df = df.head(limit)
        return df

    def get_analytics_dataset(self) -> pd.DataFrame:
        """Get the base dataset for analytics (Phase C) properly filtered.

        Routes through get_dataset_by_key so all 7 filter dimensions apply
        and the local warehouse is the authoritative source.
        """
        # Determine the primary analytics dataset from the filter selection.
        selected = self.get_selected_datasets()
        primary = selected[0] if selected else "inspection"
        return self.get_dataset_by_key(primary)

    def get_spatial_dataset(self) -> gpd.GeoDataFrame:
        """Get the spatial dataset for mapping (Phase B/D) properly filtered."""
        gdf = get_spatial_data(self.filters)
        limit = self.get_limit()
        if not gdf.empty and limit is not None:
            gdf = gdf.head(limit)
        return gdf

    def get_timeseries_dataset(self) -> pd.DataFrame:
        """Get the timeseries dataset (Phase E) properly filtered."""
        df = get_timeseries_data("built", "approved_date", "project_id", self.filters)
        limit = self.get_limit()
        if not df.empty and limit is not None:
            df = df.head(limit)
        return df

    def get_metrics_dataset(self) -> pd.DataFrame:
        """Get the KPIs dataset properly filtered."""
        df = get_metric_metrics(self.filters)
        limit = self.get_limit()
        if not df.empty and limit is not None:
            df = df.head(limit)
        return df
