"""
MotherDuck Service Layer: Bridge between Dash callbacks and MotherDuck views.

Provides high-level functions to fetch data from serving views:
- fetch_phase_b_results() → v_phase_b_results (spatial clustering)
- fetch_phase_c_results() → v_phase_c_results (distributions)
- fetch_phase_d_results() → v_phase_d_results (anomalies)
- fetch_phase_e_decomposition() → v_phase_e_decomposition (time series)
- fetch_phase_f_bootstrap_ci() → v_phase_f_bootstrap_ci (SLA forecast)
- fetch_metric_data() → v_metric_dashboard (18 Metrics)

All functions apply global filters (boroughs, date_range, metric_type) before querying.

Usage:
    from app.services.motherduck_service import fetch_phase_c_results
    df = fetch_phase_c_results({"boroughs": ["MN", "BK"], "date_start": "2026-05-01"})
"""

import logging
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

def get_motherduck_connection():
    """
    Get or create MotherDuck connection.

    Returns:
        MotherDuckConnection: Active connection to MotherDuck

    Raises:
        RuntimeError: If connection cannot be established
    """
    try:
        import os

        from socrata_toolkit.motherduck.connector import MotherDuckConnection

        # Determine the absolute path to the local duckdb file
        db_path = os.getenv("DUCKDB_PATH")
        if not db_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(project_root, "data", "local_db", "nyc_mission_control.duckdb")

        # Ignore MotherDuck token to force local fallback
        return MotherDuckConnection(token="", database_path=db_path)
    except Exception as e:
        logger.error(f"Failed to establish MotherDuck connection: {e}")
        raise RuntimeError(f"MotherDuck connection failed: {e}")

def _apply_filters(query: str, filters: dict[str, Any]) -> str:
    """
    Apply global filters to a query.

    Args:
        query: Base SQL query
        filters: Filter dict with keys: boroughs, date_start, date_end, metric_type

    Returns:
        str: Query with WHERE clause appended
    """
    where_clauses = []

    # Borough filter
    if filters.get("boroughs"):
        boroughs = filters["boroughs"]
        if isinstance(boroughs, str):
            boroughs = [boroughs]
        borough_str = ",".join(f"'{b}'" for b in boroughs)
        where_clauses.append(f"(borough IN ({borough_str}) OR borough = 'ALL')")

    # Date range filter
    if filters.get("date_start"):
        where_clauses.append(f"created_date >= '{filters['date_start']}'")
    if filters.get("date_end"):
        where_clauses.append(f"created_date <= '{filters['date_end']}'")

    # Metric type filter (application-specific)
    metric_type = filters.get("metric_type", "all")
    if metric_type == "critical":
        where_clauses.append("severity = 'HIGH'")
    elif metric_type == "active":
        where_clauses.append("status IN ('OPEN', 'IN_PROGRESS')")
    elif metric_type == "completed":
        where_clauses.append("status = 'CLOSED'")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    return query

def fetch_phase_b_results(filters: dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Fetch Phase B results (Moran's I spatial clustering).

    Args:
        filters: Global filter state

    Returns:
        pd.DataFrame: Phase B results from v_phase_b_results with filters applied
                     Columns: borough, morans_i, significance, cluster_count, ...

    Example:
        df = fetch_phase_b_results({"boroughs": ["MN"], "date_start": "2026-05-01"})
        print(df[["borough", "morans_i", "significance"]])
    """
    try:
        conn = get_motherduck_connection()
        query = "SELECT * FROM app_queries.v_phase_b_results"
        query = _apply_filters(query, filters)
        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} Phase B results")
        return df
    except Exception as e:
        logger.error(f"Error fetching Phase B results: {e}")
        return None

def fetch_phase_c_results(filters: dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Fetch Phase C results (Distribution classification).

    Args:
        filters: Global filter state

    Returns:
        pd.DataFrame: Phase C results from v_phase_c_results
                     Columns: borough, distribution_type, skewness, concentration_pct, ...
    """
    try:
        conn = get_motherduck_connection()
        query = "SELECT * FROM app_queries.v_phase_c_results"
        query = _apply_filters(query, filters)
        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} Phase C results")
        return df
    except Exception as e:
        logger.error(f"Error fetching Phase C results: {e}")
        return None

def fetch_phase_d_results(filters: dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Fetch Phase D results (Anomaly detection/geographic).

    Args:
        filters: Global filter state

    Returns:
        pd.DataFrame: Phase D results from v_phase_d_results
                     Columns: location_id, borough, outlier_type, severity, priority, ...
    """
    try:
        conn = get_motherduck_connection()
        query = "SELECT * FROM app_queries.v_phase_d_results"
        query = _apply_filters(query, filters)
        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} Phase D results")
        return df
    except Exception as e:
        logger.error(f"Error fetching Phase D results: {e}")
        return None

def fetch_phase_e_decomposition(filters: dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Fetch Phase E results (Time series decomposition).

    Args:
        filters: Global filter state

    Returns:
        pd.DataFrame: Phase E decomposition from v_phase_e_decomposition
                     Columns: period, trend, seasonal, residual, forecast, ...
    """
    try:
        conn = get_motherduck_connection()
        query = "SELECT * FROM app_queries.v_phase_e_decomposition"
        query = _apply_filters(query, filters)
        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} Phase E decomposition rows")
        return df
    except Exception as e:
        logger.error(f"Error fetching Phase E decomposition: {e}")
        return None

def fetch_phase_f_bootstrap_ci(filters: dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Fetch Phase F results (Bootstrap CI / SLA forecast).

    Args:
        filters: Global filter state

    Returns:
        pd.DataFrame: Phase F bootstrap CI from v_phase_f_bootstrap_ci
                     Columns: borough, point_estimate, ci_lower, ci_upper,
                              prob_meets_sla, risk_level, ...
    """
    try:
        conn = get_motherduck_connection()
        query = "SELECT * FROM app_queries.v_phase_f_bootstrap_ci"
        query = _apply_filters(query, filters)
        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} Phase F bootstrap CI results")
        return df
    except Exception as e:
        logger.error(f"Error fetching Phase F bootstrap CI: {e}")
        return None

def fetch_metric_data(filters: dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Fetch Metric data for dashboard cards.

    Args:
        filters: Global filter state

    Returns:
        pd.DataFrame: Metric data from v_metric_dashboard (18 Metrics × 5 boroughs = 90 rows)
                     Columns: metric_id, metric_name, borough, value, change_pct, ...

    Expected structure:
        metric_id | metric_name | borough | value | change_pct | category
        --------- | ----------- | ------- | ----- | ---------- | --------
        total_inspections | Total Inspections | MN | 2500 | +5.2 | Inspection Performance
        data_completeness | Data Completeness | MN | 98.5 | +0.3 | Quality Metrics
        ramp_completion_rate | Ramp Completion | MN | 75.0 | +2.1 | Ramp Accessibility
        morans_i_statistic | Moran's I | MN | 0.342 | -0.02 | Spatial Patterns
        ...
    """
    try:
        conn = get_motherduck_connection()
        query = "SELECT * FROM app_queries.v_metric_dashboard"
        query = _apply_filters(query, filters)
        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} Metric records")
        return df
    except Exception as e:
        logger.error(f"Error fetching Metric data: {e}")
        return None

def fetch_dataset(filters: dict[str, Any], dataset_key: str = "inspection") -> Optional[pd.DataFrame]:
    """
    Fetch raw data for analytics.

    Args:
        filters: Global filter state
        dataset_key: Dataset key (inspection, spatial, timeseries, violations)

    Returns:
        pd.DataFrame: Raw data with filters applied
    """
    try:
        conn = get_motherduck_connection()

        # Map dataset keys to tables
        table_map = {
            "inspection": "raw.inspection_raw",
            "spatial": "raw.spatial_raw",
            "timeseries": "raw.timeseries_raw",
            "violations": "raw.violations_raw",
        }

        table = table_map.get(dataset_key, table_map["inspection"])
        query = f"SELECT * FROM {table}"
        query = _apply_filters(query, filters)

        df = conn.execute(query).df()
        logger.info(f"Fetched {len(df)} records from {dataset_key}")
        return df

    except Exception as e:
        logger.error(f"Error fetching {dataset_key} dataset: {e}")
        return None

def validate_connection() -> bool:
    """
    Validate MotherDuck connection and serving views.

    Returns:
        bool: True if connection is active and all views exist
    """
    try:
        conn = get_motherduck_connection()

        views = [
            "app_queries.v_phase_b_results",
            "app_queries.v_phase_c_results",
            "app_queries.v_phase_d_results",
            "app_queries.v_phase_e_decomposition",
            "app_queries.v_phase_f_bootstrap_ci",
            "app_queries.v_metric_dashboard",
        ]

        for view in views:
            try:
                result = conn.execute(f"SELECT COUNT(*) as cnt FROM {view}")
                count = result.df()["cnt"].iloc[0]
                logger.info(f"View {view} exists with {count} rows")
            except Exception as e:
                logger.warning(f"View {view} not accessible: {e}")
                return False

        logger.info("All MotherDuck views validated successfully")
        return True

    except Exception as e:
        logger.error(f"Connection validation failed: {e}")
        return False
