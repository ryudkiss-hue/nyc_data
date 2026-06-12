"""Tests for MotherDuck staging transformations (motherduck-model-data)."""

import pandas as pd
import pytest

from socrata_toolkit.motherduck.connector import MotherDuckConnection
from socrata_toolkit.motherduck.ingestion import InspectionDataLoader
from socrata_toolkit.motherduck.staging import StagingTransformer


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


@pytest.fixture
def staging_transformer(motherduck_conn):
    """Fixture providing a StagingTransformer instance."""
    return StagingTransformer(motherduck_conn)


class TestStagingSchemaCreation:
    """Tests for staging schema and table creation."""

    def test_staging_schema_created(self, data_loader, staging_transformer):
        """Verify staging schema is created."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        result = staging_transformer.conn.fetch_all(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'staging'"
        )
        assert len(result) > 0, "Staging schema should exist"

    def test_inspection_clean_table_created(self, data_loader, staging_transformer):
        """Verify staging.inspection_clean table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        result = staging_transformer.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'staging' AND table_name = 'inspection_clean' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "inspection_clean table should exist"
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
            "geom",
            "inspection_date",
            "inspection_week",
            "inspection_month",
            "inspection_year",
            "severity_score",
            "staging_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in inspection_clean"

    def test_spatial_enriched_table_created(self, data_loader, staging_transformer):
        """Verify staging.spatial_enriched table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        result = staging_transformer.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'staging' AND table_name = 'spatial_enriched' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "spatial_enriched table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "location_id",
            "borough",
            "block",
            "lot",
            "latitude",
            "longitude",
            "geom",
            "inspection_count",
            "z_score_violations",
            "open_count",
            "avg_severity",
            "last_inspection_date",
            "days_span",
            "staging_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in spatial_enriched"

    def test_timeseries_prepared_table_created(self, data_loader, staging_transformer):
        """Verify staging.timeseries_prepared table is created with correct schema."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        result = staging_transformer.conn.fetch_all(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'staging' AND table_name = 'timeseries_prepared' "
            "ORDER BY ordinal_position"
        )

        assert len(result) > 0, "timeseries_prepared table should exist"
        column_names = [row[0] for row in result]

        expected_columns = [
            "date",
            "borough",
            "violation_count",
            "open_violations",
            "closed_violations",
            "avg_severity",
            "violation_count_7d_ma",
            "staging_load_timestamp",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column '{col}' not found in timeseries_prepared"


class TestInspectionCleanTransformation:
    """Tests for inspection_clean staging table transformations."""

    def test_inspection_clean_deduplication(self, data_loader, staging_transformer):
        """Verify deduplication: duplicate objectid keeps only latest created_date."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1, 1, 2],  # objectid 1 appears twice
                "created_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
                "violation_type": ["Type1", "Type1", "Type2"],
                "violation_code": ["CODE1", "CODE1", "CODE2"],
                "severity": ["Critical", "Critical", "Serious"],
                "borough": ["MN", "MN", "BK"],
                "block": [100, 100, 200],
                "lot": [1, 1, 2],
                "location_latitude": [40.7, 40.7, 40.6],
                "location_longitude": [-74.0, -74.0, -73.9],
                "open_violation": [True, False, True],
                "inspector_id": ["INS1", "INS1", "INS2"],
                "community_board": ["CB1", "CB1", "CB2"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()

        result = staging_transformer.conn.fetch_all(
            "SELECT objectid, created_date FROM staging.inspection_clean ORDER BY objectid"
        )

        assert len(result) == 2, "Should have 2 unique objectids after deduplication"

        # Check that objectid=1 has the latest created_date (2026-01-02)
        obj1_rows = [r for r in result if r[0] == 1]
        assert len(obj1_rows) == 1, "objectid=1 should appear only once"
        assert obj1_rows[0][1] == pd.Timestamp("2026-01-02").to_pydatetime(), (
            "Should keep latest date"
        )

    def test_inspection_clean_null_filtering(self, data_loader, staging_transformer):
        """Verify rows with null location coordinates are filtered out."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1, 2, 3],
                "created_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
                "violation_type": ["Type1", "Type2", "Type1"],
                "violation_code": ["CODE1", "CODE2", "CODE1"],
                "severity": ["High", "Low", "Medium"],
                "borough": ["MN", "BK", "QN"],
                "block": [100, 200, 300],
                "lot": [1, 2, 3],
                "location_latitude": [40.7, None, 40.8],  # objectid=2 has null latitude
                "location_longitude": [-74.0, -73.9, None],  # objectid=3 has null longitude
                "open_violation": [True, False, True],
                "inspector_id": ["INS1", "INS2", "INS3"],
                "community_board": ["CB1", "CB2", "CB3"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()

        result = staging_transformer.conn.fetch_all("SELECT COUNT(*) FROM staging.inspection_clean")

        assert result[0][0] == 1, "Should have only 1 row (objectid=1) after null filtering"

    def test_inspection_clean_severity_scoring(self, data_loader, staging_transformer):
        """Verify severity_score is computed correctly: Critical=3, Serious=2, else=1."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1, 2, 3, 4],
                "created_date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
                ),
                "violation_type": ["Type1", "Type2", "Type1", "Type2"],
                "violation_code": ["CODE1", "CODE2", "CODE1", "CODE2"],
                "severity": ["Critical", "Serious", "Minor", "Critical"],
                "borough": ["MN", "BK", "QN", "SI"],
                "block": [100, 200, 300, 400],
                "lot": [1, 2, 3, 4],
                "location_latitude": [40.7, 40.6, 40.8, 40.5],
                "location_longitude": [-74.0, -73.9, -73.8, -74.1],
                "open_violation": [True, False, True, False],
                "inspector_id": ["INS1", "INS2", "INS3", "INS4"],
                "community_board": ["CB1", "CB2", "CB3", "CB4"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 4),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()

        result = staging_transformer.conn.fetch_all(
            "SELECT objectid, severity, severity_score FROM staging.inspection_clean ORDER BY objectid"
        )

        expected_scores = {1: 3, 2: 2, 3: 1, 4: 3}

        for row in result:
            objectid, severity, score = row
            assert score == expected_scores[objectid], (
                f"objectid={objectid} severity={severity} should have score={expected_scores[objectid]}"
            )

    def test_inspection_clean_geometry_creation(self, data_loader, staging_transformer):
        """Verify geom is created from latitude/longitude."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1],
                "created_date": pd.to_datetime(["2026-01-01"]),
                "violation_type": ["Type1"],
                "violation_code": ["CODE1"],
                "severity": ["Critical"],
                "borough": ["MN"],
                "block": [100],
                "lot": [1],
                "location_latitude": [40.7],
                "location_longitude": [-74.0],
                "open_violation": [True],
                "inspector_id": ["INS1"],
                "community_board": ["CB1"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"]),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()

        result = staging_transformer.conn.fetch_all(
            "SELECT geom FROM staging.inspection_clean LIMIT 1"
        )

        assert result[0][0] is not None, "geom should not be null"

    def test_inspection_clean_date_columns(self, data_loader, staging_transformer):
        """Verify inspection_date, inspection_week, inspection_month, inspection_year are computed."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1],
                "created_date": pd.to_datetime(["2026-03-15"]),
                "violation_type": ["Type1"],
                "violation_code": ["CODE1"],
                "severity": ["Critical"],
                "borough": ["MN"],
                "block": [100],
                "lot": [1],
                "location_latitude": [40.7],
                "location_longitude": [-74.0],
                "open_violation": [True],
                "inspector_id": ["INS1"],
                "community_board": ["CB1"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"]),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()

        result = staging_transformer.conn.fetch_all(
            "SELECT inspection_date, inspection_week, inspection_month, inspection_year FROM staging.inspection_clean"
        )

        assert result[0][0] is not None, "inspection_date should not be null"
        assert result[0][1] is not None, "inspection_week should not be null"
        assert result[0][2] == 3, "inspection_month should be 3 (March)"
        assert result[0][3] == 2026, "inspection_year should be 2026"


class TestSpatialEnrichedTransformation:
    """Tests for spatial_enriched staging table transformations."""

    def test_spatial_enriched_z_score_computation(self, data_loader, staging_transformer):
        """Verify z-score is computed correctly: (count - mean) / std_dev."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        # Create inspection data with varying counts per location
        sample_df = pd.DataFrame(
            {
                "objectid": [1, 2, 3, 4, 5],
                "created_date": pd.to_datetime(
                    [
                        "2026-01-01",
                        "2026-01-02",
                        "2026-01-03",
                        "2026-01-04",
                        "2026-01-05",
                    ]
                ),
                "violation_type": ["Type1"] * 5,
                "violation_code": ["CODE1"] * 5,
                "severity": ["Critical"] * 5,
                "borough": ["MN", "MN", "MN", "BK", "BK"],
                "block": [100, 100, 100, 200, 200],
                "lot": [1, 1, 1, 2, 2],
                "location_latitude": [40.7, 40.7, 40.7, 40.6, 40.6],
                "location_longitude": [-74.0, -74.0, -74.0, -73.9, -73.9],
                "open_violation": [True] * 5,
                "inspector_id": ["INS1"] * 5,
                "community_board": ["CB1", "CB1", "CB1", "CB2", "CB2"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 5),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()
        staging_transformer.transform_spatial_enriched()

        result = staging_transformer.conn.fetch_all(
            "SELECT location_id, inspection_count, z_score_violations FROM staging.spatial_enriched ORDER BY location_id"
        )

        assert len(result) > 0, "spatial_enriched should have data"

        for row in result:
            location_id, count, z_score = row
            assert count is not None, f"{location_id} inspection_count should not be null"
            assert z_score is not None, f"{location_id} z_score should not be null"

    def test_spatial_enriched_location_id_creation(self, data_loader, staging_transformer):
        """Verify location_id is created from CONCAT(borough, block, lot)."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        sample_df = pd.DataFrame(
            {
                "objectid": [1, 2],
                "created_date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                "violation_type": ["Type1", "Type2"],
                "violation_code": ["CODE1", "CODE2"],
                "severity": ["Critical", "Serious"],
                "borough": ["MN", "BK"],
                "block": [100, 200],
                "lot": [1, 2],
                "location_latitude": [40.7, 40.6],
                "location_longitude": [-74.0, -73.9],
                "open_violation": [True, False],
                "inspector_id": ["INS1", "INS2"],
                "community_board": ["CB1", "CB2"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 2),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()
        staging_transformer.transform_spatial_enriched()

        result = staging_transformer.conn.fetch_all(
            "SELECT location_id FROM staging.spatial_enriched ORDER BY location_id"
        )

        assert len(result) == 2, "Should have 2 locations"
        location_ids = [row[0] for row in result]

        # location_id should be formatted as 'borough-block-lot' (e.g., 'MN-100-1')
        assert all("-" in loc_id for loc_id in location_ids), "location_id should contain hyphens"
        assert any("MN" in loc_id for loc_id in location_ids), "Should have MN borough"
        assert any("BK" in loc_id for loc_id in location_ids), "Should have BK borough"


class TestTimeseriesPreparedTransformation:
    """Tests for timeseries_prepared staging table transformations."""

    def test_timeseries_prepared_with_calendar_join(self, data_loader, staging_transformer):
        """Verify timeseries has daily records aggregated by date."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        # Create inspection data across multiple days
        sample_df = pd.DataFrame(
            {
                "objectid": [1, 2, 3],
                "created_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-03"]),
                "violation_type": ["Type1", "Type1", "Type2"],
                "violation_code": ["CODE1", "CODE1", "CODE2"],
                "severity": ["Critical", "Serious", "Minor"],
                "borough": ["MN", "MN", "MN"],
                "block": [100, 100, 100],
                "lot": [1, 1, 1],
                "location_latitude": [40.7, 40.7, 40.7],
                "location_longitude": [-74.0, -74.0, -74.0],
                "open_violation": [True, False, True],
                "inspector_id": ["INS1", "INS1", "INS2"],
                "community_board": ["CB1", "CB1", "CB1"],
                "data_load_timestamp": pd.to_datetime(["2026-06-11"] * 3),
            }
        )

        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()
        staging_transformer.transform_timeseries_prepared()

        result = staging_transformer.conn.fetch_all(
            "SELECT DISTINCT date FROM staging.timeseries_prepared WHERE borough='MN' ORDER BY date"
        )

        assert len(result) >= 2, "Should have at least 2 date records (2026-01-01 and 2026-01-03)"

    def test_timeseries_prepared_7day_moving_average(self, data_loader, staging_transformer):
        """Verify violation_count_7d_ma is computed correctly."""
        data_loader.create_raw_schema()
        staging_transformer.create_staging_schema()

        # Create 10 days of data for one borough
        dates = pd.date_range(start="2026-01-01", periods=10, freq="D")
        sample_data = []
        for i, date in enumerate(dates):
            sample_data.append(
                {
                    "objectid": i,
                    "created_date": date,
                    "violation_type": "Type1",
                    "violation_code": "CODE1",
                    "severity": "Critical",
                    "borough": "MN",
                    "block": 100,
                    "lot": 1,
                    "location_latitude": 40.7,
                    "location_longitude": -74.0,
                    "open_violation": True,
                    "inspector_id": "INS1",
                    "community_board": "CB1",
                    "data_load_timestamp": pd.Timestamp("2026-06-11"),
                }
            )

        sample_df = pd.DataFrame(sample_data)
        data_loader.load_inspection_data(sample_df)
        staging_transformer.transform_inspection_clean()
        staging_transformer.transform_timeseries_prepared()

        result = staging_transformer.conn.fetch_all(
            "SELECT date, violation_count_7d_ma FROM staging.timeseries_prepared WHERE borough='MN' ORDER BY date"
        )

        assert len(result) > 0, "Should have timeseries records"

        # Check that MA is computed (not null on later dates)
        ma_values = [row[1] for row in result if row[1] is not None]
        assert len(ma_values) > 0, "7-day moving average should have values"
