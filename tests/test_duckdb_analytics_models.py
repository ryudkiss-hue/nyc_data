"""Tests for the analytics marts (Task 4)."""

from unittest.mock import patch

import pandas as pd
import pytest

import socrata_toolkit.core.duckdb_analytics_models as am
import socrata_toolkit.core.duckdb_pipeline as dp

ALL_CREATE_FUNCS = [
    am.create_borough_summary,
    am.create_time_series_snapshots,
    am.create_material_analysis_mart,
    am.create_clustering_features,
    am.create_geo_animation_mart,
]

@pytest.fixture
def db(tmp_path):
    """Isolated DuckDB database per test; resets module-level singleton."""
    db_path = str(tmp_path / "test_analytics.duckdb")
    conn = dp.get_duckdb_connection(db_path)
    dp.initialize_database()
    yield conn
    dp.reset_connection()

def _stage(conn, df, name="inspections"):
    conn.register("_fixture_df", df)
    conn.execute(f"CREATE OR REPLACE TABLE staging.{name} AS SELECT * FROM _fixture_df")
    conn.unregister("_fixture_df")

def _inspections_df(**overrides):
    base = {
        "objectid": [1, 2, 3, 4, 5],
        "borough": ["MANHATTAN", "Manhattan", "BROOKLYN", "BROOKLYN", "QUEENS"],
        "created_date": [
            "2026-01-15",
            "2026-01-20",
            "2026-02-10",
            "2026-02-11",
            "2026-03-05",
        ],
        "violation_count": [2, 0, 1, 3, 0],
        "material_type": ["concrete", "concrete", "asphalt", "concrete", "asphalt"],
        "latitude": [40.71, 40.72, 40.65, 40.66, 40.74],
        "longitude": [-74.00, -73.99, -73.95, -73.94, -73.80],
    }
    base.update(overrides)
    return pd.DataFrame(base)

@pytest.fixture
def staged(db):
    _stage(db, _inspections_df())
    return db

def test_borough_summary_aggregates(staged):
    result = am.create_borough_summary()
    assert result["status"] == "success"
    assert result["table"] == "analytics.borough_summary"
    assert result["row_count"] == 3
    rows = dict(
        staged.execute(
            "SELECT borough, record_count FROM analytics.borough_summary"
        ).fetchall()
    )
    assert rows == {"MANHATTAN": 2, "BROOKLYN": 2, "QUEENS": 1}
    violations = dict(
        staged.execute(
            "SELECT borough, total_violations FROM analytics.borough_summary"
        ).fetchall()
    )
    assert violations == {"MANHATTAN": 2, "BROOKLYN": 4, "QUEENS": 0}

def test_borough_summary_missing_borough_column_errors(db):
    _stage(db, _inspections_df().drop(columns=["borough"]))
    result = am.create_borough_summary()
    assert result["status"] == "error"
    assert "borough" in result["error"]

def test_time_series_snapshots_month_buckets(staged):
    result = am.create_time_series_snapshots()
    assert result["status"] == "success"
    assert result["row_count"] == 3
    months = [
        str(r[0])[:10]
        for r in staged.execute(
            "SELECT month FROM analytics.time_series_snapshots ORDER BY month"
        ).fetchall()
    ]
    assert months == ["2026-01-01", "2026-02-01", "2026-03-01"]

def test_material_analysis_mart_with_material(staged):
    result = am.create_material_analysis_mart()
    assert result["status"] == "success"
    assert result["row_count"] == 2
    rows = dict(
        staged.execute(
            "SELECT material, record_count FROM analytics.material_analysis_mart"
        ).fetchall()
    )
    assert rows == {"concrete": 3, "asphalt": 2}

def test_material_analysis_mart_without_material(db):
    _stage(db, _inspections_df().drop(columns=["material_type"]))
    result = am.create_material_analysis_mart()
    assert result["status"] == "success"
    assert result["row_count"] == 0
    assert "no material column" in result["note"]
    count = db.execute(
        "SELECT COUNT(*) FROM analytics.material_analysis_mart"
    ).fetchone()[0]
    assert count == 0

def test_clustering_features_numeric_matrix(staged):
    result = am.create_clustering_features()
    assert result["status"] == "success"
    assert result["row_count"] == 5
    row = staged.execute(
        "SELECT violation_count, has_violations, latitude, longitude "
        "FROM analytics.clustering_features WHERE record_id = 1"
    ).fetchone()
    assert row == (2, 1, 40.71, -74.00)
    total = staged.execute(
        "SELECT SUM(violation_count) FROM analytics.clustering_features"
    ).fetchone()[0]
    assert total == 6

def test_clustering_features_geom_only_defers_extraction(db):
    df = _inspections_df().drop(columns=["latitude", "longitude"])
    df["the_geom"] = ["POINT (-73.98 40.75)"] * 5
    _stage(db, df)
    result = am.create_clustering_features()
    assert result["status"] == "success"
    assert "deferred" in result["note"]
    cols = {
        r[0]
        for r in db.execute("DESCRIBE analytics.clustering_features").fetchall()
    }
    assert "geom" in cols
    assert "latitude" not in cols

def test_geo_animation_mart_with_lat_lon(staged):
    result = am.create_geo_animation_mart()
    assert result["status"] == "success"
    assert result["row_count"] == 3
    row = staged.execute(
        "SELECT avg_latitude, record_count FROM analytics.geo_animation_mart "
        "WHERE borough = 'BROOKLYN'"
    ).fetchone()
    assert row[0] == pytest.approx(40.655)
    assert row[1] == 2

def test_geo_animation_mart_without_geo_columns(db):
    _stage(db, _inspections_df().drop(columns=["latitude", "longitude"]))
    result = am.create_geo_animation_mart()
    assert result["status"] == "success"
    assert result["row_count"] == 0
    assert "note" in result

def test_all_functions_error_when_staging_missing(db):
    for func in ALL_CREATE_FUNCS:
        result = func()
        assert result["status"] == "error", func.__name__
        assert "staging.inspections" in result["error"]

def test_idempotency_each_create_runs_twice(staged):
    for func in ALL_CREATE_FUNCS:
        first = func()
        second = func()
        assert first["status"] == "success", func.__name__
        assert second["status"] == "success", func.__name__
        assert first["row_count"] == second["row_count"]

def test_refresh_all_analytics_views(staged):
    results = am.refresh_all_analytics_views()
    assert set(results) == {
        "borough_summary",
        "time_series_snapshots",
        "material_analysis_mart",
        "clustering_features",
        "geo_animation_mart",
    }
    assert all(r["status"] == "success" for r in results.values())

def test_scheduler_run_materialize_analytics_contract():
    from socrata_toolkit.core.scheduler import ScheduleRunner

    runner = ScheduleRunner()
    mocks = {}
    with (
        patch.object(am, "create_borough_summary") as m_borough,
        patch.object(am, "create_time_series_snapshots") as m_ts,
        patch.object(am, "create_material_analysis_mart") as m_mat,
        patch.object(am, "create_clustering_features") as m_clust,
        patch.object(am, "create_geo_animation_mart") as m_geo,
    ):
        mocks = {
            "borough_summary": m_borough,
            "time_series": m_ts,
            "material_analysis": m_mat,
            "clustering": m_clust,
            "geo_animation": m_geo,
        }
        for name, mock in mocks.items():
            mock.return_value = {"status": "success", "table": name, "row_count": 0}
        results = runner.run_materialize_analytics()
    for name, mock in mocks.items():
        mock.assert_called_once_with()
        assert results[name]["status"] == "success"
    assert set(results) == set(mocks)
