
import pandas as pd
import pytest

from app.analytics import _compute_duplicate_pct, _estimate_cardinality
from socrata_toolkit.core.duckdb_store import DuckDBManager


@pytest.fixture
def test_duckdb(tmp_path):
    """Setup a temporary DuckDB for pushdown tests."""
    db_path = str(tmp_path / "test.duckdb")
    manager = DuckDBManager(db_path)

    # Create a test table
    df = pd.DataFrame(
        {
            "id": [1, 2, 2, 3, 4],  # 4 unique, 1 duplicate row
            "cat": ["A", "A", "A", "B", "B"],  # 2 unique
        }
    )
    manager.conn.register("temp_df", df)
    manager.query('CREATE TABLE "test_ds" AS SELECT * FROM temp_df')
    manager.close()

    # Inject paths into app.data_loader (Mocking global state)
    import app.data_loader

    original_path = app.data_loader._DUCKDB_PATH
    original_available = app.data_loader._DUCKDB_AVAILABLE

    app.data_loader._DUCKDB_PATH = db_path
    app.data_loader._DUCKDB_AVAILABLE = True

    yield db_path

    # Restore
    app.data_loader._DUCKDB_PATH = original_path
    app.data_loader._DUCKDB_AVAILABLE = original_available


def test_duckdb_cardinality_pushdown(test_duckdb):
    """Verify cardinality estimation uses DuckDB SQL."""
    # We pass series=None because it should hit DuckDB
    # If it fails to hit DuckDB, it will crash or return -1
    card = _estimate_cardinality(None, dataset_key="test_ds", col_name="cat")
    assert card == 2

    card_id = _estimate_cardinality(None, dataset_key="test_ds", col_name="id")
    assert card_id == 4


def test_duckdb_duplicate_pct_pushdown(test_duckdb):
    """Verify duplicate detection uses DuckDB SQL."""
    # 5 rows total, 4 unique rows
    # Duplicate % = 100 * (5 - 4) / 5 = 20%
    pct = _compute_duplicate_pct(None, dataset_key="test_ds")
    assert pct == 20.0


def test_duckdb_fallback_on_error(mocker):
    """Verify fallback to sampling when DuckDB fails."""
    import app.data_loader

    mocker.patch.object(app.data_loader, "_DUCKDB_AVAILABLE", True)
    mocker.patch(
        "socrata_toolkit.core.duckdb_store.DuckDBManager", side_effect=Exception("DB Locked")
    )

    df = pd.DataFrame({"col": [1, 1, 2]})
    # Should fall back to pandas.nunique() -> 2
    card = _estimate_cardinality(df["col"], dataset_key="err", col_name="col")
    assert card == 2
