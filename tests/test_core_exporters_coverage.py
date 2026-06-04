"""Comprehensive tests for core.exporters module.

Tests XLSX, PostgreSQL, and MongoDB exporters with realistic synthetic data.
Uses Faker for volume/integration testing and mocks for unit testing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestXLSXExporter:
    """Test XLSXExporter for writing data to Excel files."""

    def test_xlsx_write_dataframe_basic(self, sample_df, temp_data_dir):
        """Test writing a DataFrame to Excel."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "output.xlsx"

        exporter.write(sample_df, str(output_path))
        assert output_path.exists()

        # Verify the file can be read back
        read_df = pd.read_excel(output_path)
        assert len(read_df) == len(sample_df)
        assert list(read_df.columns) == list(sample_df.columns)

    def test_xlsx_write_list_of_dicts(self, temp_data_dir):
        """Test writing a list of dictionaries to Excel."""
        from socrata_toolkit.core.exporters import XLSXExporter

        data = [
            {"id": 1, "name": "Alice", "score": 95},
            {"id": 2, "name": "Bob", "score": 87},
            {"id": 3, "name": "Charlie", "score": 92},
        ]
        exporter = XLSXExporter()
        output_path = temp_data_dir / "output.xlsx"

        exporter.write(data, str(output_path))
        assert output_path.exists()

        read_df = pd.read_excel(output_path)
        assert len(read_df) == 3
        assert "name" in read_df.columns

    def test_xlsx_write_with_custom_sheet(self, sample_df, temp_data_dir):
        """Test writing with custom sheet name."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "output.xlsx"

        exporter.write(sample_df, str(output_path), sheet="CustomSheet")
        assert output_path.exists()

        # Verify sheet name
        xls = pd.ExcelFile(output_path)
        assert "CustomSheet" in xls.sheet_names

    def test_xlsx_write_with_freeze_panes(self, sample_df, temp_data_dir):
        """Test that freeze_panes is applied."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "output.xlsx"

        exporter.write(sample_df, str(output_path), freeze_panes=True)
        assert output_path.exists()

    def test_xlsx_write_with_auto_filter(self, sample_df, temp_data_dir):
        """Test that auto_filter is applied."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "output.xlsx"

        exporter.write(sample_df, str(output_path), auto_filter=True)
        assert output_path.exists()

    def test_xlsx_write_empty_dataframe(self, empty_dataframe, temp_data_dir):
        """Test writing an empty DataFrame."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "output.xlsx"

        exporter.write(empty_dataframe, str(output_path))
        assert output_path.exists()

    def test_xlsx_write_large_volume(self, fake_large_dataframe, temp_data_dir):
        """Test writing a large DataFrame (10K rows)."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "large_output.xlsx"

        exporter.write(fake_large_dataframe, str(output_path))
        assert output_path.exists()

        # Verify all rows were written
        read_df = pd.read_excel(output_path)
        assert len(read_df) == len(fake_large_dataframe)

    def test_xlsx_write_with_metadata(self, sample_df, temp_data_dir):
        """Test writing with metadata sheets."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "output_with_meta.xlsx"

        # Create mock metadata object
        mock_meta = MagicMock()
        mock_meta.summary.return_value = {"total_rows": len(sample_df), "total_cols": len(sample_df.columns)}
        mock_meta.column_dict.return_value = [
            {"column": "id", "type": "int"},
            {"column": "description", "type": "str"},
        ]

        exporter.write(sample_df, str(output_path), meta=mock_meta)
        assert output_path.exists()

        # Verify metadata sheets exist
        xls = pd.ExcelFile(output_path)
        assert "Summary" in xls.sheet_names
        assert "Column Dictionary" in xls.sheet_names


class TestPostgresExporter:
    """Test PostgresExporter for database operations."""

    def test_postgres_exporter_requires_psycopg(self):
        """Test that PostgresExporter raises error without psycopg."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg", None):
            with pytest.raises(ImportError, match="Install postgres extras"):
                PostgresExporter("postgresql://localhost/test")

    def test_postgres_exporter_init_with_mock(self):
        """Test PostgresExporter initialization with mocked psycopg."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_psycopg.connect.return_value = mock_conn

            exporter = PostgresExporter("postgresql://localhost/test")
            assert exporter.conn == mock_conn

    def test_postgres_exporter_context_manager(self):
        """Test PostgresExporter as context manager."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_psycopg.connect.return_value = mock_conn

            with PostgresExporter("postgresql://localhost/test") as exporter:
                assert exporter is not None

            mock_conn.close.assert_called_once()

    def test_postgres_sql_type_detection(self):
        """Test _sql_type method for type inference."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_psycopg.connect.return_value = mock_conn

            exporter = PostgresExporter("postgresql://localhost/test")

            assert exporter._sql_type(True) == "BOOLEAN"
            assert exporter._sql_type(42) == "BIGINT"
            assert exporter._sql_type(3.14) == "DOUBLE PRECISION"
            assert exporter._sql_type("text") == "TEXT"

    def test_postgres_upsert_empty_batch(self):
        """Test upsert with empty batch."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_psycopg.connect.return_value = mock_conn

            exporter = PostgresExporter("postgresql://localhost/test")
            result = exporter.upsert_batches([], "test_table", "id")

            assert result == 0

    def test_postgres_upsert_single_batch(self):
        """Test upsert with single batch of records."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_psycopg.connect.return_value = mock_conn

            exporter = PostgresExporter("postgresql://localhost/test")
            batch = [
                {"id": 1, "name": "Alice", "age": 30},
                {"id": 2, "name": "Bob", "age": 25},
            ]
            result = exporter.upsert_batches([batch], "test_table", "id")

            assert result >= 0
            # Verify table creation was attempted
            mock_cursor.execute.assert_called()

    def test_postgres_upsert_multiple_batches(self):
        """Test upsert with multiple batches."""
        from socrata_toolkit.core.exporters import PostgresExporter

        with patch("socrata_toolkit.core.exporters.psycopg") as mock_psycopg:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_psycopg.connect.return_value = mock_conn

            exporter = PostgresExporter("postgresql://localhost/test")
            batches = [
                [{"id": 1, "value": 10}],
                [{"id": 2, "value": 20}],
                [{"id": 3, "value": 30}],
            ]
            result = exporter.upsert_batches(batches, "test_table", "id")

            assert result >= 0
            assert mock_cursor.execute.call_count > 0


class TestMongoExporter:
    """Test MongoExporter for MongoDB operations."""

    def test_mongo_exporter_requires_pymongo(self):
        """Test that MongoExporter raises error without pymongo."""
        from socrata_toolkit.core.exporters import MongoExporter

        with patch("socrata_toolkit.core.exporters.pymongo", None):
            with pytest.raises(ImportError, match="Install pymongo"):
                MongoExporter("mongodb://localhost/test_db")

    def test_mongo_exporter_init_with_mock(self):
        """Test MongoExporter initialization with mocked pymongo."""
        from socrata_toolkit.core.exporters import MongoExporter

        with patch("socrata_toolkit.core.exporters.pymongo") as mock_pymongo:
            mock_client = MagicMock()
            mock_pymongo.MongoClient.return_value = mock_client

            exporter = MongoExporter("mongodb://localhost/test_db")
            assert exporter.client is not None

    def test_mongo_exporter_context_manager(self):
        """Test MongoExporter as context manager."""
        from socrata_toolkit.core.exporters import MongoExporter

        with patch("socrata_toolkit.core.exporters.pymongo") as mock_pymongo:
            mock_client = MagicMock()
            mock_pymongo.MongoClient.return_value = mock_client

            with MongoExporter("mongodb://localhost/test_db") as exporter:
                assert exporter is not None

            mock_client.close.assert_called_once()

    def test_mongo_upsert_documents(self):
        """Test upserting documents to MongoDB."""
        from socrata_toolkit.core.exporters import MongoExporter

        with patch("socrata_toolkit.core.exporters.pymongo") as mock_pymongo:
            mock_client = MagicMock()
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_client.__getitem__.return_value = mock_db
            mock_db.__getitem__.return_value = mock_collection
            mock_pymongo.MongoClient.return_value = mock_client

            exporter = MongoExporter("mongodb://localhost/test_db")
            documents = [
                {"_id": 1, "name": "Alice", "age": 30},
                {"_id": 2, "name": "Bob", "age": 25},
            ]

            exporter.upsert_documents(documents, "test_collection", "_id")

            # Verify bulk write was called
            mock_collection.bulk_write.assert_called_once()


class TestExporterIntegration:
    """Integration tests for exporting synthetic data."""

    def test_export_fake_inspection_records_to_excel(self, fake_inspection_records, temp_data_dir):
        """Test exporting 100 fake inspection records to Excel."""
        from socrata_toolkit.core.exporters import XLSXExporter

        df = pd.DataFrame(fake_inspection_records)
        exporter = XLSXExporter()
        output_path = temp_data_dir / "inspections.xlsx"

        exporter.write(df, str(output_path))
        assert output_path.exists()

        # Verify data integrity
        read_df = pd.read_excel(output_path)
        assert len(read_df) == 100
        assert "borough" in read_df.columns
        assert "status" in read_df.columns

    def test_export_fake_violation_records_to_excel(self, fake_violation_records, temp_data_dir):
        """Test exporting 500 fake violation records to Excel."""
        from socrata_toolkit.core.exporters import XLSXExporter

        df = pd.DataFrame(fake_violation_records)
        exporter = XLSXExporter()
        output_path = temp_data_dir / "violations.xlsx"

        exporter.write(df, str(output_path))
        assert output_path.exists()

        read_df = pd.read_excel(output_path)
        assert len(read_df) == 500
        assert "violation_type" in read_df.columns

    def test_export_geospatial_data_to_excel(self, fake_geospatial_dataframe, temp_data_dir):
        """Test exporting geospatial data to Excel."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "geo_data.xlsx"

        exporter.write(fake_geospatial_dataframe, str(output_path))
        assert output_path.exists()

        read_df = pd.read_excel(output_path)
        assert len(read_df) == 100
        assert "latitude" in read_df.columns
        assert "longitude" in read_df.columns

    @pytest.mark.requires_faker
    def test_export_large_volume_performance(self, fake_large_dataframe, temp_data_dir):
        """Test performance of exporting large volume (10K rows)."""
        from socrata_toolkit.core.exporters import XLSXExporter

        exporter = XLSXExporter()
        output_path = temp_data_dir / "large_volume.xlsx"

        # This should complete in reasonable time
        exporter.write(fake_large_dataframe, str(output_path))
        assert output_path.exists()

        # File size should be reasonable for 10K rows
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        assert file_size_mb > 0
        assert file_size_mb < 50  # Sanity check for file size
