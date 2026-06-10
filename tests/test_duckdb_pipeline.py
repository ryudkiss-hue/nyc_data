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
    )

    assert SOCRATA_DATASETS["inspection"] == "dntt-gqwq"


def test_duckdb_connection_initialized(db):
    assert db.execute("SELECT 1+1").fetchone()[0] == 2


def test_initialize_database_creates_schemas(db):
    result = dp.initialize_database()
    assert result["status"] == "initialized"
    assert set(result["schemas"]) == {"raw", "staging", "analytics"}
    schemas = {
        r[0]
        for r in db.execute(
            "SELECT schema_name FROM information_schema.schemata"
        ).fetchall()
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
