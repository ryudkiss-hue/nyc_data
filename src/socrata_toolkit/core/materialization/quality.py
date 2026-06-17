"""Mart quality tracking: freshness, completeness, schema stability."""
import json
import logging
from datetime import datetime

import duckdb

logger = logging.getLogger(__name__)

class MartQuality:
    """Track and score mart quality across multiple dimensions."""

    def __init__(self):
        self.quality_table = "analytics._mart_quality"

    def _ensure_table(self, conn: duckdb.DuckDBPyConnection):
        """Create quality metrics table if not exists."""
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.quality_table} (
                mart_name VARCHAR,
                row_count INTEGER,
                expected_row_count_min INTEGER,
                expected_row_count_max INTEGER,
                schema_hash VARCHAR,
                materialized_at TIMESTAMP,
                freshness_score FLOAT,
                completeness_score FLOAT,
                stability_score FLOAT,
                overall_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    def track_metrics(
        self,
        mart_name: str,
        row_count: int,
        schema: dict,
        materialized_at: str,
        expected_row_count_min: int = None,
        expected_row_count_max: int = None,
        conn: duckdb.DuckDBPyConnection = None,
    ):
        """Track quality metrics for a mart."""
        if conn is None:
            return

        self._ensure_table(conn)

        # Compute schema hash
        schema_hash = hash(json.dumps(schema, sort_keys=True))

        try:
            conn.execute(
                f"""
                INSERT INTO {self.quality_table}
                (mart_name, row_count, expected_row_count_min, expected_row_count_max, schema_hash, materialized_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    mart_name,
                    row_count,
                    expected_row_count_min,
                    expected_row_count_max,
                    str(schema_hash),
                    materialized_at,
                ],
            )
            logger.info(f"Tracked quality metrics for {mart_name}")
        except Exception as e:
            logger.error(f"Failed to track metrics for {mart_name}: {e}")

    def compute_quality_score(self, mart_name: str, conn: duckdb.DuckDBPyConnection) -> float:
        """Compute 0-100 quality score based on:
        - Freshness (40%): Materialized <24h ago
        - Completeness (35%): Row count in expected range
        - Stability (25%): No unexpected schema changes
        """
        try:
            result = conn.execute(
                f"""
                SELECT
                  row_count,
                  expected_row_count_min,
                  expected_row_count_max,
                  materialized_at,
                  schema_hash
                FROM {self.quality_table}
                WHERE mart_name = ?
                ORDER BY materialized_at DESC
                LIMIT 2
                """,
                [mart_name],
            ).fetchall()

            if not result or len(result) < 1:
                return 0.0

            current = result[0]
            row_count = current[0]
            expected_min = current[1]
            expected_max = current[2]
            materialized_at = current[3]
            schema_hash = current[4]

            # Freshness score (40%)
            if materialized_at:
                mat_time = datetime.fromisoformat(str(materialized_at))
                age_hours = (datetime.now() - mat_time).total_seconds() / 3600
                freshness = max(0, 100 - (age_hours / 24 * 100))  # 100 if <24h, 0 if >24h
            else:
                freshness = 0

            # Completeness score (35%)
            if expected_min and expected_max:
                if expected_min <= row_count <= expected_max:
                    completeness = 100
                else:
                    # Score based on how far from expected range
                    if row_count < expected_min:
                        deviation = (expected_min - row_count) / expected_min
                    else:
                        deviation = (row_count - expected_max) / expected_max
                    completeness = max(0, 100 - (deviation * 100))
            else:
                completeness = 100  # No expected range; assume OK

            # Stability score (25%)
            if len(result) >= 2:
                previous = result[1]
                previous_schema = previous[4]
                stability = 100 if schema_hash == previous_schema else 50
            else:
                stability = 100  # First run; assume stable

            # Weighted score
            overall = (freshness * 0.40) + (completeness * 0.35) + (stability * 0.25)
            return round(overall, 1)
        except Exception as e:
            logger.error(f"Failed to compute quality score for {mart_name}: {e}")
            return 0.0

    def detect_drift(
        self, mart_name: str, threshold_pct: float = 20, conn: duckdb.DuckDBPyConnection = None
    ) -> dict:
        """Detect schema drift or row count anomalies.

        Returns:
            {"drift_detected": bool, "issues": [...]}
        """
        if conn is None:
            return {"drift_detected": False, "issues": []}

        try:
            result = conn.execute(
                f"""
                SELECT
                  row_count,
                  schema_hash,
                  LAG(row_count) OVER (ORDER BY materialized_at DESC) as prev_row_count,
                  LAG(schema_hash) OVER (ORDER BY materialized_at DESC) as prev_schema
                FROM {self.quality_table}
                WHERE mart_name = ?
                ORDER BY materialized_at DESC
                LIMIT 2
                """,
                [mart_name],
            ).fetchall()

            issues = []

            if result and len(result) >= 1:
                current = result[0]
                row_count = current[0]

                # Check for schema drift
                if len(result) >= 2 and current[1] != current[3]:
                    issues.append("Schema changed since last materialization")

                # Check for row count anomaly
                if len(result) >= 2 and current[2]:
                    prev_count = current[2]
                    pct_change = abs(row_count - prev_count) / prev_count * 100
                    if pct_change > threshold_pct:
                        issues.append(
                            f"Row count changed by {pct_change:.1f}% (threshold: {threshold_pct}%)"
                        )

            return {"drift_detected": len(issues) > 0, "issues": issues}
        except Exception as e:
            logger.error(f"Failed to detect drift for {mart_name}: {e}")
            return {"drift_detected": False, "issues": [str(e)]}
