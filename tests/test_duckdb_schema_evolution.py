import pytest

import os

import pandas as pd
import pytest

from socrata_toolkit.core.duckdb_store import DuckDBManager, DuckDBRepository


@pytest.fixture
def temp_mgr(tmp_path):
    """Providing a fresh memory/temp DuckDB for each test."""
    db_path = str(tmp_path / "evolution.duckdb")
    mgr = DuckDBManager(db_path)
    yield mgr
    mgr.close()


def test_automatic_column_addition(temp_mgr):
    """Verify that upserting a DF with extra columns triggers ALTER TABLE."""
    table_name = "evolution_test"
    repo = DuckDBRepository(temp_mgr, table_name)

    # 1. Create initial table
    df1 = pd.DataFrame({"id": [1], "val1": ["A"]})
    repo.upsert_dataframe(df1, "id")

    assert repo.count() == 1
    cols = [c[1] for c in temp_mgr.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()]
    assert "val1" in cols
    assert "val2" not in cols

    # 2. Upsert with new column "val2"
    df2 = pd.DataFrame({"id": [1, 2], "val1": ["A", "B"], "val2": ["X", "Y"]})
    repo.upsert_dataframe(df2, "id")

    assert repo.count() == 2
    cols_after = [
        c[1] for c in temp_mgr.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    ]
    assert "val2" in cols_after

    # Verify data integrity
    res = repo.fetch_all()
    row2 = res[res["id"] == 2].iloc[0]
    assert row2["val2"] == "Y"


def test_type_safety_on_evolution(temp_mgr):
    """Ensure evolved columns default to VARCHAR for maximum safety in municipal drift."""
    table_name = "type_safety_test"
    repo = DuckDBRepository(temp_mgr, table_name)

    repo.upsert_dataframe(pd.DataFrame({"id": [1]}), "id")

    # Add a numeric-looking column that might actually contain strings in future rows
    repo.upsert_dataframe(pd.DataFrame({"id": [1], "drift_col": [123]}), "id")

    info = temp_mgr.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    drift_info = next(c for c in info if c[1] == "drift_col")
    # type is the 3rd element in pragma table_info
    assert "VARCHAR" in drift_info[2].upper()
