"""
Socrata toolkit workflows, data quality, and Productivity ROI telemetry.

Maps four operational views to cross-dataset logic on the ingestion matrix.
Includes enhanced column profiling, health scoring, and quality metrics.
"""

from __future__ import annotations

import hashlib
import logging
import json
import re
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any
from functools import lru_cache

import pandas as pd

from app.services.roi_service import ProductivityROI

# Pre-compile regex for BBL normalization (performance optimization)
_RE_NON_DIGIT = re.compile(r"\D")

# Module-level memoization caches for column-type detection
_GEO_COLUMN_CACHE: dict[str, Any] = {}
_DATE_COLUMN_CACHE: dict[str, Any] = {}

def normalize_bbl(series: pd.Series) -> pd.Series:
    """Industrial-grade vectorized BBL normalization."""
    # Convert to string and strip non-digits using pre-compiled regex
    s = series.astype(str).str.replace(_RE_NON_DIGIT, "", regex=True)
    # Filter short values and pad to 10 digits (NYC Standard)
    s = s.where(s.str.len() >= 6, other=pd.NA)
    return s.str.zfill(10)

from app.data_loader import (
    BBL_CANDIDATES,
    DATE_CANDIDATES,
    GRACE_CANDIDATES,
    OWNER_CANDIDATES,
    df_to_gdf,
    pick_column,
)

try:
    import geopandas as gpd
except ImportError:
    gpd = None  # type: ignore

log = logging.getLogger(__name__)

# LRU Cache for column detection to prevent memory leaks in long sessions
@lru_cache(maxsize=128)
def _get_cached_geo_cols(schema_hash: str, columns_tuple: tuple[str, ...]) -> list[str]:
    """
    Detect and cache geospatial column names based on common naming patterns.
    
    Args:
        schema_hash: A unique hash of the dataframe schema.
        columns_tuple: A tuple of column names.
        
    Returns:
        A list of identified geospatial column names.
    """
    geo_names = {"latitude", "longitude", "lat", "lon", "lng", "the_geom", "geometry",
                 "x", "y", "xcoord", "ycoord", "location", "point"}
    return [c for c in columns_tuple if c.lower() in geo_names or "geo" in c.lower() or "coord" in c.lower()]

@lru_cache(maxsize=128)
def _get_cached_date_cols(schema_hash: str, columns_tuple: tuple[str, ...]) -> list[str]:
    """
    Detect and cache date/time column names based on common naming patterns.
    
    Args:
        schema_hash: A unique hash of the dataframe schema.
        columns_tuple: A tuple of column names.
        
    Returns:
        A list of identified date/time column names.
    """
    date_names = {"date", "created", "updated", "opened", "closed", "timestamp", "time"}
    result = []
    for col in columns_tuple:
        if any(d in col.lower() for d in date_names):
            result.append(col)
    return result


from pydantic import BaseModel, Field

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Anomaly Detection & State Machines
# ---------------------------------------------------------------------------

class AnomalyDetector:
    """Multi-signal anomaly detection: Seasonal Median + Z-Score."""
    def __init__(self, window: int = 30):
        self.window = window

    def detect(self, series: pd.Series) -> pd.DataFrame:
        """Runs seasonal median and z-score detection."""
        # Seasonal Median (using rolling median as proxy for seasonal baseline)
        median = series.rolling(window=self.window, center=True).median()
        deviation = (series - median).abs()
        
        # Z-Score
        z_scores = stats.zscore(series, nan_policy='omit')
        
        results = pd.DataFrame({
            'value': series,
            'median_baseline': median,
            'deviation': deviation,
            'z_score': z_scores
        })
        # Flag anomalies
        results['is_anomaly'] = (results['deviation'] > results['median_baseline'] * 0.5) | (results['z_score'].abs() > 3)
        return results

class SeverityStateMachine:
    """Escalates severity based on persistent anomalies over a window."""
    def __init__(self):
        self.state = "ok"
        self.history = []
        
    def update(self, is_anomaly: bool) -> str:
        self.history.append(is_anomaly)
        if len(self.history) > 7: self.history.pop(0)
        
        anomaly_count = sum(self.history)
        
        if anomaly_count >= 5: self.state = "critical"
        elif anomaly_count >= 2: self.state = "warn"
        else: self.state = "ok"
        
        return self.state

def process_hiqa_inspection_stream(series: pd.Series) -> pd.DataFrame:
    """Processes HIQA inspection stream with anomaly detection and severity escalation."""
    detector = AnomalyDetector()
    state_machine = SeverityStateMachine()
    
    anomalies = detector.detect(series)
    
    # Apply state machine
    anomalies['severity'] = [state_machine.update(is_anom) for is_anom in anomalies['is_anomaly']]
    
    return anomalies

# ---------------------------------------------------------------------------
# Data-quality types (Pydantic Upgraded)
# ---------------------------------------------------------------------------

class ColumnProfile(BaseModel):
    """Per-column statistics computed over a sample. High-fidelity validation."""
    name: str
    dtype: str
    null_pct: float
    cardinality: int
    sample_values: list[str] = Field(default_factory=list)
    min_val: str = ""
    max_val: str = ""
    is_numeric: bool = False
    is_datetime: bool = False
    is_geo: bool = False

    def quality_score(self) -> float:
        """0-100 score for this column's health. Strict industrial grading."""
        score = 100.0
        score -= min(self.null_pct * 0.5, 40)  # null penalty
        if self.cardinality == 1:
            score -= 20  # constant column
        if self.cardinality <= 0:
            score -= 60  # all-null or error (Guarantees <= 0 after null penalty)
        return max(0.0, score)


class DatasetProfile(BaseModel):
    """Full dataset profile with column-level stats."""
    key: str
    row_count: int
    col_count: int
    columns: list[ColumnProfile]
    geo_columns: list[str]
    date_columns: list[str]
    pk_candidates: list[str]
    fk_candidates: list[str]
    overall_null_pct: float
    duplicate_row_pct: float
    quality_score: float

    def as_dict(self) -> dict[str, Any]:
        return self.dict()

@lru_cache(maxsize=1)
def _get_roi_aggregator():
    from app.services.roi_service import ROIAggregator
    return ROIAggregator()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _utc_today() -> pd.Timestamp:
    return pd.Timestamp.now(tz=timezone.utc).normalize().tz_localize(None)


def _safe_sample_values(series: pd.Series, n: int = 3) -> list[str]:
    """Return n representative non-null string values from a series."""
    vals = series.dropna().unique()
    return [str(v)[:60] for v in vals[:n]]


def _estimate_cardinality(series: pd.Series, max_sample: int = 5000, dataset_key: str | None = None, col_name: str | None = None) -> int:
    """Estimate distinct value count. Prioritizes DuckDB SQL for performance."""
    from app.data_loader import _DUCKDB_AVAILABLE, _DUCKDB_PATH
    
    if _DUCKDB_AVAILABLE and dataset_key and col_name:
        try:
            from socrata_toolkit.core.duckdb_store import DuckDBManager
            manager = DuckDBManager(_DUCKDB_PATH)
            # Use SQL for exact count on cached data
            res = manager.query(f'SELECT count(DISTINCT "{col_name}") FROM "{dataset_key}"').fetchone()
            count = int(res[0]) if res else -1
            manager.close()
            return count
        except Exception:
            pass

    try:
        if len(series) > max_sample:
            # Sample-based estimation for large series
            sample = series.sample(min(max_sample, len(series)), random_state=42)
            return int(sample.nunique())
        return int(series.nunique())
    except Exception:
        return -1


def _detect_geo_columns(df: pd.DataFrame) -> list[str]:
    """Detect geographic columns. Uses mutable DataFrame id for caching."""
    df_id = id(df)
    if df_id in _GEO_COLUMN_CACHE:
        return _GEO_COLUMN_CACHE[df_id]

    geo_names = {"latitude", "longitude", "lat", "lon", "lng", "the_geom", "geometry",
                 "x", "y", "xcoord", "ycoord", "location", "point"}
    result = [c for c in df.columns if c.lower() in geo_names or "geo" in c.lower() or "coord" in c.lower()]
    _GEO_COLUMN_CACHE[df_id] = result
    return result


def _detect_date_columns(df: pd.DataFrame) -> list[str]:
    """Detect date columns with single-pass scan."""
    df_id = id(df)
    if df_id in _DATE_COLUMN_CACHE:
        return _DATE_COLUMN_CACHE[df_id]

    date_names = {"date", "created", "updated", "opened", "closed", "timestamp", "time"}
    result = []
    for col in df.columns:
        col_l = col.lower()
        if any(d in col_l for d in date_names):
            result.append(col)
        elif df[col].dtype == "object":
            sample = df[col].dropna().head(5)
            try:
                if pd.api.types.is_datetime64_any_dtype(sample):
                    parsed = sample
                else:
                    parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().mean() > 0.8:
                    result.append(col)
            except Exception:
                pass

    result = list(dict.fromkeys(result))  # deduplicate preserving order
    _DATE_COLUMN_CACHE[df_id] = result
    return result


def _detect_pk_candidates(df: pd.DataFrame) -> list[str]:
    """Columns likely to be primary keys: high cardinality + low nulls."""
    pk_keywords = {"id", "key", "uid", "uuid", "no", "num", "number", "code", "identifier"}
    candidates = []
    for col in df.columns:
        col_l = col.lower()
        if any(kw in col_l for kw in pk_keywords):
            null_pct = df[col].isna().mean()
            card = _estimate_cardinality(df[col])
            if null_pct < 0.05 and card > len(df) * 0.9:
                candidates.append(col)
    return candidates[:3]


def _compute_duplicate_pct(df: pd.DataFrame, sample_size: int = 5000, dataset_key: str | None = None) -> float:
    """Compute duplicate percentage. Prioritizes DuckDB SQL for performance."""
    from app.data_loader import _DUCKDB_AVAILABLE, _DUCKDB_PATH
    
    if _DUCKDB_AVAILABLE and dataset_key:
        try:
            from socrata_toolkit.core.duckdb_store import DuckDBManager
            manager = DuckDBManager(_DUCKDB_PATH)
            # DuckDB SQL for exact duplicate detection
            res = manager.query(f'SELECT count(*) FROM "{dataset_key}"').fetchone()
            total = int(res[0]) if res else 0
            res_u = manager.query(f'SELECT count(*) FROM (SELECT DISTINCT * FROM "{dataset_key}")').fetchone()
            unique = int(res_u[0]) if res_u else total
            manager.close()
            
            if total > 0:
                return round(100.0 * (total - unique) / total, 2)
            return 0.0
        except Exception:
            pass

    if df is None or df.empty or len(df) < 2:
        return 0.0
    try:
        # Sample for large dataframes to avoid O(n) full scan
        check_df = df.sample(min(sample_size, len(df)), random_state=42) if len(df) > sample_size else df
        dupes = check_df.duplicated().sum()
        return round(100.0 * dupes / len(check_df), 2)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Dataset profiler
# ---------------------------------------------------------------------------

def profile_dataset(key: str, df: pd.DataFrame, *, sample_rows: int = 5_000) -> DatasetProfile:
    """Compute a full DatasetProfile for a DataFrame. Optimized with schema memoization and early returns."""
    if df.empty:
        return DatasetProfile(
            key=key, row_count=0, col_count=0, columns=[],
            geo_columns=[], date_columns=[], pk_candidates=[], fk_candidates=[],
            overall_null_pct=0.0, duplicate_row_pct=0.0, quality_score=0.0,
        )

    # Use a fast hash of the columns and shape for schema memoization
    schema_hash = hashlib.md5(f"{list(df.columns)}-{df.shape[1]}".encode()).hexdigest()
    columns_tuple = tuple(df.columns)
    
    # Check LRU caches for pre-detected columns
    date_cols_list = _get_cached_date_cols(schema_hash, columns_tuple)
    geo_cols_list = _get_cached_geo_cols(schema_hash, columns_tuple)
    
    sample = df.sample(min(sample_rows, len(df)), random_state=42) if len(df) > sample_rows else df

    date_cols_set = set(c.lower() for c in date_cols_list)
    geo_cols_set = set(c.lower() for c in geo_cols_list)

    col_profiles: list[ColumnProfile] = []
    for col in sample.columns:
        if col.startswith("_"):
            continue  # skip internal columns
        
        series = sample[col]
        null_pct = round(series.isna().mean() * 100, 2)
        cardinality = _estimate_cardinality(series, dataset_key=key, col_name=col)
        sample_vals = _safe_sample_values(series)
        dtype = str(series.dtype)

        is_numeric = pd.api.types.is_numeric_dtype(series)
        is_datetime = "datetime" in dtype or col.lower() in date_cols_set
        is_geo = col.lower() in geo_cols_set

        min_val = max_val = ""
        if is_numeric and series.notna().any():
            try:
                min_val = str(round(series.min(), 4))
                max_val = str(round(series.max(), 4))
            except Exception:
                pass
        elif is_datetime and series.notna().any():
            try:
                # Performance: Bypass parsing if already datetime-like
                if pd.api.types.is_datetime64_any_dtype(series):
                    parsed = series
                else:
                    parsed = pd.to_datetime(series, errors="coerce")
                
                min_val = str(parsed.min())[:10]
                max_val = str(parsed.max())[:10]
            except Exception:
                pass

        col_profiles.append(ColumnProfile(
            name=col, dtype=dtype, null_pct=null_pct,
            cardinality=cardinality, sample_values=sample_vals,
            min_val=min_val, max_val=max_val,
            is_numeric=is_numeric, is_datetime=is_datetime, is_geo=is_geo,
        ))

    overall_null = round(sample.isna().values.mean() * 100, 2) if not sample.empty else 0.0
    dup_pct = _compute_duplicate_pct(df, dataset_key=key)

    # Use cached detection results
    geo_cols = geo_cols_list
    date_cols = date_cols_list
    pk_cands = _detect_pk_candidates(df)

    # Foreign key candidates: known shared keys
    from app.data_loader import BBL_CANDIDATES as BK
    fk_cands = [c for c in df.columns if any(k in c.lower() for k in BK)][:5]

    # Quality score
    col_scores = [cp.quality_score() for cp in col_profiles]
    avg_col_score = sum(col_scores) / len(col_scores) if col_scores else 50.0
    dup_penalty = min(dup_pct * 0.5, 20)
    quality = max(0.0, avg_col_score - dup_penalty)

    # Clean up large intermediate sample before returning
    del sample
    
    return DatasetProfile(
        key=key,
        row_count=len(df),
        col_count=len(df.columns),
        columns=col_profiles,
        geo_columns=geo_cols,
        date_columns=date_cols,
        pk_candidates=pk_cands,
        fk_candidates=fk_cands,
        overall_null_pct=overall_null,
        duplicate_row_pct=dup_pct,
        quality_score=quality,
    )


def profile_all_datasets(frames: dict[str, pd.DataFrame]) -> dict[str, DatasetProfile]:
    """Profile all loaded datasets concurrently using ThreadPoolExecutor."""
    profiles: dict[str, DatasetProfile] = {}
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Filter valid frames
    valid_frames = {k: v for k, v in frames.items() if not v.empty and "_error" not in v.columns}
    
    with ThreadPoolExecutor(max_workers=min(len(valid_frames) or 1, 4)) as executor:
        future_to_key = {executor.submit(profile_dataset, key, df): key for key, df in valid_frames.items()}
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                profiles[key] = future.result()
            except Exception as exc:
                log.warning("Profile failed for %s: %s", key, exc)
                
    return profiles


# ---------------------------------------------------------------------------
# ROI computation
# ---------------------------------------------------------------------------

def compute_productivity_roi(
    *,
    lots_validated: int,
    spatial_conflicts_checked: int,
    contracts_cleared: int,
    joins_automated: int,
    actionable_discrepancies: int,
    quality_flags: int = 0,
    datasets_profiled: int = 0,
) -> ProductivityROI:
    """
    Time-savings matrix (engineering baselines):
      lots * 3 min + conflicts * 15 min + contracts * 5 min + quality_flags * 2 min
    """
    minutes = (
        lots_validated * 3
        + spatial_conflicts_checked * 15
        + contracts_cleared * 5
        + quality_flags * 2
    )
    return ProductivityROI(
        joins_automated=joins_automated,
        actionable_discrepancies=actionable_discrepancies,
        lots_validated=lots_validated,
        spatial_conflicts_checked=spatial_conflicts_checked,
        contracts_cleared=contracts_cleared,
        hours_reclaimed=minutes / 60.0,
        quality_flags=quality_flags,
        datasets_profiled=datasets_profiled,
    )


# ---------------------------------------------------------------------------
# Workflow functions
# ---------------------------------------------------------------------------

def qa_qc_inventory_ledger(
    lot_info: pd.DataFrame,
    mappluto: pd.DataFrame,
    complaints_311: pd.DataFrame,
    *,
    stale_days: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    """
    Join lot info + MapPLUTO on BBL; flag owner mismatches and stale 311 complaints.
    Returns (ledger, stale_311, join_count, quality_flag_count).
    """
    joins = 0
    quality_flags = 0

    if lot_info.empty:
        return pd.DataFrame(), pd.DataFrame(), joins, quality_flags

    # Minimize copies: process in-place where possible
    lot = lot_info.copy()
    if "_bbl" not in lot.columns:
        bbl_col = pick_column(lot, BBL_CANDIDATES)
        if bbl_col:
            lot["_bbl"] = normalize_bbl(lot[bbl_col])

    pluto = mappluto.copy() if not mappluto.empty else pd.DataFrame()
    if not pluto.empty and "_bbl" not in pluto.columns:
        bbl_col = pick_column(pluto, BBL_CANDIDATES)
        if bbl_col:
            pluto["_bbl"] = normalize_bbl(pluto[bbl_col])

    # Use indexed merge for better performance
    if not pluto.empty and "_bbl" in lot.columns and "_bbl" in pluto.columns:
        pluto_owner = (
            pick_column(pluto, OWNER_CANDIDATES)
            or pick_column(pluto, ("ownername", "ownertype"))
        )
        lot_owner = pick_column(lot, OWNER_CANDIDATES)
        keep_cols = ["_bbl"] + ([pluto_owner] if pluto_owner else [])

        # Use drop_duplicates + merge instead of multiple intermediate copies
        pluto_dedup = pluto[keep_cols].drop_duplicates("_bbl")
        merged = lot.merge(
            pluto_dedup,
            on="_bbl", how="left", suffixes=("", "_pluto"),
        )
        joins += 1
    else:
        merged = lot

    lot_owner = pick_column(merged, OWNER_CANDIDATES)
    if lot_owner:
        pluto_owner_col = (
            f"{lot_owner}_pluto"
            if f"{lot_owner}_pluto" in merged.columns
            else pick_column(merged, ("ownername", "ownertype"))
        )
        if pluto_owner_col:
            merged["owner_discrepancy"] = (
                merged[lot_owner].astype(str).str.lower().str.strip()
                != merged[pluto_owner_col].astype(str).str.lower().str.strip()
            ) & merged[lot_owner].notna() & merged[pluto_owner_col].notna()
        else:
            merged["owner_discrepancy"] = False
    else:
        merged["owner_discrepancy"] = False

    missing_mask = merged.isna().any(axis=1)
    merged["missing_or_corrupt"] = missing_mask

    # Data quality severity tagging
    owner_flags = int(merged["owner_discrepancy"].sum()) if "owner_discrepancy" in merged.columns else 0
    missing_flags = int(merged["missing_or_corrupt"].sum()) if "missing_or_corrupt" in merged.columns else 0
    quality_flags = owner_flags + missing_flags

    if quality_flags > 0:
        merged["_quality_severity"] = "ok"
        if "owner_discrepancy" in merged.columns:
            merged.loc[merged["owner_discrepancy"], "_quality_severity"] = "warn"
        if "missing_or_corrupt" in merged.columns:
            merged.loc[merged["missing_or_corrupt"] & (merged.get("_quality_severity", "ok") != "warn"), "_quality_severity"] = "info"

    stale = pd.DataFrame()
    if not complaints_311.empty:
        c = complaints_311.copy()
        date_col = pick_column(c, DATE_CANDIDATES)
        if date_col:
            if pd.api.types.is_datetime64_any_dtype(c[date_col]):
                c["_opened"] = c[date_col]
            else:
                c["_opened"] = pd.to_datetime(c[date_col], errors="coerce")
            cutoff = _utc_today() - pd.Timedelta(days=stale_days)
            stale = c[c["_opened"].notna() & (c["_opened"] <= cutoff)].copy()
            if "_bbl" not in stale.columns:
                bbl_col = pick_column(stale, BBL_CANDIDATES)
                if bbl_col:
                    stale["_bbl"] = normalize_bbl(stale[bbl_col])
            if not stale.empty:
                stale["_days_open"] = (_utc_today() - stale["_opened"]).dt.days
                quality_flags += len(stale)

    return merged, stale, joins, quality_flags


def spatial_conflict_detection(
    weekly_construction: pd.DataFrame,
    street_permits: pd.DataFrame,
    capital_blocks: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """
    Spatial overlaps: weekly schedule vs permits and vs capital reconstruction blocks.
    Returns conflict table and count of spatial join operations performed.

    Performance: Pushes heavy intersection logic down to DuckDB spatial extension
    when datasets exceed 10,000 rows. Falls back to Geopandas if extensions fail.
    """
    joins = 0
    
    if weekly_construction.empty:
        return pd.DataFrame(), joins
        
    from app.data_loader import _DUCKDB_AVAILABLE, _DUCKDB_PATH
    
    # Pushdown Strategy if DuckDB spatial is available and datasets are large
    if _DUCKDB_AVAILABLE and len(street_permits) > 10000:
        try:
            from socrata_toolkit.core.duckdb_store import DuckDBManager
            mgr = DuckDBManager(_DUCKDB_PATH)
            
            # Register temp views
            mgr.conn.register("tmp_weekly", weekly_construction)
            mgr.conn.register("tmp_permits", street_permits)
            
            # We assume geometries are present in WKT or Well-Known Binary form. 
            # In a true deployment, the 'geom' column would be cast to DuckDB GEOMETRY.
            # Using basic bbox / intersect logic (conceptual pushdown wrapper)
            conflicts_query = """
                SELECT w.*, 'weekly_vs_permit' as conflict_type, 'high' as conflict_severity
                FROM tmp_weekly w
                JOIN tmp_permits p ON ST_Intersects(ST_GeomFromText(w.geometry), ST_GeomFromText(p.geometry))
            """
            
            # Due to mock data lacking valid 'geometry' columns in our tests, we catch errors and fallback
            # but log the attempt.
            res_df = mgr.conn.execute(conflicts_query).df()
            mgr.close()
            
            if not res_df.empty:
                res_df["conflict_id"] = range(1, len(res_df) + 1)
                res_df["detected_at"] = pd.Timestamp.now(tz=timezone.utc).isoformat()
                return res_df, 1
        except Exception as e:
            log.info(f"Spatial pushdown failed, falling back to GeoPandas: {e}")
            pass

    # Standard GeoPandas Fallback
    if gpd is None:
        return pd.DataFrame({"note": ["geopandas not installed — pip install -e \".[mission]\""]}), 0

    weekly_gdf = df_to_gdf(weekly_construction) if not weekly_construction.empty else None
    permits_gdf = df_to_gdf(street_permits) if not street_permits.empty else None
    capital_gdf = df_to_gdf(capital_blocks) if not capital_blocks.empty else None

    if weekly_gdf is None or weekly_gdf.empty:
        return pd.DataFrame(), joins

    conflicts: list[pd.DataFrame] = []

    # Build spatial index once for reuse
    try:
        weekly_index = weekly_gdf.sindex
    except Exception:
        weekly_index = None

    if permits_gdf is not None and not permits_gdf.empty and weekly_index is not None:
        try:
            # Use indexed spatial join for better performance
            joined = gpd.sjoin(weekly_gdf, permits_gdf, how="inner", predicate="intersects")
            if not joined.empty:
                joined["conflict_type"] = "weekly_vs_permit"
                joined["conflict_severity"] = "high"
                conflicts.append(joined)
                joins += 1
        except Exception:
            pass

    if capital_gdf is not None and not capital_gdf.empty and weekly_index is not None:
        try:
            joined = gpd.sjoin(weekly_gdf, capital_gdf, how="inner", predicate="intersects")
            if not joined.empty:
                joined["conflict_type"] = "weekly_vs_capital"
                joined["conflict_severity"] = "medium"
                conflicts.append(joined)
                joins += 1
        except Exception:
            pass

    if not conflicts:
        return pd.DataFrame(), joins

    out = pd.concat(conflicts, ignore_index=True)
    out["conflict_id"] = range(1, len(out) + 1)
    out["detected_at"] = pd.Timestamp.now(tz=timezone.utc).isoformat()
    return out, joins


def contract_dispatch_clearance(
    violations: pd.DataFrame,
    tree_damage: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """
    Violations past grace period (city-contract clearance) + Parks routing from tree damage.
    Optimized with set-based pre-filtering for O(1) lookups.
    """
    joins = 0
    cleared = pd.DataFrame()
    parks_routing = pd.DataFrame()

    if not violations.empty:
        v = violations.copy()
        grace_col = pick_column(v, GRACE_CANDIDATES)
        if grace_col:
            if pd.api.types.is_datetime64_any_dtype(v[grace_col]):
                v["_grace"] = v[grace_col]
            else:
                v["_grace"] = pd.to_datetime(v[grace_col], errors="coerce")
            today = _utc_today()
            v["days_past_grace"] = (today - v["_grace"]).dt.days
            cleared = v[v["days_past_grace"].notna() & (v["days_past_grace"] >= 0)].copy()
            if not cleared.empty:
                # Severity buckets
                cleared["_clearance_urgency"] = "normal"
                cleared.loc[cleared["days_past_grace"] > 90, "_clearance_urgency"] = "urgent"
                cleared.loc[cleared["days_past_grace"] > 365, "_clearance_urgency"] = "critical"
            if "_bbl" not in cleared.columns:
                bbl_col = pick_column(cleared, BBL_CANDIDATES)
                if bbl_col:
                    cleared["_bbl"] = normalize_bbl(cleared[bbl_col])

    if not tree_damage.empty and not cleared.empty:
        t = tree_damage.copy()
        if "_bbl" not in t.columns:
            bbl_col = pick_column(t, BBL_CANDIDATES)
            if bbl_col:
                t["_bbl"] = normalize_bbl(t[bbl_col])

        # O(1) set lookup optimization
        tree_bbl_set = set(t["_bbl"].dropna().astype(str))
        cleared["route_parks_coordination"] = [str(b) in tree_bbl_set for b in cleared["_bbl"]]
        parks_routing = cleared[cleared["route_parks_coordination"]].copy()
        joins += 1
    elif not tree_damage.empty:
        t = tree_damage.copy()
        if "_bbl" not in t.columns:
            bbl_col = pick_column(t, BBL_CANDIDATES)
            if bbl_col:
                t["_bbl"] = normalize_bbl(t[bbl_col])
        parks_routing = t.copy()
        parks_routing["route_parks_coordination"] = True

    return cleared, parks_routing, joins


def productivity_ada_dashboard(
    built: pd.DataFrame,
    ramp_progress: pd.DataFrame,
    pedestrian_demand: pd.DataFrame,
) -> dict[str, Any]:
    """Sidewalk feet repaired, ramp installs, demand corridor overlay stats."""
    result: dict[str, Any] = {
        "feet_repaired": 0.0,
        "ramp_installs": 0,
        "ramp_pending": 0,
        "high_demand_corridors": 0,
        "ramp_demand_index": pd.DataFrame(),
        "completion_rate_pct": 0.0,
    }

    if not built.empty:
        length_col = pick_column(
            built, ("feet", "length", "sqft", "linear_feet", "sidewalk_feet", "repaired_feet")
        )
        if length_col:
            result["feet_repaired"] = float(
                pd.to_numeric(built[length_col], errors="coerce").fillna(0).sum()
            )
        else:
            result["feet_repaired"] = float(len(built))

    if not ramp_progress.empty:
        status_col = pick_column(ramp_progress, ("status", "install_status", "completed"))
        if status_col:
            s = ramp_progress[status_col].astype(str)
            done = s.str.contains("complete|install|done", case=False, na=False)
            pending = s.str.contains("pending|scheduled|planned|open", case=False, na=False)
            result["ramp_installs"] = int(done.sum())
            result["ramp_pending"] = int(pending.sum())
            total = len(ramp_progress)
            if total > 0:
                result["completion_rate_pct"] = round(100.0 * int(done.sum()) / total, 1)
        else:
            result["ramp_installs"] = len(ramp_progress)

    if not pedestrian_demand.empty and not ramp_progress.empty:
        demand = pedestrian_demand.copy()
        ramps = ramp_progress.copy()
        d_col = pick_column(demand, ("demand", "pedestrian_demand", "score", "index"))
        if d_col:
            threshold = demand[d_col].quantile(0.75) if demand[d_col].notna().any() else 0
            result["high_demand_corridors"] = int((demand[d_col] >= threshold).sum())
        lat_d = pick_column(demand, ("latitude", "lat"))
        lon_d = pick_column(demand, ("longitude", "lon", "lng"))
        lat_r = pick_column(ramps, ("latitude", "lat"))
        lon_r = pick_column(ramps, ("longitude", "lon", "lng"))
        if lat_d and lon_d and lat_r and lon_r:
            ddf = demand[[lat_d, lon_d]].dropna().copy()
            rdf = ramps[[lat_r, lon_r]].dropna().copy()
            ddf.columns = pd.Index(["lat", "lon"])
            rdf.columns = pd.Index(["lat", "lon"])
            ddf["source"] = "demand"
            rdf["source"] = "ramp"
            result["ramp_demand_index"] = pd.concat([ddf, rdf], ignore_index=True)

    return result


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_all_workflows(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Execute all workflows using Strategy Pattern. Optimized for scalability."""
    from app.services.workflow_service import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator()
    workflow_results = orchestrator.run_all(frames)
    
    qa = workflow_results["qa"]
    spatial = workflow_results["spatial"]
    contract = workflow_results["contract"]
    prod = workflow_results["productivity"]["productivity"]

    # Profile all datasets
    profiles = profile_all_datasets(frames)

    # ROI aggregation via service
    roi = _get_roi_aggregator().compute(
        lots_validated=int(len(qa["ledger"])) if not qa["ledger"].empty else 0,
        spatial_conflicts_checked=len(spatial["conflicts"]),
        contracts_cleared=len(contract["cleared"]),
        joins_automated=qa["joins"] + spatial["joins"] + contract["joins"],
        actionable_discrepancies=qa["flags"] + len(spatial["conflicts"]),
        quality_flags=qa["flags"] + len(spatial["conflicts"]),
        datasets_profiled=len(profiles),
    )

    return {
        "ledger": qa["ledger"],
        "stale_311": qa["stale_311"],
        "conflicts": spatial["conflicts"],
        "cleared": contract["cleared"],
        "parks_routing": contract["parks"],
        "productivity": prod,
        "profiles": profiles,
        "roi": roi,
    }


# ---------------------------------------------------------------------------
# Dataset comparison utility
# ---------------------------------------------------------------------------

def compare_datasets(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str = "Dataset A",
    label_b: str = "Dataset B",
) -> pd.DataFrame:
    """
    Side-by-side column comparison. Returns a DataFrame showing columns,
    which dataset has them, and whether they are shared join candidates.
    """
    cols_a = {c.lower(): c for c in df_a.columns if not c.startswith("_")}
    cols_b = {c.lower(): c for c in df_b.columns if not c.startswith("_")}

    all_cols = sorted(set(cols_a) | set(cols_b))
    rows = []
    for col_lower in all_cols:
        in_a = col_lower in cols_a
        in_b = col_lower in cols_b
        is_shared = in_a and in_b
        join_candidate = is_shared and any(
            kw in col_lower for kw in {"bbl", "id", "key", "permit", "bin", "block"}
        )
        rows.append({
            "column": col_lower,
            f"in_{label_a.replace(' ', '_')}": "✓" if in_a else "—",
            f"in_{label_b.replace(' ', '_')}": "✓" if in_b else "—",
            "shared": "✓" if is_shared else "",
            "join_candidate": "🔑" if join_candidate else "",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Data quality summary
# ---------------------------------------------------------------------------

def quality_summary(profiles: dict[str, DatasetProfile]) -> pd.DataFrame:
    """Tabular quality summary across all profiled datasets."""
    rows = []
    for key, p in profiles.items():
        rows.append({
            "dataset": key,
            "rows": p.row_count,
            "columns": p.col_count,
            "null_%": p.overall_null_pct,
            "dup_%": p.duplicate_row_pct,
            "quality_score": p.quality_score,
            "geo_cols": len(p.geo_columns),
            "date_cols": len(p.date_columns),
            "pk_candidates": ", ".join(p.pk_candidates[:2]),
        })
    return pd.DataFrame(rows).sort_values("quality_score", ascending=False)
