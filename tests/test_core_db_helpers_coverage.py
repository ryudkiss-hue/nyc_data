"""Tests for core.db_helpers module - Database helper utilities."""

from __future__ import annotations
import pytest


from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.core.db_helpers import build_fts_index_sql, ensure_fts_index


class TestBuildFtsIndexSql:
    """Tests for build_fts_index_sql function."""

    def test_build_fts_index_single_column(self):
        """Test building FTS index SQL for single column."""
        sql = build_fts_index_sql("documents", ["content"])
        assert "CREATE INDEX" in sql
        assert "documents" in sql
        assert "to_tsvector('english'" in sql
        assert "GIN" in sql

    def test_build_fts_index_multiple_columns(self):
        """Test building FTS index SQL for multiple columns."""
        sql = build_fts_index_sql("articles", ["title", "body"])
        assert "CREATE INDEX" in sql
        assert "to_tsvector('english'" in sql
        assert "COALESCE(title, '')" in sql
        assert "COALESCE(body, '')" in sql
        assert "||" in sql

    def test_build_fts_index_custom_language(self):
        """Test building FTS index with custom language."""
        sql = build_fts_index_sql("documents", ["content"], language="french")
        assert "to_tsvector('french'" in sql

    def test_build_fts_index_custom_name(self):
        """Test building FTS index with custom index name."""
        sql = build_fts_index_sql("documents", ["content"], index_name="my_custom_idx")
        assert '"my_custom_idx"' in sql

    def test_build_fts_index_schema_qualified_table(self):
        """Test building FTS index for schema-qualified table."""
        sql = build_fts_index_sql("public.documents", ["content"])
        assert "public.documents" in sql
        assert "public_documents" in sql

    def test_build_fts_index_empty_columns_raises(self):
        """Test that empty columns list raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            build_fts_index_sql("documents", [])

    def test_build_fts_index_quotes_stripped(self):
        """Test that quotes in column names are stripped from index name."""
        sql = build_fts_index_sql("documents", ['"content"', "title"])
        # Quotes should be stripped from index name generation
        # but COALESCE still references the column with quotes
        assert "documents_content_title_fts_idx" in sql or "documents_content_title" in sql

    def test_build_fts_index_dot_notation_columns(self):
        """Test building FTS index with dot notation in column names."""
        sql = build_fts_index_sql("documents", ["t1.content", "t2.description"])
        # Dots should be converted to underscores in index name
        assert "t1_content_t2_description_fts_idx" in sql

    def test_build_fts_index_gin_strategy(self):
        """Test that GIN strategy is used."""
        sql = build_fts_index_sql("documents", ["content"])
        assert "USING GIN" in sql

    def test_build_fts_index_if_not_exists(self):
        """Test that IF NOT EXISTS clause is present."""
        sql = build_fts_index_sql("documents", ["content"])
        assert "IF NOT EXISTS" in sql

    def test_build_fts_index_coalesce_columns(self):
        """Test that COALESCE is applied to all columns."""
        sql = build_fts_index_sql("articles", ["title", "body", "summary"])
        assert sql.count("COALESCE") == 3

    def test_build_fts_index_three_columns(self):
        """Test building index for three columns."""
        sql = build_fts_index_sql("pages", ["h1", "h2", "content"])
        assert "COALESCE(h1, '')" in sql
        assert "COALESCE(h2, '')" in sql
        assert "COALESCE(content, '')" in sql

    def test_build_fts_index_auto_index_name(self):
        """Test automatic index naming."""
        sql = build_fts_index_sql("my_table", ["col1", "col2"])
        # Index name should be auto-generated from table and column names
        assert "_fts_idx" in sql
        assert "my_table" in sql


class TestEnsureFtsIndex:
    """Tests for ensure_fts_index function."""

    def test_ensure_fts_index_success(self):
        """Test successful FTS index creation."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg = MagicMock()
        mock_psycopg.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"psycopg": mock_psycopg}):
            ensure_fts_index("postgresql://localhost/test", "documents", ["content"])
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_ensure_fts_index_multiple_columns(self):
        """Test FTS index creation with multiple columns."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg = MagicMock()
        mock_psycopg.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"psycopg": mock_psycopg}):
            ensure_fts_index("postgresql://localhost/test", "articles", ["title", "body"])
            mock_cursor.execute.assert_called_once()
            sql = mock_cursor.execute.call_args[0][0]
            assert "title" in sql
            assert "body" in sql

    def test_ensure_fts_index_custom_language(self):
        """Test FTS index creation with custom language."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg = MagicMock()
        mock_psycopg.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"psycopg": mock_psycopg}):
            ensure_fts_index(
                "postgresql://localhost/test", "documents", ["content"], language="spanish"
            )
            sql = mock_cursor.execute.call_args[0][0]
            assert "spanish" in sql

    def test_ensure_fts_index_psycopg_not_installed(self):
        """Test ImportError when psycopg not available."""

        # Mock the import to fail
        def mock_import_error(*args, **kwargs):
            raise ImportError("No module named 'psycopg'")

        # Patch builtins to make import fail for psycopg
        import builtins

        original_import = builtins.__import__

        def import_with_error(name, *args, **kwargs):
            if name == "psycopg":
                raise ImportError("No module named 'psycopg'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_with_error):
            with pytest.raises(ImportError, match="Install Postgres extras"):
                ensure_fts_index("postgresql://localhost/test", "documents", ["content"])

    def test_ensure_fts_index_connection_error(self):
        """Test handling of connection errors."""
        mock_psycopg = MagicMock()
        mock_psycopg.connect.side_effect = Exception("Connection failed")

        with patch.dict("sys.modules", {"psycopg": mock_psycopg}):
            with pytest.raises(Exception, match="Connection failed"):
                ensure_fts_index("postgresql://localhost/test", "documents", ["content"])

    def test_ensure_fts_index_sql_generation(self):
        """Test that ensure_fts_index generates correct SQL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg = MagicMock()
        mock_psycopg.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"psycopg": mock_psycopg}):
            ensure_fts_index("postgresql://localhost/test", "docs", ["content"])
            # Verify that the SQL generated contains expected components
            sql = mock_cursor.execute.call_args[0][0]
            assert "CREATE INDEX" in sql
            assert "docs" in sql
