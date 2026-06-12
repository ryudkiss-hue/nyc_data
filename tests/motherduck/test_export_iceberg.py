"""Tests for Iceberg export functionality (motherduck-ducklake).

TDD approach: tests first, implementation follows.

Purpose: Enable external sharing of analytics results in Iceberg format.
"""

from pathlib import Path

import pytest

from socrata_toolkit.motherduck.connector import MotherDuckConnection
from socrata_toolkit.motherduck.export_iceberg import IcebergExporter


class TestIcebergExporterInitialization:
    """Test IcebergExporter initialization and configuration."""

    def test_iceberg_exporter_initialized(self):
        """Test creating exporter and verifying export_path is set."""
        conn = MotherDuckConnection(token=None, database_path=":memory:")
        export_path = "s3://my-bucket/exports"

        exporter = IcebergExporter(connection=conn, export_path=export_path)

        assert exporter.export_path == export_path
        assert exporter.connection is conn

    def test_export_analytics_tables_method_exists(self):
        """Test that export_analytics_tables method exists and is callable."""
        conn = MotherDuckConnection(token=None, database_path=":memory:")
        exporter = IcebergExporter(connection=conn, export_path="/tmp/exports")

        assert hasattr(exporter, "export_analytics_tables")
        assert callable(exporter.export_analytics_tables)

    def test_export_method_with_list(self):
        """Test export_analytics_tables accepts specific table list."""
        conn = MotherDuckConnection(token=None, database_path=":memory:")
        exporter = IcebergExporter(connection=conn, export_path="/tmp/exports")

        # Should accept None (default tables) or explicit list
        result_default = exporter.export_analytics_tables(tables=None)
        result_list = exporter.export_analytics_tables(
            tables=["phase_b_spatial_clusters", "phase_c_distributions"]
        )

        # Both should return a result dict with status info
        assert isinstance(result_default, dict)
        assert isinstance(result_list, dict)

    def test_export_path_computed_correctly(self):
        """Test that table paths are computed correctly."""
        conn = MotherDuckConnection(token=None, database_path=":memory:")
        export_path = "/data/exports"
        exporter = IcebergExporter(connection=conn, export_path=export_path)

        # Test path computation for a sample table
        table_name = "phase_b_spatial_clusters"
        expected_path = "/data/exports/phase_b_spatial_clusters/"

        # Verify the internal method that computes paths exists
        assert hasattr(exporter, "_compute_table_path")
        computed_path = exporter._compute_table_path(table_name)
        assert computed_path == expected_path

    def test_export_path_with_s3_uri(self):
        """Test that S3 paths are handled correctly."""
        conn = MotherDuckConnection(token=None, database_path=":memory:")
        s3_path = "s3://my-bucket/analytics/exports"
        exporter = IcebergExporter(connection=conn, export_path=s3_path)

        table_name = "phase_d_anomalies"
        expected_path = "s3://my-bucket/analytics/exports/phase_d_anomalies/"

        computed_path = exporter._compute_table_path(table_name)
        assert computed_path == expected_path

    def test_default_tables_exported_when_none(self):
        """Test that default table list is used when None is passed."""
        conn = MotherDuckConnection(token=None, database_path=":memory:")
        exporter = IcebergExporter(connection=conn, export_path="/tmp/exports")

        # Verify default tables are defined
        assert hasattr(exporter, "DEFAULT_TABLES")
        assert isinstance(exporter.DEFAULT_TABLES, list)
        assert len(exporter.DEFAULT_TABLES) == 6

        # Check that expected tables are in the default list
        expected_tables = [
            "phase_b_spatial_clusters",
            "phase_c_distributions",
            "phase_d_anomalies",
            "phase_e_decomposition",
            "phase_f_bootstrap_ci",
            "kpi_metrics",
        ]
        for table in expected_tables:
            assert table in exporter.DEFAULT_TABLES
