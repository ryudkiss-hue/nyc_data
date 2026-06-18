"""KPI materialization database schema and operations.

Manages DuckDB analytics schema for KPI materialization:
- kpi_time_series: Monthly KPI snapshots
- kpi_forecasts: 3-month ahead predictions
- kpi_anomalies: Anomaly detection flags
- kpi_latest: Current status snapshot
"""

from typing import Optional, List
from datetime import datetime, date, timezone
import logging

logger = logging.getLogger(__name__)


def initialize_analytics_schema(conn):
    """Create KPI analytics tables if missing."""

    # Time-series table: monthly snapshots
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics.kpi_time_series (
            kpi_id VARCHAR NOT NULL,
            period DATE NOT NULL,
            borough VARCHAR,
            current_value DOUBLE,
            target DOUBLE,
            achievement_pct DOUBLE,
            materialized_at TIMESTAMP,
            PRIMARY KEY (kpi_id, period, borough)
        )
    """)

    # Forecasts table: 3 months ahead
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics.kpi_forecasts (
            kpi_id VARCHAR NOT NULL,
            forecast_period DATE NOT NULL,
            forecast_value DOUBLE,
            forecast_ci_lower DOUBLE,
            forecast_ci_upper DOUBLE,
            forecast_confidence DOUBLE,
            forecast_method VARCHAR,
            forecast_computed_at TIMESTAMP,
            PRIMARY KEY (kpi_id, forecast_period)
        )
    """)

    # Anomalies table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics.kpi_anomalies (
            kpi_id VARCHAR NOT NULL,
            period DATE NOT NULL,
            observed_value DOUBLE,
            expected_value DOUBLE,
            z_score DOUBLE,
            is_anomaly BOOLEAN,
            anomaly_severity VARCHAR,
            detected_at TIMESTAMP,
            PRIMARY KEY (kpi_id, period)
        )
    """)

    # Latest status snapshot
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics.kpi_latest (
            kpi_id VARCHAR PRIMARY KEY,
            period DATE,
            current_value DOUBLE,
            target DOUBLE,
            status VARCHAR,
            computed_at TIMESTAMP
        )
    """)

    # Create indices for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_ts_period ON analytics.kpi_time_series(kpi_id, period)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_forecast_kpi ON analytics.kpi_forecasts(kpi_id, forecast_period)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_kpi ON analytics.kpi_anomalies(kpi_id, period)")

    logger.info("Analytics schema initialized with 4 KPI tables")


def upsert_kpi_time_series(conn, kpi_id: str, period: date, borough: Optional[str],
                           current_value: float, target: float):
    """Idempotent upsert into kpi_time_series."""

    achievement = (current_value / target * 100.0) if target > 0 else 0.0
    now = datetime.now(timezone.utc)

    conn.execute("""
        INSERT INTO analytics.kpi_time_series
        (kpi_id, period, borough, current_value, target, achievement_pct, materialized_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO UPDATE SET
            current_value = EXCLUDED.current_value,
            achievement_pct = EXCLUDED.achievement_pct,
            materialized_at = EXCLUDED.materialized_at
    """, [kpi_id, period, borough, current_value, target, achievement, now])


def upsert_forecast(conn, kpi_id: str, forecast_period: date,
                   forecast_value: float, ci_lower: float, ci_upper: float,
                   confidence: float, method: str):
    """Batch insert forecast."""

    now = datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO analytics.kpi_forecasts
        (kpi_id, forecast_period, forecast_value, forecast_ci_lower,
         forecast_ci_upper, forecast_confidence, forecast_method, forecast_computed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO UPDATE SET
            forecast_value = EXCLUDED.forecast_value,
            forecast_ci_lower = EXCLUDED.forecast_ci_lower,
            forecast_ci_upper = EXCLUDED.forecast_ci_upper
    """, [kpi_id, forecast_period, forecast_value, ci_lower, ci_upper, confidence, method, now])


def upsert_anomaly(conn, kpi_id: str, period: date,
                  observed: float, expected: float, z_score: float,
                  is_anomaly: bool, severity: str):
    """Insert anomaly detection result."""

    now = datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO analytics.kpi_anomalies
        (kpi_id, period, observed_value, expected_value, z_score,
         is_anomaly, anomaly_severity, detected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT DO UPDATE SET
            z_score = EXCLUDED.z_score,
            is_anomaly = EXCLUDED.is_anomaly,
            anomaly_severity = EXCLUDED.anomaly_severity
    """, [kpi_id, period, observed, expected, z_score, is_anomaly, severity, now])


def upsert_kpi_latest(conn, kpi_id: str, period: date, current: float,
                     target: float, status: str):
    """Update latest status snapshot."""

    now = datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO analytics.kpi_latest
        (kpi_id, period, current_value, target, status, computed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (kpi_id) DO UPDATE SET
            period = EXCLUDED.period,
            current_value = EXCLUDED.current_value,
            status = EXCLUDED.status,
            computed_at = EXCLUDED.computed_at
    """, [kpi_id, period, current, target, status, now])


def get_kpi_time_series(conn, kpi_id: str, months_back: int = 12) -> List[dict]:
    """Fetch historical KPI values for forecasting."""

    result = conn.execute("""
        SELECT period, current_value FROM analytics.kpi_time_series
        WHERE kpi_id = ? AND borough IS NULL
        ORDER BY period DESC
        LIMIT ?
    """, [kpi_id, months_back]).fetchall()

    return [{"period": r[0], "value": r[1]} for r in result]


def vacuum_analytics_schema(conn):
    """Optimize analytics tables."""
    for table in ['kpi_time_series', 'kpi_forecasts', 'kpi_anomalies', 'kpi_latest']:
        conn.execute(f"VACUUM ANALYZE analytics.{table}")
    logger.info("Analytics schema vacuumed and analyzed")
