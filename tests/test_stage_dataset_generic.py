"""Tests for generic stage_dataset() function with auto column discovery."""
import json
from pathlib import Path

import duckdb
import pytest

from socrata_toolkit.core.duckdb_pipeline import stage_dataset


@pytest.fixture
def db():
    """In-memory DuckDB connection for testing."""
    return duckdb.connect(":memory:")

@pytest.fixture
def setup_test_data(db):
    """Create raw tables with sample data for testing."""
    db.execute("CREATE SCHEMA raw")
    db.execute("CREATE SCHEMA staging")

    # Load config to understand dataset structure
    config_path = Path("data/dataset_config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    # Create raw tables for 5 test datasets (must match config.json keys)
    datasets = ["inspection", "violations", "ramp_progress", "permits", "ramp_complaints"]
    for dataset_key in datasets:
        # Create raw table with sample data
        db.execute(f"""
            CREATE TABLE raw.{dataset_key} (
                objectid INTEGER,
                created_date TIMESTAMP,
                borough VARCHAR,
                data_value FLOAT
            )
        """)

        # Insert test data
        db.execute(f"""
            INSERT INTO raw.{dataset_key} VALUES
            (1, '2026-06-01'::TIMESTAMP, 'MN', 100.0),
            (2, '2026-06-02'::TIMESTAMP, 'BK', 200.0),
            (1, '2026-06-03'::TIMESTAMP, 'MN', 150.0),  -- duplicate key, newer date
            (3, '2026-06-04'::TIMESTAMP, 'QN', NULL),
            (4, NULL, 'SI', 250.0)  -- null key
        """)

    return db, datasets

def test_stage_inspection_discovery(setup_test_data):
    """Test stage_dataset('inspection') loads and deduplicates correctly."""
    db, _ = setup_test_data

    row_count = stage_dataset("inspection", db)

    # Verify staging table exists and has rows
    assert row_count > 0, "Staging table should have rows"

    tables = db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging'"
    ).fetchall()
    assert any(t[0] == "inspection" for t in tables), "staging.inspection not found"

def test_stage_violations_column_discovery(setup_test_data):
    """Test stage_dataset works with auto-discovered columns."""
    db, _ = setup_test_data

    row_count = stage_dataset("violations", db)

    assert row_count > 0, "Staging table should have rows"

    # Verify staging table exists
    result = db.execute(
        "SELECT COUNT(*) FROM staging.violations"
    ).fetchone()[0]
    assert result == row_count, "Row count mismatch"

def test_stage_ramp_progress_dedup(setup_test_data):
    """Test stage_dataset works with ramp_progress dataset."""
    db, _ = setup_test_data

    row_count = stage_dataset("ramp_progress", db)

    # Verify staging table exists and has rows
    assert row_count > 0, "Staging table should have rows"

    # Verify staging table is populated
    result = db.execute(
        "SELECT COUNT(*) FROM staging.ramp_progress"
    ).fetchone()[0]
    assert result > 0, "Staging table should not be empty"

def test_stage_permits_multiple_datasets(setup_test_data):
    """Test stage_dataset works with permits dataset."""
    db, _ = setup_test_data

    row_count = stage_dataset("permits", db)

    assert row_count > 0, "Staging table should have rows"

    # Verify table exists
    tables = db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging'"
    ).fetchall()
    assert any(t[0] == "permits" for t in tables), "staging.permits not found"

def test_stage_ramp_complaints_discovery(setup_test_data):
    """Test stage_dataset with ramp_complaints dataset."""
    db, _ = setup_test_data

    row_count = stage_dataset("ramp_complaints", db)

    assert row_count > 0, "Staging table should have rows"

    # Verify staging table is populated
    result = db.execute(
        "SELECT COUNT(*) FROM staging.ramp_complaints"
    ).fetchone()[0]
    assert result > 0, "Staging table should not be empty"
