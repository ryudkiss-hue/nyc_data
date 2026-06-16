"""Comprehensive tests for pipeline streaming and sync modules.

Covers stream_pipeline (dry-run and live paths) and sync_dataset.
All network, database, and LLM calls are mocked. Heavy external
dependencies (psycopg, pymongo, tqdm) are either mocked or patched
at import time so tests run without them installed.
"""
from __future__ import annotations
import pytest


import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers to build mock Socrata clients
# ---------------------------------------------------------------------------

def _mock_client(batches: list[list[dict]], row_count: int | None = None) -> MagicMock:
    """Build a mock SocrataClient that streams pre-defined batches.

    By default the reported remote ``row_count`` matches the total number of
    rows across ``batches`` so the live pipeline's end-of-cycle reconciliation
    audit (local count vs remote count) succeeds. Pass ``row_count`` explicitly
    to simulate a specific remote total (e.g. for dry-run estimate checks).
    """
    client = MagicMock()
    meta = MagicMock()
    if row_count is None:
        row_count = sum(len(b) for b in batches)
    meta.row_count = row_count
    client.get_metadata.return_value = meta
    client.fetch_json.return_value = iter(batches)
    client._headers.return_value = {}
    client.config = MagicMock()
    return client

def _simple_batch() -> list[dict]:
    return [{"id": "1", "borough": "MN", "description": "crack"}]

# ===========================================================================
# stream_pipeline tests
# ===========================================================================

class TestStreamPipelineDryRun:
    """Tests for the dry-run branch of stream_pipeline."""

    def test_dry_run_returns_dict(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        report = stream_pipeline(client, "data.example.com", "test-123", targets={}, dry_run=True)
        assert isinstance(report, dict)

    def test_dry_run_reports_rows_sampled(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        report = stream_pipeline(client, "data.example.com", "test-123", targets={}, dry_run=True)
        assert report["rows_sampled"] == 1

    def test_dry_run_reports_total_estimate(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()], row_count=42)
        report = stream_pipeline(client, "data.example.com", "test-123", targets={}, dry_run=True)
        assert report["total_estimate"] == 42

    def test_dry_run_postgres_target_included_when_enabled(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {"postgres": {"enabled": True, "table": "test_tbl", "conflict_column": "id"}}
        with patch("socrata_toolkit.core.pipeline.generate_postgres_preview", return_value="SQL"):
            report = stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=True)
        assert "postgres" in report["targets"]

    def test_dry_run_mongo_target_included_when_enabled(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {"mongo": {"enabled": True}}
        report = stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=True)
        assert "mongo" in report["targets"]
        assert "sample" in report["targets"]["mongo"]

    def test_dry_run_xlsx_target_included_when_enabled(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {"xlsx": {"enabled": True}}
        report = stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=True)
        assert "xlsx" in report["targets"]

    def test_dry_run_empty_batch_reports_zero_rows(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([[]])
        report = stream_pipeline(client, "d.com", "abc", targets={}, dry_run=True)
        assert report["rows_sampled"] == 0

    def test_dry_run_metadata_error_sets_total_to_none(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        client.get_metadata.side_effect = RuntimeError("API unavailable")
        report = stream_pipeline(client, "d.com", "abc", targets={}, dry_run=True)
        assert report["total_estimate"] is None

    def test_chunk_size_sets_page_size(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        stream_pipeline(client, "d.com", "abc", targets={}, dry_run=True, chunk_size=500)
        assert client.config.page_size == 500

class TestStreamPipelineLive:
    """Tests for the live (non-dry-run) path of stream_pipeline."""

    def test_live_jsonl_target_creates_file(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {"xlsx": {"enabled": True}}
        report = stream_pipeline(client, "d.com", "abc123", targets=targets, dry_run=False)
        assert "jsonl_backup" in report["targets"]["xlsx"]

    def test_live_returns_row_count(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        batch = [{"id": str(i)} for i in range(5)]
        client = _mock_client([batch])
        targets = {"xlsx": {"enabled": True}}
        report = stream_pipeline(client, "d.com", "abc123", targets=targets, dry_run=False)
        assert report["rows"] == 5

    def test_live_progress_callback_called(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {}
        cb = MagicMock()
        stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=False, progress_callback=cb)
        cb.assert_called()

    def test_live_empty_batch_skipped(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([[], _simple_batch()])
        targets = {}
        report = stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=False)
        assert report["rows"] == 1

    def test_live_postgres_not_enabled_skips_pg(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {"postgres": {"enabled": False}}
        report = stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=False)
        assert "postgres" not in report["targets"]

    def test_live_postgres_import_error_raised(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {"postgres": {"enabled": True, "dsn": "fake", "table": "t", "conflict_column": "id"}}
        with patch.dict("sys.modules", {"psycopg": None}):
            with pytest.raises((ImportError, Exception)):
                stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=False)

    def test_live_governance_processor_called_per_row(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        batch = [{"id": "a"}, {"id": "b"}]
        client = _mock_client([batch])
        targets = {}
        processor = MagicMock()

        fake_cdc = MagicMock()

        with patch("socrata_toolkit.pipeline.streaming.CDCEvent", fake_cdc):
            stream_pipeline(client, "d.com", "abc", targets=targets,
                            dry_run=False, governance_processor=processor)

        assert processor.process_event.call_count == 2

    def test_live_governance_exception_does_not_crash(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {}
        processor = MagicMock()
        processor.process_event.side_effect = RuntimeError("governance error")

        fake_cdc = MagicMock()
        with patch("socrata_toolkit.pipeline.streaming.CDCEvent", fake_cdc):
            report = stream_pipeline(client, "d.com", "abc", targets=targets,
                                     dry_run=False, governance_processor=processor)
        assert report["rows"] == 1

    def test_live_max_rows_passed_to_fetch_json(self):
        from socrata_toolkit.pipeline.streaming import stream_pipeline

        client = _mock_client([_simple_batch()])
        targets = {}
        stream_pipeline(client, "d.com", "abc", targets=targets, dry_run=False, max_rows=50)
        client.fetch_json.assert_called_once_with("d.com", "abc", max_rows=50)

# ===========================================================================
# sync_dataset tests
# ===========================================================================

class TestSyncDataset:
    """Tests for the sync_dataset function."""

    def _make_duckdb_manager(self, has_table: bool = False, last_updated=None):
        """Return a mock DuckDBManager."""
        manager = MagicMock()
        conn = MagicMock()
        manager.conn = conn

        if last_updated:
            manager.query.return_value.fetchone.return_value = (last_updated,)
        else:
            manager.query.side_effect = Exception("no table")

        if has_table:
            conn.execute.return_value.fetchall.return_value = [("test_table",)]
        else:
            conn.execute.return_value.fetchall.return_value = []
        return manager

    def _sync_patches(self, mock_client, mock_manager, mock_repo):
        """Return a list of context managers that fully mock sync_dataset deps."""
        return [
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ]

    def test_returns_integer_count(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        batch = [{"id": "1", "updated_at": "2026-01-01"}]
        mock_client = _mock_client([batch])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert isinstance(count, int)

    def test_syncs_batch_with_id_column(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        batch = [{"id": "1", "updated_at": "2026-01-01"}]
        mock_client = _mock_client([batch])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert count == 1
        mock_repo.upsert_dataframe.assert_called_once()

    def test_syncs_batch_with_at_id_column(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        batch = [{"@id": "row-1", "updated_at": "2026-01-01"}]
        mock_client = _mock_client([batch])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert count == 1

    def test_empty_batches_skipped(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        mock_client = _mock_client([[], []])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert count == 0

    def test_incremental_fetch_uses_where_clause(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        mock_client = _mock_client([[]])
        mock_manager = self._make_duckdb_manager(last_updated="2025-01-01")
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        call_kwargs = mock_client.fetch_json.call_args
        assert call_kwargs is not None
        assert "where" in call_kwargs.kwargs or (len(call_kwargs.args) > 2)

    def test_token_set_on_client_config(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        mock_client = _mock_client([[]])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at", token="tok123")

        assert mock_client.config.app_token == "tok123"

    def test_fetch_exception_returns_partial_count(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        mock_client = MagicMock()
        mock_client.config = MagicMock()

        def _fail_on_second(domain, fourfour, **kwargs):
            yield [{"id": "1", "updated_at": "2026-01-01"}]
            raise RuntimeError("network failure")

        mock_client.fetch_json.side_effect = _fail_on_second
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert count == 1

    def test_multi_batch_accumulates_count(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        batch1 = [{"id": str(i), "updated_at": "2026-01-01"} for i in range(3)]
        batch2 = [{"id": str(i + 3), "updated_at": "2026-01-02"} for i in range(2)]
        mock_client = _mock_client([batch1, batch2])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert count == 5

    def test_tqdm_absent_does_not_crash(self):
        from socrata_toolkit.pipeline.sync import sync_dataset

        batch = [{"id": "1", "updated_at": "2026-01-01"}]
        mock_client = _mock_client([batch])
        mock_manager = self._make_duckdb_manager()
        mock_repo = MagicMock()

        with (
            patch("socrata_toolkit.pipeline.sync.DuckDBManager", return_value=mock_manager),
            patch("socrata_toolkit.pipeline.sync.SocrataClient", return_value=mock_client),
            patch("socrata_toolkit.pipeline.sync.DuckDBRepository", return_value=mock_repo),
            patch("socrata_toolkit.pipeline.sync.tqdm", None),
        ):
            count = sync_dataset("d.com", "abc", ":memory:", "test_table", "updated_at")

        assert count == 1
