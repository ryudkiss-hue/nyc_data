"""Tests for generalized materialization factory (Phase 4a: Materialization + Management)."""
import json
import pytest
import duckdb
from pathlib import Path

from socrata_toolkit.core.materialization import (
    MaterializationFactory,
    BuilderRegistry,
    MartLineage,
    MartQuality,
    MartBuilder,
)

@pytest.fixture
def db():
    """In-memory DuckDB for testing."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE SCHEMA raw")
    conn.execute("CREATE SCHEMA staging")
    conn.execute("CREATE SCHEMA analytics")
    return conn

@pytest.fixture
def sample_staging_data(db):
    """Create sample staging tables for testing."""
    # inspection staging table
    db.execute("""
        CREATE TABLE staging.inspection (
            objectid INTEGER,
            material_type VARCHAR,
            borough VARCHAR,
            created_date TIMESTAMP,
            condition_rating INTEGER
        )
    """)
    db.execute("""
        INSERT INTO staging.inspection VALUES
        (1, 'concrete', 'MN', '2026-06-01'::TIMESTAMP, 8),
        (2, 'asphalt', 'BK', '2026-06-02'::TIMESTAMP, 6),
        (3, 'concrete', 'MN', '2026-06-03'::TIMESTAMP, 9),
        (4, 'stone', 'QN', '2026-06-04'::TIMESTAMP, 5)
    """)

    # violations staging table
    db.execute("""
        CREATE TABLE staging.violations (
            violation_id INTEGER,
            material_type VARCHAR,
            borough VARCHAR,
            created_date TIMESTAMP,
            severity VARCHAR
        )
    """)
    db.execute("""
        INSERT INTO staging.violations VALUES
        (1, 'concrete', 'MN', '2026-06-01'::TIMESTAMP, 'high'),
        (2, 'asphalt', 'BK', '2026-06-02'::TIMESTAMP, 'medium'),
        (3, 'concrete', 'QN', '2026-06-03'::TIMESTAMP, 'low')
    """)

    return db

@pytest.fixture
def test_dataset_config():
    """Test dataset configuration."""
    return {
        "inspection": {
            "key_candidates": ["objectid"],
            "date_candidates": ["created_date"],
            "expected_row_count_min": 1,
            "expected_row_count_max": 1000
        },
        "violations": {
            "key_candidates": ["violation_id"],
            "date_candidates": ["created_date"],
            "expected_row_count_min": 1,
            "expected_row_count_max": 1000
        }
    }

@pytest.fixture
def test_analytics_config():
    """Test analytics configuration."""
    return {
        "universal_mats": [
            {
                "name": "raw_counts_summary",
                "builder": "universal_counts",
                "datasets": ["all"]
            }
        ],
        "role1_mats": [
            {
                "name": "sidewalk_repair_matrix",
                "builder": "cross_tab",
                "datasets": ["inspection", "violations"],
                "rows": "material_type",
                "cols": "borough",
                "metric": "COUNT(*)"
            }
        ]
    }

def test_builder_registry_register_and_lookup():
    """Test that builders can register and be looked up."""
    registry = BuilderRegistry()

    class TestBuilder(MartBuilder):
        pass

    registry.register("test_builder")(TestBuilder)

    assert registry.get("test_builder") == TestBuilder

def test_builder_registry_missing_builder():
    """Test that missing builder raises error."""
    registry = BuilderRegistry()

    with pytest.raises(ValueError, match="Unknown builder"):
        registry.get("nonexistent")

def test_cross_tab_builder_discovery(sample_staging_data, test_dataset_config):
    """Test CrossTabBuilder discovers columns and generates SQL."""
    from socrata_toolkit.core.materialization.builders import CrossTabBuilder

    config = {
        "name": "sidewalk_repair_matrix",
        "builder": "cross_tab",
        "datasets": ["inspection"],
        "rows": "material_type",
        "cols": "borough",
        "metric": "COUNT(*)"
    }

    builder = CrossTabBuilder(config, test_dataset_config, sample_staging_data)

    # Verify column discovery
    assert builder.discovered_columns["inspection"]["actual_columns"]
    assert "material_type" in builder.discovered_columns["inspection"]["actual_columns"]
    assert "borough" in builder.discovered_columns["inspection"]["actual_columns"]

def test_mart_lineage_record(sample_staging_data):
    """Test lineage recording."""
    lineage = MartLineage()

    lineage.record(
        mart_name="sidewalk_repair_matrix",
        source_datasets=["inspection", "violations"],
        target_schema="analytics",
        target_table="sidewalk_repair_matrix",
        row_count=4,
        conn=sample_staging_data
    )

    # Verify lineage table was created
    result = sample_staging_data.execute(
        "SELECT COUNT(*) FROM analytics._lineage WHERE mart_name = 'sidewalk_repair_matrix'"
    ).fetchone()
    assert result[0] == 1

def test_mart_quality_score(sample_staging_data):
    """Test quality score computation."""
    quality = MartQuality()

    quality.track_metrics(
        mart_name="sidewalk_repair_matrix",
        row_count=4,
        schema={"material_type": "VARCHAR", "borough": "VARCHAR", "count": "INTEGER"},
        materialized_at="2026-06-10 18:00:00",
        conn=sample_staging_data
    )

    score = quality.compute_quality_score("sidewalk_repair_matrix", sample_staging_data)

    # Quality score should be >0 and <=100
    assert 0 <= score <= 100

def test_materialization_factory_end_to_end(sample_staging_data, test_dataset_config, test_analytics_config):
    """Test full materialization factory pipeline."""
    factory = MaterializationFactory(test_dataset_config, sample_staging_data)

    results = factory.materialize(test_analytics_config, schema="analytics")

    # Verify results structure
    assert "raw_counts_summary" in results
    assert "sidewalk_repair_matrix" in results

    # Verify successful materialization
    assert results["sidewalk_repair_matrix"]["status"] == "success"
    assert results["sidewalk_repair_matrix"]["row_count"] > 0

    # Verify table was created
    tables = sample_staging_data.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'analytics'"
    ).fetchall()
    assert any(t[0] == "sidewalk_repair_matrix" for t in tables)

def test_materialization_idempotency(sample_staging_data, test_dataset_config, test_analytics_config):
    """Test that materialization is idempotent (can run multiple times)."""
    factory = MaterializationFactory(test_dataset_config, sample_staging_data)

    results1 = factory.materialize(test_analytics_config, schema="analytics")
    results2 = factory.materialize(test_analytics_config, schema="analytics")

    # Both runs should succeed with same row counts
    assert results1["sidewalk_repair_matrix"]["row_count"] == results2["sidewalk_repair_matrix"]["row_count"]
