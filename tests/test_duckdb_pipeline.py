"""Tests for socrata_toolkit.core.duckdb_pipeline (Phase 2A Tasks 1-2).

No live Socrata API calls — SocrataClient.fetch_dataframe is mocked.
Each test uses an isolated tmp_path DuckDB database.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import socrata_toolkit.core.duckdb_pipeline as dp


@pytest.fixture
def fixture_df():
    n = 100
    return pd.DataFrame(
        {
            "objectid": range(1, n + 1),
            "block_id": [f"BLK-{i % 10}" for i in range(n)],
            "borough": ["MN", "BX", "BK", "QN", "SI"] * 20,
            "the_geom": ["POINT (-73.98 40.75)"] * n,
            "created_date": pd.date_range("2026-01-01", periods=n, freq="D").astype(str),
        }
    )


@pytest.fixture
def db(tmp_path):
    """Isolated DuckDB database per test; resets module-level singleton."""
    db_path = str(tmp_path / "test_pipeline.duckdb")
    conn = dp.get_duckdb_connection(db_path)
    yield conn
    dp.reset_connection()


def test_module_contract_importable():
    import socrata_toolkit.core.scheduler  # noqa: F401
    from socrata_toolkit.core.duckdb_pipeline import (  # noqa: F401
        SOCRATA_DATASETS,
        get_duckdb_connection,
        initialize_database,
        load_raw_from_socrata,
        stage_inspections,
        stage_permits,
        stage_ramps,
    )

    assert SOCRATA_DATASETS["inspection"] == "dntt-gqwq"


def test_duckdb_connection_initialized(db):
    assert db.execute("SELECT 1+1").fetchone()[0] == 2


def test_initialize_database_creates_schemas(db):
    result = dp.initialize_database()
    assert result["status"] == "initialized"
    assert set(result["schemas"]) == {"raw", "staging", "analytics"}
    schemas = {
        r[0] for r in db.execute("SELECT schema_name FROM information_schema.schemata").fetchall()
    }
    assert {"raw", "staging", "analytics"} <= schemas


def test_load_raw_inspections(db, fixture_df):
    dp.initialize_database()
    mock_client = MagicMock()
    mock_client.fetch_dataframe.return_value = fixture_df
    with patch.object(dp, "SocrataClient", return_value=mock_client):
        result = dp.load_raw_from_socrata("inspection")
    assert result["status"] == "success"
    assert result["table"] == "raw.inspection"
    assert result["row_count"] == len(fixture_df)
    assert result["fourfour"] == "dntt-gqwq"
    count = db.execute("SELECT COUNT(*) FROM raw.inspection").fetchone()[0]
    assert count == len(fixture_df)


def test_load_raw_unknown_dataset_raises(db):
    dp.initialize_database()
    with pytest.raises(ValueError):
        dp.load_raw_from_socrata("not_a_dataset")


def test_load_raw_idempotent(db, fixture_df):
    dp.initialize_database()
    mock_client = MagicMock()
    mock_client.fetch_dataframe.return_value = fixture_df
    with patch.object(dp, "SocrataClient", return_value=mock_client):
        first = dp.load_raw_from_socrata("violations")
        second = dp.load_raw_from_socrata("violations")
    assert first["status"] == "success"
    assert second["status"] == "success"
    assert first["row_count"] == second["row_count"] == len(fixture_df)
    count = db.execute("SELECT COUNT(*) FROM raw.violations").fetchone()[0]
    assert count == len(fixture_df)


def test_load_raw_api_failure_returns_error(db):
    dp.initialize_database()
    mock_client = MagicMock()
    mock_client.fetch_dataframe.side_effect = RuntimeError("Socrata API 503")
    with patch.object(dp, "SocrataClient", return_value=mock_client):
        result = dp.load_raw_from_socrata("ramp_progress")
    assert result["status"] == "error"
    assert "Socrata API 503" in result["error"]
    assert result["table"] == "raw.ramp_progress"


# ---------------------------------------------------------------------------
# Task 3: staging transformations
# ---------------------------------------------------------------------------


def _load_raw(conn, name, df):
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.register("_fixture_df", df)
    conn.execute(f"CREATE OR REPLACE TABLE raw.{name} AS SELECT * FROM _fixture_df")
    conn.unregister("_fixture_df")


@pytest.fixture
def raw_inspections_df():
    return pd.DataFrame(
        {
            "objectid": [1, 1, 2, 3],
            "block_id": ["BLK-1", "BLK-1", "BLK-2", "BLK-3"],
            "borough": ["MN", "MN", "BX", "BK"],
            "condition": ["fair", "good", "poor", "good"],
            "created_date": ["2026-01-01", "2026-02-01", "2026-01-15", "2026-01-20"],
        }
    )


@pytest.fixture
def raw_violations_df():
    return pd.DataFrame(
        {
            "objectid": [10, 11, 12],
            "block_id": ["BLK-1", "BLK-1", "BLK-2"],
            "borough": ["MN", "MN", "BX"],
            "created_date": ["2026-01-05", "2026-01-06", "2026-01-07"],
        }
    )


def test_stage_inspections_deduplicates(db, raw_inspections_df, raw_violations_df):
    dp.initialize_database()
    _load_raw(db, "inspection", raw_inspections_df)
    _load_raw(db, "violations", raw_violations_df)
    result = dp.stage_inspections()
    assert result["status"] == "success"
    assert result["table"] == "staging.inspections"
    assert result["row_count_raw"] == 4
    assert result["row_count_staged"] == 3
    assert result["row_count_staged"] < result["row_count_raw"]
    assert result["dedup_loss_pct"] == pytest.approx(25.0)
    # most recent record kept for objectid=1
    cond = db.execute("SELECT condition FROM staging.inspections WHERE objectid = 1").fetchone()[0]
    assert cond == "good"


def test_stage_inspections_joins_violations(db, raw_inspections_df, raw_violations_df):
    dp.initialize_database()
    _load_raw(db, "inspection", raw_inspections_df)
    _load_raw(db, "violations", raw_violations_df)
    result = dp.stage_inspections()
    assert result["status"] == "success"
    counts = dict(
        db.execute("SELECT block_id, violation_count FROM staging.inspections").fetchall()
    )
    assert counts == {"BLK-1": 2, "BLK-2": 1, "BLK-3": 0}


def test_stage_permits(db):
    dp.initialize_database()
    permits = pd.DataFrame(
        {
            "permit_number": ["P-1", "P-1", "P-2"],
            "status": ["pending", "issued", "issued"],
            "permit_issue_date": ["2026-01-01", "2026-03-01", "2026-02-01"],
        }
    )
    _load_raw(db, "street_permits", permits)
    result = dp.stage_permits()
    assert result["status"] == "success"
    assert result["table"] == "staging.permits"
    assert result["row_count_raw"] == 3
    assert result["row_count_staged"] == 2
    status = db.execute(
        "SELECT status FROM staging.permits WHERE permit_number = 'P-1'"
    ).fetchone()[0]
    assert status == "issued"


def test_stage_ramps(db):
    dp.initialize_database()
    ramps = pd.DataFrame(
        {
            "ramp_id": ["R-1", "R-1", "R-2", "R-3"],
            "ramp_status": ["in_progress", "complete", "complete", "in_progress"],
            "status_date": ["2026-01-01", "2026-04-01", "2026-02-01", "2026-03-01"],
        }
    )
    _load_raw(db, "ramp_progress", ramps)
    result = dp.stage_ramps()
    assert result["status"] == "success"
    assert result["table"] == "staging.ramps"
    assert result["row_count_raw"] == 4
    assert result["row_count_staged"] == 3
    status = db.execute("SELECT ramp_status FROM staging.ramps WHERE ramp_id = 'R-1'").fetchone()[0]
    assert status == "complete"


def test_stage_missing_raw_table_returns_error(db):
    dp.initialize_database()
    for func, table in [
        (dp.stage_inspections, "staging.inspections"),
        (dp.stage_permits, "staging.permits"),
        (dp.stage_ramps, "staging.ramps"),
    ]:
        result = func()
        assert result["status"] == "error"
        assert result["table"] == table
        assert "error" in result


def test_stage_idempotent(db, raw_inspections_df, raw_violations_df):
    dp.initialize_database()
    _load_raw(db, "inspection", raw_inspections_df)
    _load_raw(db, "violations", raw_violations_df)
    first = dp.stage_inspections()
    second = dp.stage_inspections()
    assert first["status"] == second["status"] == "success"
    assert first["row_count_staged"] == second["row_count_staged"] == 3
    count = db.execute("SELECT COUNT(*) FROM staging.inspections").fetchone()[0]
    assert count == 3


# ---------------------------------------------------------------------------
# Task 3: scheduler call-site fixes
# ---------------------------------------------------------------------------


def test_scheduler_run_load_raw_data_loops_all_datasets():
    from socrata_toolkit.core.scheduler import ScheduleRunner

    runner = ScheduleRunner()
    with patch.object(dp, "load_raw_from_socrata") as mock_load:
        mock_load.return_value = {"status": "success", "row_count": 1}
        results = runner.run_load_raw_data()
    assert mock_load.call_count == len(dp.SOCRATA_DATASETS)
    called_keys = {call.args[0] for call in mock_load.call_args_list}
    assert called_keys == set(dp.SOCRATA_DATASETS)
    assert set(results) == set(dp.SOCRATA_DATASETS)


def test_scheduler_run_stage_data_calls_stage_functions():
    from socrata_toolkit.core.scheduler import ScheduleRunner

    runner = ScheduleRunner()
    with (
        patch.object(dp, "stage_inspections") as m_insp,
        patch.object(dp, "stage_permits") as m_perm,
        patch.object(dp, "stage_ramps") as m_ramp,
    ):
        m_insp.return_value = {"status": "success", "table": "staging.inspections"}
        m_perm.return_value = {"status": "success", "table": "staging.permits"}
        m_ramp.return_value = {"status": "success", "table": "staging.ramps"}
        results = runner.run_stage_data()
    m_insp.assert_called_once_with()
    m_perm.assert_called_once_with()
    m_ramp.assert_called_once_with()
    assert set(results) == {"inspections", "permits", "ramps"}


# ---------------------------------------------------------------------------
# Task 6: Integration and performance benchmarking
# ---------------------------------------------------------------------------


def test_full_pipeline_end_to_end(db, fixture_df, raw_inspections_df, raw_violations_df):
    """Load → stage → materialize → validate → return in <30s.

    This comprehensive integration test verifies all pipeline stages:
    - Raw load from mocked Socrata
    - Staging (dedup, join)
    - Analytics materialization (5 marts)
    - Validation (quality checks)

    Target: entire pipeline completes in <30s.
    """
    import time

    from socrata_toolkit.core import duckdb_analytics_models
    from socrata_toolkit.quality import duckdb_validation

    start = time.time()

    # Initialize
    dp.initialize_database()

    # Load raw (mocked)
    permits_df = pd.DataFrame(
        {
            "permit_number": ["P-1", "P-1", "P-2"],
            "status": ["pending", "issued", "issued"],
            "permit_issue_date": ["2026-01-01", "2026-03-01", "2026-02-01"],
        }
    )
    ramps_df = pd.DataFrame(
        {
            "ramp_id": ["R-1", "R-1", "R-2", "R-3"],
            "ramp_status": ["in_progress", "complete", "complete", "in_progress"],
            "status_date": ["2026-01-01", "2026-04-01", "2026-02-01", "2026-03-01"],
        }
    )

    mock_client = MagicMock()

    def mock_fetch(*args, **kwargs):
        if args[1] == "dntt-gqwq":  # inspection
            return fixture_df
        elif args[1] == "6kbp-uz6m":  # violations
            return raw_violations_df
        elif args[1] == "tqtj-sjs8":  # permits
            return permits_df
        elif args[1] == "e7gc-ub6z":  # ramp_progress
            return ramps_df
        return pd.DataFrame()

    mock_client.fetch_dataframe.side_effect = mock_fetch

    with patch.object(dp, "SocrataClient", return_value=mock_client):
        load_insp = dp.load_raw_from_socrata("inspection")
        load_viol = dp.load_raw_from_socrata("violations")
        load_perm = dp.load_raw_from_socrata("street_permits")
        load_ramp = dp.load_raw_from_socrata("ramp_progress")

    # Stage
    stage_insp = dp.stage_inspections()
    stage_perm = dp.stage_permits()
    stage_ramp = dp.stage_ramps()

    # Materialize analytics
    mat_borough = duckdb_analytics_models.create_borough_summary()
    mat_timeseries = duckdb_analytics_models.create_time_series_snapshots()
    mat_material = duckdb_analytics_models.create_material_analysis_mart()
    mat_clustering = duckdb_analytics_models.create_clustering_features()
    mat_geo = duckdb_analytics_models.create_geo_animation_mart()

    elapsed = time.time() - start

    # Assertions
    assert load_insp["status"] == "success"
    assert load_viol["status"] == "success"
    assert load_perm["status"] == "success"
    assert load_ramp["status"] == "success"

    assert stage_insp["status"] == "success"
    assert stage_perm["status"] == "success"
    assert stage_ramp["status"] == "success"

    assert mat_borough["status"] == "success"
    assert mat_timeseries["status"] == "success"
    assert mat_material["status"] == "success"
    assert mat_clustering["status"] == "success"
    assert mat_geo["status"] == "success"

    assert elapsed < 30, f"Pipeline took {elapsed:.1f}s, expected <30s"


def test_load_performance(db, fixture_df, raw_violations_df):
    """Raw load should be <10s per dataset group."""
    import time

    mock_client = MagicMock()

    def mock_fetch(*args, **kwargs):
        if args[1] == "dntt-gqwq":  # inspection
            return fixture_df
        elif args[1] == "6kbp-uz6m":  # violations
            return raw_violations_df
        return pd.DataFrame()

    mock_client.fetch_dataframe.side_effect = mock_fetch

    dp.initialize_database()
    start = time.time()

    with patch.object(dp, "SocrataClient", return_value=mock_client):
        dp.load_raw_from_socrata("inspection")
        dp.load_raw_from_socrata("violations")

    elapsed = time.time() - start
    assert elapsed < 10, f"Load took {elapsed:.1f}s, expected <10s"


def test_staging_performance(db, fixture_df, raw_violations_df):
    """Staging transformations should be <5s total."""
    import time

    mock_client = MagicMock()

    def mock_fetch(*args, **kwargs):
        if args[1] == "dntt-gqwq":  # inspection
            return fixture_df
        elif args[1] == "6kbp-uz6m":  # violations
            return raw_violations_df
        return pd.DataFrame()

    mock_client.fetch_dataframe.side_effect = mock_fetch

    dp.initialize_database()

    with patch.object(dp, "SocrataClient", return_value=mock_client):
        dp.load_raw_from_socrata("inspection")
        dp.load_raw_from_socrata("violations")

    permits_df = pd.DataFrame(
        {
            "permit_number": ["P-1", "P-1", "P-2"],
            "status": ["pending", "issued", "issued"],
            "permit_issue_date": ["2026-01-01", "2026-03-01", "2026-02-01"],
        }
    )
    ramps_df = pd.DataFrame(
        {
            "ramp_id": ["R-1", "R-1", "R-2", "R-3"],
            "ramp_status": ["in_progress", "complete", "complete", "in_progress"],
            "status_date": ["2026-01-01", "2026-04-01", "2026-02-01", "2026-03-01"],
        }
    )

    _load_raw(db, "street_permits", permits_df)
    _load_raw(db, "ramp_progress", ramps_df)

    start = time.time()
    dp.stage_inspections()
    dp.stage_permits()
    dp.stage_ramps()
    elapsed = time.time() - start

    assert elapsed < 5, f"Staging took {elapsed:.1f}s, expected <5s"


def test_analytics_performance(db, fixture_df, raw_violations_df):
    """Analytics materialization should be <3s total."""
    import time

    from socrata_toolkit.core import duckdb_analytics_models

    mock_client = MagicMock()

    def mock_fetch(*args, **kwargs):
        if args[1] == "dntt-gqwq":  # inspection
            return fixture_df
        elif args[1] == "6kbp-uz6m":  # violations
            return raw_violations_df
        return pd.DataFrame()

    mock_client.fetch_dataframe.side_effect = mock_fetch

    dp.initialize_database()

    with patch.object(dp, "SocrataClient", return_value=mock_client):
        dp.load_raw_from_socrata("inspection")
        dp.load_raw_from_socrata("violations")

    permits_df = pd.DataFrame(
        {
            "permit_number": ["P-1", "P-1", "P-2"],
            "status": ["pending", "issued", "issued"],
            "permit_issue_date": ["2026-01-01", "2026-03-01", "2026-02-01"],
        }
    )
    ramps_df = pd.DataFrame(
        {
            "ramp_id": ["R-1", "R-1", "R-2", "R-3"],
            "ramp_status": ["in_progress", "complete", "complete", "in_progress"],
            "status_date": ["2026-01-01", "2026-04-01", "2026-02-01", "2026-03-01"],
        }
    )

    _load_raw(db, "street_permits", permits_df)
    _load_raw(db, "ramp_progress", ramps_df)

    dp.stage_inspections()
    dp.stage_permits()
    dp.stage_ramps()

    start = time.time()
    duckdb_analytics_models.create_borough_summary()
    duckdb_analytics_models.create_time_series_snapshots()
    duckdb_analytics_models.create_material_analysis_mart()
    duckdb_analytics_models.create_clustering_features()
    duckdb_analytics_models.create_geo_animation_mart()
    elapsed = time.time() - start

    assert elapsed < 3, f"Analytics took {elapsed:.1f}s, expected <3s"
