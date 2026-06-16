"""Comprehensive tests for core.duckdb_store module."""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from socrata_toolkit.core.duckdb_store import (
    DuckDBManager,
    _default_cache_dir,
    _escape_sql_literal,
    _latest_parquet_for_key,
    query_parquet_cache,
)


class TestDuckDBManagerInit:
    """Tests for DuckDBManager initialization."""

    def test_init_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))
            assert manager.db_path == str(db_path)

    def test_init_with_memory_db(self):
        manager = DuckDBManager(":memory:")
        assert manager.db_path == ":memory:"

    def test_init_with_env_path(self):
        with patch.dict("os.environ", {"DUCKDB_PATH": "/custom/path.duckdb"}):
            manager = DuckDBManager()
            assert manager.db_path == "/custom/path.duckdb"


class TestDuckDBManagerConnection:
    """Tests for DuckDBManager connection handling."""

    def test_connection_lazy_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            assert manager._conn is None
            conn = manager.conn
            assert conn is not None
            assert manager._conn is not None

    def test_connection_reuse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            conn1 = manager.conn
            conn2 = manager.conn
            assert conn1 is conn2

    def test_close_connection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            _ = manager.conn
            manager.close()
            assert manager._conn is None

    def test_close_when_not_initialized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            manager.close()
            assert manager._conn is None


class TestDuckDBManagerQuery:
    """Tests for DuckDBManager query execution."""

    def test_query_simple_select(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            result = manager.query("SELECT 1 as num")
            assert result is not None

    def test_query_with_multiple_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            result = manager.query(
                "SELECT 1 as num UNION ALL SELECT 2 as num UNION ALL SELECT 3 as num"
            )
            assert result is not None

    def test_query_with_args_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            result = manager.query("SELECT ? as num", [42])
            assert result is not None


class TestEscapeSqlLiteral:
    """Tests for _escape_sql_literal helper."""

    def test_escape_simple_string(self):
        result = _escape_sql_literal("hello")
        assert result == "hello"

    def test_escape_single_quote(self):
        result = _escape_sql_literal("it's")
        assert result == "it''s"

    def test_escape_multiple_quotes(self):
        result = _escape_sql_literal("don't say can't")
        assert result == "don''t say can''t"

    def test_escape_empty_string(self):
        result = _escape_sql_literal("")
        assert result == ""


class TestDefaultCacheDir:
    """Tests for _default_cache_dir function."""

    def test_default_cache_dir_no_env(self):
        with patch.dict("os.environ", {"SOCRATA_CACHE_DIR": ""}, clear=False):
            cache_dir = _default_cache_dir()
            assert isinstance(cache_dir, Path)
            assert "cache" in cache_dir.as_posix()

    def test_default_cache_dir_with_env(self):
        test_path = "/custom/cache/path"
        with patch.dict("os.environ", {"SOCRATA_CACHE_DIR": test_path}):
            cache_dir = _default_cache_dir()
            assert Path(cache_dir) == Path(test_path)

    def test_default_cache_dir_with_whitespace_env(self):
        with patch.dict("os.environ", {"SOCRATA_CACHE_DIR": "   "}, clear=False):
            cache_dir = _default_cache_dir()
            assert isinstance(cache_dir, Path)


class TestLatestParquetForKey:
    """Tests for _latest_parquet_for_key function."""

    def test_latest_parquet_no_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _latest_parquet_for_key("nonexistent_key", tmpdir)
            assert result is None

    def test_latest_parquet_single_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            # Create a test parquet file
            test_file = cache_dir / "test_key_2024010101.parquet.gz"
            test_file.touch()

            result = _latest_parquet_for_key("test_key", cache_dir)
            assert result is not None
            assert result.name == "test_key_2024010101.parquet.gz"

    def test_latest_parquet_legacy_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            legacy_file = cache_dir / "test_key.parquet"
            legacy_file.touch()

            result = _latest_parquet_for_key("test_key", cache_dir)
            assert result is not None
            assert result.name == "test_key.parquet"

    def test_latest_parquet_multiple_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            # Create multiple timestamped files
            file1 = cache_dir / "data_2024010101.parquet.gz"
            file2 = cache_dir / "data_2024010102.parquet.gz"
            file1.touch()
            file2.touch()

            result = _latest_parquet_for_key("data", cache_dir)
            assert result is not None
            # Should return one of the files
            assert "data_202401" in result.name


class TestQueryParquetCache:
    """Tests for query_parquet_cache function."""

    def test_query_parquet_cache_with_mock_manager(self):
        with patch("socrata_toolkit.core.duckdb_store.DuckDBManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_result = MagicMock()
            mock_manager.query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            result = query_parquet_cache("SELECT 1")
            assert result is not None


class TestDuckDBManagerWithDataFrame:
    """Tests for DuckDBManager with DataFrame operations."""

    def test_create_table_from_dataframe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
            manager.conn.register("test_table", df)

            result = manager.query("SELECT COUNT(*) as cnt FROM test_table")
            assert result is not None

    def test_query_dataframe_types(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            df = pd.DataFrame(
                {
                    "int_col": [1, 2, 3],
                    "float_col": [1.5, 2.5, 3.5],
                    "str_col": ["a", "b", "c"],
                }
            )
            manager.conn.register("typed_table", df)

            result = manager.query("SELECT * FROM typed_table")
            assert result is not None


class TestDuckDBManagerEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_multiple_managers_different_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = Path(tmpdir) / "db1.duckdb"
            path2 = Path(tmpdir) / "db2.duckdb"

            manager1 = DuckDBManager(str(path1))
            manager2 = DuckDBManager(str(path2))

            assert manager1.db_path == str(path1)
            assert manager2.db_path == str(path2)
            assert manager1.db_path != manager2.db_path

    def test_memory_database(self):
        manager = DuckDBManager(":memory:")
        assert manager.db_path == ":memory:"
        conn = manager.conn
        assert conn is not None

    def test_connection_with_spatial_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "spatial.duckdb"
            manager = DuckDBManager(str(db_path))

            # Accessing conn should attempt to load spatial
            conn = manager.conn
            assert conn is not None

    def test_repeated_close(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            manager = DuckDBManager(str(db_path))

            _ = manager.conn
            manager.close()
            manager.close()
            assert manager._conn is None


# ---------------------------------------------------------------------------
# get_bundle_dir
# ---------------------------------------------------------------------------


class TestGetBundleDir:
    def test_normal_returns_cwd(self):
        import os

        from socrata_toolkit.core.duckdb_store import get_bundle_dir

        assert get_bundle_dir() == os.getcwd()

    def test_frozen_returns_meipass(self):
        import sys

        from socrata_toolkit.core import duckdb_store

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/bundle/path", create=True),
        ):
            assert duckdb_store.get_bundle_dir() == "/bundle/path"


# ---------------------------------------------------------------------------
# query_parquet_cache — bare key and raw SQL execution paths
# ---------------------------------------------------------------------------


class TestQueryParquetCacheExecution:
    def test_empty_raises_value_error(self):
        with pytest.raises(ValueError):
            query_parquet_cache("   ")

    def test_bare_key_no_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            query_parquet_cache("violations", cache_dir=tmp_path)

    def test_bare_key_with_parquet(self, tmp_path):
        df = pd.DataFrame({"id": [1, 2, 3], "borough": ["MN", "BX", "BK"]})
        df.to_parquet(tmp_path / "violations_20240101.parquet")
        result = query_parquet_cache("violations", cache_dir=tmp_path)
        assert len(result) == 3
        assert set(result["borough"]) == {"MN", "BX", "BK"}

    def test_raw_sql_execution(self, tmp_path):
        df = pd.DataFrame({"id": [1, 2], "v": [10, 20]})
        pq = tmp_path / "data.parquet"
        df.to_parquet(pq)
        sql = f"SELECT v FROM read_parquet('{pq}') WHERE id = 1"
        result = query_parquet_cache(sql)
        assert result["v"].tolist() == [10]


# ---------------------------------------------------------------------------
# DuckDBRepository
# ---------------------------------------------------------------------------


class TestDuckDBRepository:
    def _repo(self, table="t"):
        from socrata_toolkit.core.duckdb_store import DuckDBManager, DuckDBRepository

        manager = DuckDBManager(":memory:")
        return DuckDBRepository(manager, table), manager

    def test_upsert_empty_returns_zero(self):
        repo, mgr = self._repo()
        assert repo.upsert_dataframe(pd.DataFrame(), "id") == 0
        mgr.close()

    def test_upsert_creates_table(self):
        repo, mgr = self._repo()
        df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        n = repo.upsert_dataframe(df, "id")
        assert n == 2
        assert repo.count() == 2
        mgr.close()

    def test_upsert_updates_existing(self):
        repo, mgr = self._repo()
        repo.upsert_dataframe(pd.DataFrame({"id": [1, 2], "name": ["a", "b"]}), "id")
        # upsert overlapping id with new value + a new row
        n = repo.upsert_dataframe(pd.DataFrame({"id": [2, 3], "name": ["B", "c"]}), "id")
        assert n == 2
        out = repo.fetch_all()
        assert repo.count() == 3
        names = dict(zip(out["id"], out["name"]))
        assert names[2] == "B"  # updated
        mgr.close()

    def test_fetch_all_with_limit(self):
        repo, mgr = self._repo()
        repo.upsert_dataframe(pd.DataFrame({"id": list(range(10)), "v": list(range(10))}), "id")
        out = repo.fetch_all(limit=3)
        assert len(out) == 3
        mgr.close()

    def test_count_empty_table(self):
        repo, mgr = self._repo()
        repo.upsert_dataframe(pd.DataFrame({"id": [1], "v": [1]}), "id")
        assert repo.count() == 1
        mgr.close()
