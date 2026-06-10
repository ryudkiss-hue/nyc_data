"""Pre-computed analytics views and marts.

These views are materialized in the analytics schema and serve
as the source for Dash dashboards and analysis methods.

Each function creates or refreshes an analytics view designed for a specific use case.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def create_borough_summary(conn) -> Dict:
    """Borough-level KPI aggregation.

    Creates a view with per-borough inspection statistics, violation counts,
    completion rates, and SLA metrics.

    Args:
        conn: DuckDB connection

    Returns:
        Status dict
    """
    logger.info("Creating borough_summary analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.borough_summary CASCADE")

        conn.execute("""
            CREATE VIEW analytics.borough_summary AS
            SELECT
                UPPER(borough) as borough,
                COUNT(DISTINCT objectid) as inspection_count,
                AVG(condition_score) as avg_condition_score,
                SUM(violation_count) as total_violations,
                COUNT(CASE WHEN condition_score >= 80 THEN 1 END) as good_condition_count,
                ROUND(100.0 * COUNT(CASE WHEN condition_score >= 80 THEN 1 END) /
                    NULLIF(COUNT(*), 0), 2) as pct_good_condition,
                MAX(staged_at) as last_updated
            FROM staging.inspections
            GROUP BY UPPER(borough)
        """)

        return {"status": "success", "view": "analytics.borough_summary"}
    except Exception as e:
        logger.error(f"Failed to create borough_summary: {e}")
        return {"status": "error", "error": str(e)}


def create_time_series_snapshots(conn) -> Dict:
    """Time-series data for temporal analysis.

    Creates a monthly snapshot view with trend detection,
    seasonality, and year-over-year comparisons.

    Args:
        conn: DuckDB connection

    Returns:
        Status dict
    """
    logger.info("Creating time_series_snapshots analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.time_series_snapshots CASCADE")

        conn.execute("""
            CREATE VIEW analytics.time_series_snapshots AS
            SELECT
                DATE_TRUNC('month', inspection_date)::DATE as month,
                UPPER(borough) as borough,
                COUNT(DISTINCT objectid) as inspection_count,
                AVG(condition_score) as avg_condition_score,
                SUM(violation_count) as total_violations,
                LAG(COUNT(DISTINCT objectid)) OVER (
                    PARTITION BY UPPER(borough) ORDER BY DATE_TRUNC('month', inspection_date)
                ) as prev_month_count
            FROM staging.inspections
            WHERE inspection_date IS NOT NULL
            GROUP BY DATE_TRUNC('month', inspection_date), UPPER(borough)
            ORDER BY month DESC, borough
        """)

        return {"status": "success", "view": "analytics.time_series_snapshots"}
    except Exception as e:
        logger.error(f"Failed to create time_series_snapshots: {e}")
        return {"status": "error", "error": str(e)}


def create_material_analysis_mart(conn) -> Dict:
    """Material-specific failure rates and economics.

    Creates a mart with material type, failure curves,
    lifecycle costs, and maintenance recommendations.

    Args:
        conn: DuckDB connection

    Returns:
        Status dict
    """
    logger.info("Creating material_analysis_mart analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.material_analysis_mart CASCADE")

        conn.execute("""
            CREATE VIEW analytics.material_analysis_mart AS
            SELECT
                material_type,
                COUNT(*) as total_inspections,
                AVG(condition_score) as avg_condition_score,
                MIN(condition_score) as min_condition_score,
                MAX(condition_score) as max_condition_score,
                SUM(violation_count) as total_violations,
                AVG(violation_count) as avg_violations_per_inspection,
                COUNT(CASE WHEN condition_score < 60 THEN 1 END) as poor_condition_count,
                ROUND(100.0 * COUNT(CASE WHEN condition_score < 60 THEN 1 END) /
                    NULLIF(COUNT(*), 0), 2) as pct_poor_condition
            FROM staging.inspections
            WHERE material_type IS NOT NULL
            GROUP BY material_type
            ORDER BY pct_poor_condition DESC
        """)

        return {"status": "success", "view": "analytics.material_analysis_mart"}
    except Exception as e:
        logger.error(f"Failed to create material_analysis_mart: {e}")
        return {"status": "error", "error": str(e)}


def create_clustering_features(conn) -> Dict:
    """Pre-computed features for clustering analysis.

    Creates a feature matrix with inspection history, cost, condition,
    location, and material type for unsupervised clustering.

    Args:
        conn: DuckDB connection

    Returns:
        Status dict
    """
    logger.info("Creating clustering_features analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.clustering_features CASCADE")

        conn.execute("""
            CREATE VIEW analytics.clustering_features AS
            SELECT
                objectid,
                condition_score,
                violation_count,
                CASE WHEN violation_count = 0 THEN 0 ELSE 1 END as has_violations,
                CASE WHEN material_type IN ('concrete', 'asphalt') THEN 1 ELSE 0 END as is_standard_material,
                latitude,
                longitude,
                SQRT(POWER(latitude - 40.7128, 2) + POWER(longitude - (-74.0060), 2)) as distance_from_center,
                material_type,
                inspection_date
            FROM staging.inspections
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)

        return {"status": "success", "view": "analytics.clustering_features"}
    except Exception as e:
        logger.error(f"Failed to create clustering_features: {e}")
        return {"status": "error", "error": str(e)}


def create_geo_animation_mart(conn) -> Dict:
    """Pre-aggregated geospatial temporal animation data.

    Creates a mart with monthly condition scores by community board
    for animated borough-level heatmaps and hot-spot tracking.

    Args:
        conn: DuckDB connection

    Returns:
        Status dict
    """
    logger.info("Creating geo_animation_mart analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.geo_animation_mart CASCADE")

        conn.execute("""
            CREATE VIEW analytics.geo_animation_mart AS
            SELECT
                DATE_TRUNC('month', inspection_date)::DATE as month,
                UPPER(borough) as borough,
                ROUND(AVG(condition_score), 2) as avg_condition_score,
                COUNT(DISTINCT objectid) as inspection_count,
                COUNT(CASE WHEN violation_count > 0 THEN 1 END) as inspection_with_violations,
                ROW_NUMBER() OVER (
                    PARTITION BY DATE_TRUNC('month', inspection_date)
                    ORDER BY COUNT(DISTINCT objectid) DESC
                ) as borough_rank
            FROM staging.inspections
            WHERE inspection_date IS NOT NULL
            GROUP BY DATE_TRUNC('month', inspection_date), UPPER(borough)
            ORDER BY month DESC, borough_rank
        """)

        return {"status": "success", "view": "analytics.geo_animation_mart"}
    except Exception as e:
        logger.error(f"Failed to create geo_animation_mart: {e}")
        return {"status": "error", "error": str(e)}


def refresh_all_analytics_views(conn) -> Dict:
    """Refresh all analytics views.

    Args:
        conn: DuckDB connection

    Returns:
        Summary of refresh results
    """
    logger.info("Refreshing all analytics views...")
    results = {
        "borough_summary": create_borough_summary(conn),
        "time_series_snapshots": create_time_series_snapshots(conn),
        "material_analysis_mart": create_material_analysis_mart(conn),
        "clustering_features": create_clustering_features(conn),
        "geo_animation_mart": create_geo_animation_mart(conn)
    }

    success_count = sum(1 for r in results.values() if r.get("status") == "success")
    logger.info(f"Refreshed {success_count}/{len(results)} analytics views")

    return results