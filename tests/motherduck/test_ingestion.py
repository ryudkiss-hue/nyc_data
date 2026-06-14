"""Tests for MotherDuck data ingestion layer (motherduck-load-data)."""
import pandas as pd
import pytest

from socrata_toolkit.motherduck.connector import MotherDuckConnection
from socrata_toolkit.motherduck.ingestion import InspectionDataLoader


@pytest.fixture
def motherduck_conn():
    """Fixture providing a local DuckDB connection (no MotherDuck token needed)."""
    conn = MotherDuckConnection(token=None, database_path=":memory:")
    yield conn
    conn.close()

@pytest.fixture
def data_loader(motherduck_conn):
    """Fixture providing an InspectionDataLoader instance."""
    return InspectionDataLoader(motherduck_conn)

class TestRawTableCreation:
    """Tests for raw schema and table creation."""

    def test_inspection_raw_table_created(self, data_loader):
        """Verify raw.inspection_raw table is created with correct schema."""
        data_loader.create_raw_schema()

        result = data_loader.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'raw' AND table_name = 'inspection_raw' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "inspection_raw table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "objectid",
            "created_date",
            "violation_type",
            "violation_code",
            "severity",
            "borough",
            "block",
            "lot",
            "location_latitude",
            "location_longitude",
            "open_violation",
            "inspector_id",
            "community_board",
            "data_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in inspection_raw"

    def test_spatial_raw_table_created(self, data_loader):
        """Verify raw.spatial_raw table is created with correct schema."""
        data_loader.create_raw_schema()

        result = data_loader.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'raw' AND table_name = 'spatial_raw' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "spatial_raw table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "location_id",
            "borough",
            "block",
            "lot",
            "latitude",
            "longitude",
            "the_geom",
            "community_board",
            "inspection_count",
            "last_inspection_date",
            "data_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in spatial_raw"

    def test_timeseries_raw_table_created(self, data_loader):
        """Verify raw.timeseries_raw table is created with correct schema."""
        data_loader.create_raw_schema()

        result = data_loader.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'raw' AND table_name = 'timeseries_raw' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "timeseries_raw table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "date",
            "borough",
            "violation_count",
            "open_violations",
            "closed_violations",
            "avg_severity_score",
            "data_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in timeseries_raw"

    def test_violations_raw_table_created(self, data_loader):
        """Verify raw.violations_raw table is created with correct schema."""
        data_loader.create_raw_schema()

        result = data_loader.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'raw' AND table_name = 'violations_raw' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "violations_raw table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "violation_id",
            "inspection_id",
            "violation_type",
            "violation_code",
            "violation_date",
            "status",
            "borough",
            "data_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in violations_raw"

class TestDataLoading:
    """Tests for loading data into raw tables."""

    def test_load_inspection_data(self, data_loader):
        """Verify inspection data can be loaded into raw.inspection_raw."""
        data_loader.create_raw_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1, 2, 3],
                "created_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "violation_type": ["Type1", "Type2", "Type1"],
                "violation_code": ["CODE1", "CODE2", "CODE1"],
                "severity": ["High", "Low", "Medium"],
                "borough": ["MN", "BK", "QN"],
                "block": [100, 200, 300],
                "lot": [1, 2, 3],
                "location_latitude": [40.7, 40.6, 40.8],
                "location_longitude": [-74.0, -73.9, -73.8],
                "open_violation": [True, False, True],
                "inspector_id": ["INS1", "INS2", "INS3"],
                "community_board": ["CB1", "CB2", "CB3"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_inspection_data(sample_df)

        result = data_loader.conn.fetch_all("SELECT COUNT(*) FROM raw.inspection_raw")
        assert result[0][0] == 3, "Expected 3 rows in inspection_raw"

    def test_load_spatial_data(self, data_loader):
        """Verify spatial data can be loaded into raw.spatial_raw."""
        data_loader.create_raw_schema()

        sample_df = pd.DataFrame(
            {
                "location_id": ["LOC1", "LOC2", "LOC3"],
                "borough": ["MN", "BK", "QN"],
                "block": [100, 200, 300],
                "lot": [1, 2, 3],
                "latitude": [40.7, 40.6, 40.8],
                "longitude": [-74.0, -73.9, -73.8],
                "the_geom": ["POINT(1 1)", "POINT(2 2)", "POINT(3 3)"],
                "community_board": ["CB1", "CB2", "CB3"],
                "inspection_count": [5, 10, 15],
                "last_inspection_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_spatial_data(sample_df)

        result = data_loader.conn.fetch_all("SELECT COUNT(*) FROM raw.spatial_raw")
        assert result[0][0] == 3, "Expected 3 rows in spatial_raw"

    def test_load_timeseries_data(self, data_loader):
        """Verify timeseries data can be loaded into raw.timeseries_raw."""
        data_loader.create_raw_schema()

        sample_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
                "borough": ["MN", "BK", "QN"],
                "violation_count": [100, 150, 200],
                "open_violations": [50, 75, 100],
                "closed_violations": [50, 75, 100],
                "avg_severity_score": [3.5, 4.0, 3.8],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_timeseries_data(sample_df)

        result = data_loader.conn.fetch_all(
            "SELECT COUNT(*) FROM raw.timeseries_raw"
        )
        assert result[0][0] == 3, "Expected 3 rows in timeseries_raw"

    def test_load_violations_data(self, data_loader):
        """Verify violations data can be loaded into raw.violations_raw."""
        data_loader.create_raw_schema()

        sample_df = pd.DataFrame(
            {
                "violation_id": [1001, 1002, 1003],
                "inspection_id": [1, 2, 3],
                "violation_type": ["Type1", "Type2", "Type1"],
                "violation_code": ["CODE1", "CODE2", "CODE1"],
                "violation_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "status": ["Open", "Closed", "Open"],
                "borough": ["MN", "BK", "QN"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_violations_data(sample_df)

        result = data_loader.conn.fetch_all("SELECT COUNT(*) FROM raw.violations_raw")
        assert result[0][0] == 3, "Expected 3 rows in violations_raw"
