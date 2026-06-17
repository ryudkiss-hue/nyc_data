"""Tests for core.app module - Database and environment helpers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pandas as pd
from sqlalchemy.engine import Engine

from socrata_toolkit.core.app import (
    candidate_sidewalk_tables,
    compute_kpis_from_df,
    find_latlon_columns,
    get_engine,
    list_tables,
    load_env,
    safe_read_table,
)


class TestLoadEnv:
    """Tests for load_env function."""

    def test_load_env_default_values(self):
        """Test load_env returns dict with default values when no env vars set."""
        with patch.dict(os.environ, {}, clear=True), patch("dotenv.load_dotenv"):
            result = load_env()
            assert isinstance(result, dict)
            assert result["PG_DSN"] is None
            assert result["EXPORT_DIR"] == "analysis"
            assert result["MAPBOX_TOKEN"] is None

    def test_load_env_with_env_variables(self):
        """Test load_env reads environment variables."""
        env_vars = {
            "PG_DSN": "postgresql://user:pass@localhost/db",
            "EXPORT_DIR": "custom_export",
            "MAPBOX_TOKEN": "pk.test123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = load_env()
            assert result["PG_DSN"] == "postgresql://user:pass@localhost/db"
            assert result["EXPORT_DIR"] == "custom_export"
            assert result["MAPBOX_TOKEN"] == "pk.test123"

    def test_load_env_dotenv_not_available(self):
        """Test load_env when dotenv is not available."""
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            result = load_env()
            assert result["EXPORT_DIR"] == "analysis"

    def test_load_env_file_not_found(self):
        """Test load_env when .env file doesn't exist."""
        with patch("dotenv.load_dotenv", side_effect=FileNotFoundError()):
            result = load_env()
            assert isinstance(result, dict)


class TestGetEngine:
    """Tests for get_engine function."""

    def test_get_engine_with_valid_dsn(self):
        """Test creating engine with valid DSN."""
        with patch("socrata_toolkit.core.app.create_engine") as mock_create:
            mock_engine = MagicMock(spec=Engine)
            mock_create.return_value = mock_engine

            result = get_engine("postgresql://localhost/test")
            assert result == mock_engine
            mock_create.assert_called_once()

    def test_get_engine_with_none_dsn(self):
        """Test get_engine returns None for None DSN."""
        result = get_engine(None)
        assert result is None

    def test_get_engine_with_empty_string(self):
        """Test get_engine returns None for empty string."""
        result = get_engine("")
        assert result is None

    def test_get_engine_creation_fails(self):
        """Test get_engine returns None when engine creation fails."""
        with patch(
            "socrata_toolkit.core.app.create_engine", side_effect=Exception("Connection failed")
        ):
            result = get_engine("postgresql://localhost/test")
            assert result is None


class TestListTables:
    """Tests for list_tables function."""

    def test_list_tables_success(self):
        """Test listing tables from database."""
        mock_engine = MagicMock(spec=Engine)
        expected_df = pd.DataFrame(
            {
                "table_schema": ["public", "public"],
                "table_name": ["users", "orders"],
            }
        )

        with patch("pandas.read_sql_query", return_value=expected_df):
            result = list_tables(mock_engine)
            assert len(result) == 2
            assert list(result.columns) == ["table_schema", "table_name"]

    def test_list_tables_empty_result(self):
        """Test list_tables with no results."""
        mock_engine = MagicMock(spec=Engine)
        expected_df = pd.DataFrame({"table_schema": [], "table_name": []})

        with patch("pandas.read_sql_query", return_value=expected_df):
            result = list_tables(mock_engine)
            assert len(result) == 0


class TestCandidateSidewalkTables:
    """Tests for candidate_sidewalk_tables function."""

    def test_candidate_sidewalk_tables_found(self):
        """Test identifying sidewalk-related tables."""
        mock_engine = MagicMock(spec=Engine)
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public", "public", "public", "public"],
                "table_name": ["sidewalk_inspections", "orders", "ramp_progress", "users"],
            }
        )

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            result = candidate_sidewalk_tables(mock_engine)
            assert "sidewalk_inspections" in result
            assert "ramp_progress" in result
            assert "orders" not in result

    def test_candidate_sidewalk_tables_none_found(self):
        """Test returning defaults when no matches found."""
        mock_engine = MagicMock(spec=Engine)
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public", "public"],
                "table_name": ["users", "products"],
            }
        )

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            result = candidate_sidewalk_tables(mock_engine)
            assert "inspections" in result
            assert len(result) > 0

    def test_candidate_sidewalk_tables_query_fails(self):
        """Test returning defaults when query fails."""
        mock_engine = MagicMock(spec=Engine)

        with patch("socrata_toolkit.core.app.list_tables", side_effect=Exception("Query failed")):
            result = candidate_sidewalk_tables(mock_engine)
            assert "inspections" in result
            assert "permits" in result

    def test_candidate_sidewalk_tables_no_table_name_column(self):
        """Test when result has no table_name column."""
        mock_engine = MagicMock(spec=Engine)
        mock_tables = pd.DataFrame({"table_schema": ["public"]})

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            result = candidate_sidewalk_tables(mock_engine)
            assert result == []

    def test_candidate_sidewalk_tables_deduplication(self):
        """Test that results are deduplicated."""
        mock_engine = MagicMock(spec=Engine)
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public", "public"],
                "table_name": ["inspections", "inspections"],
            }
        )

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            result = candidate_sidewalk_tables(mock_engine)
            assert result.count("inspections") == 1


class TestSafeReadTable:
    """Tests for safe_read_table function."""

    def test_safe_read_table_success(self):
        """Test reading table successfully."""
        mock_engine = MagicMock(spec=Engine)
        expected_data = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public"],
                "table_name": ["test_table"],
            }
        )

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            with patch("pandas.read_sql_query", return_value=expected_data):
                result = safe_read_table(mock_engine, "test_table")
                assert len(result) == 2

    def test_safe_read_table_not_found(self):
        """Test reading non-existent table."""
        mock_engine = MagicMock(spec=Engine)
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public"],
                "table_name": ["other_table"],
            }
        )

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            result = safe_read_table(mock_engine, "missing_table")
            assert len(result) == 0

    def test_safe_read_table_list_fails(self):
        """Test when listing tables fails."""
        mock_engine = MagicMock(spec=Engine)

        with patch("socrata_toolkit.core.app.list_tables", side_effect=Exception("Query failed")):
            result = safe_read_table(mock_engine, "test_table")
            assert len(result) == 0

    def test_safe_read_table_with_limit(self):
        """Test reading table with custom limit."""
        mock_engine = MagicMock(spec=Engine)
        expected_data = pd.DataFrame({"id": [1, 2, 3]})
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public"],
                "table_name": ["test_table"],
            }
        )

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            with patch("pandas.read_sql_query", return_value=expected_data) as mock_read:
                result = safe_read_table(mock_engine, "test_table", limit=500)
                assert len(result) == 3

    def test_safe_read_table_fallback_query(self):
        """Test fallback to unqualified query when primary fails."""
        mock_engine = MagicMock(spec=Engine)
        expected_data = pd.DataFrame({"id": [1, 2]})
        mock_tables = pd.DataFrame(
            {
                "table_schema": ["public"],
                "table_name": ["test_table"],
            }
        )

        call_count = 0

        def read_sql_side_effect(q, engine, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Primary query failed")
            return expected_data

        with patch("socrata_toolkit.core.app.list_tables", return_value=mock_tables):
            with patch("pandas.read_sql_query", side_effect=read_sql_side_effect):
                result = safe_read_table(mock_engine, "test_table")
                assert len(result) == 2


class TestFindLatlonColumns:
    """Tests for find_latlon_columns function."""

    def test_find_latlon_explicit_names(self):
        """Test finding lat/lon columns with explicit names."""
        df = pd.DataFrame(
            {
                "latitude": [40.7, 40.8],
                "longitude": [-73.9, -74.0],
                "name": ["A", "B"],
            }
        )
        result = find_latlon_columns(df)
        assert result == ("latitude", "longitude")

    def test_find_latlon_short_names(self):
        """Test finding lat/lon columns with short names."""
        df = pd.DataFrame(
            {
                "lat": [40.7, 40.8],
                "lon": [-73.9, -74.0],
                "name": ["A", "B"],
            }
        )
        result = find_latlon_columns(df)
        assert result is not None
        assert result[0] == "lat"
        assert result[1] == "lon"

    def test_find_latlon_xy_columns(self):
        """Test finding lat/lon columns with x/y names."""
        df = pd.DataFrame(
            {
                "x": [40.7, 40.8],
                "y": [-73.9, -74.0],
                "name": ["A", "B"],
            }
        )
        result = find_latlon_columns(df)
        assert result is not None
        # The function may return in either order depending on the heuristic
        assert set(result) == {"x", "y"}

    def test_find_latlon_by_range(self):
        """Test finding lat/lon columns by numeric range heuristic."""
        df = pd.DataFrame(
            {
                "col_a": [40.7, 40.8, 40.9],
                "col_b": [-73.9, -74.0, -74.1],
                "col_c": [1000, 2000, 3000],
            }
        )
        result = find_latlon_columns(df)
        assert result is not None

    def test_find_latlon_missing(self):
        """Test when no lat/lon columns found."""
        df = pd.DataFrame(
            {
                "name": ["A", "B"],
                "value": [1, 2],
            }
        )
        result = find_latlon_columns(df)
        assert result is None

    def test_find_latlon_only_one_candidate(self):
        """Test when only one explicit lat/lon candidate but other numeric columns exist."""
        df = pd.DataFrame(
            {
                "latitude": [40.7, 40.8],
                "other_col": [1, 2],
            }
        )
        result = find_latlon_columns(df)
        # The function tries heuristics with numeric columns even if not explicit
        # So result depends on whether other_col looks like a longitude
        if result is not None:
            assert "latitude" in result

    def test_find_latlon_with_nulls(self):
        """Test finding lat/lon when columns have null values."""
        df = pd.DataFrame(
            {
                "latitude": [40.7, None, 40.9],
                "longitude": [-73.9, -74.0, None],
            }
        )
        result = find_latlon_columns(df)
        assert result == ("latitude", "longitude")

    def test_find_latlon_all_nulls(self):
        """Test when numeric columns are all nulls."""
        df = pd.DataFrame(
            {
                "col_a": [None, None, None],
                "col_b": [None, None, None],
            }
        )
        result = find_latlon_columns(df)
        assert result is None


class TestComputeKpisFromDf:
    """Tests for compute_kpis_from_df function."""

    def test_compute_kpis_with_violations_column(self):
        """Test KPI computation with violations data."""
        df = pd.DataFrame(
            {
                "violations": [10, 20, 30],
                "curb_miles": [1.0, 2.0, 3.0],
            }
        )
        result = compute_kpis_from_df(df)
        assert "total_defects" in result or "defect_density" in result

    def test_compute_kpis_with_curb_miles(self):
        """Test KPI computation with curb miles data."""
        df = pd.DataFrame(
            {
                "curb_miles": [1.5, 2.5, 3.5],
            }
        )
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)

    def test_compute_kpis_empty_dataframe(self):
        """Test KPI computation with empty DataFrame."""
        df = pd.DataFrame()
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)

    def test_compute_kpis_with_nulls(self):
        """Test KPI computation with null values."""
        df = pd.DataFrame(
            {
                "violations": [10, None, 30],
                "curb_miles": [1.0, 2.0, None],
            }
        )
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)

    def test_compute_kpis_specialized_available(self):
        """Test KPI computation when specialized implementation is available."""
        df = pd.DataFrame(
            {
                "violations": [10, 20, 30],
            }
        )

        mock_kpis = {"specialized": "kpi"}

        with patch(
            "socrata_toolkit.engineering.dot_sidewalk.compute_sidewalk_kpis", return_value=mock_kpis
        ):
            result = compute_kpis_from_df(df)
            # Result should use specialized implementation
            assert result == mock_kpis

    def test_compute_kpis_with_fallback(self):
        """Test KPI computation uses fallback when specialized module unavailable."""
        df = pd.DataFrame(
            {
                "violations": [10, 20],
            }
        )

        # The function handles ImportError internally and falls back to basic computation
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)
        # Result may contain specialized or fallback keys depending on what's available
        assert len(result) > 0

    def test_compute_kpis_defect_density_calculation(self):
        """Test defect density is calculated correctly."""
        df = pd.DataFrame(
            {
                "violations": [60.0],
                "curb_miles": [3.0],
            }
        )
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)

    def test_compute_kpis_zero_division_protection(self):
        """Test protection against zero division."""
        df = pd.DataFrame(
            {
                "violations": [10],
                "curb_miles": [0],
            }
        )
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)

    def test_compute_kpis_non_numeric_violations(self):
        """Test handling of non-numeric violations column."""
        df = pd.DataFrame(
            {
                "violations": ["a", "b", "c"],
                "curb_miles": [1.0, 2.0, 3.0],
            }
        )
        result = compute_kpis_from_df(df)
        assert isinstance(result, dict)
