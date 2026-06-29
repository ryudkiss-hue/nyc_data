"""Coverage tests for core.cli review group, migrate, and alerts command bodies.

These exercise execution paths (not just --help) by patching the review store,
psycopg, and alert manager dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main

pytestmark = pytest.mark.skip(reason="Legacy CLI test - command removed")


@pytest.fixture
def runner():
    return CliRunner()


def _store_cm(store):
    """Wrap a mock store so `with ReviewStore() as s` yields it."""
    cm = MagicMock()
    cm.__enter__.return_value = store
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------------------------
# review list
# ---------------------------------------------------------------------------


class TestReviewList:
    def test_list_empty(self, runner):
        store = MagicMock()
        store.list.return_value = pd.DataFrame()
        with (
            patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)),
            patch("socrata_toolkit.core.cli._default_pack_date", return_value="2024-01-01"),
        ):
            result = runner.invoke(main, ["review", "list"])
        assert result.exit_code == 0
        assert "(no decisions)" in result.output

    def test_list_with_rows(self, runner):
        store = MagicMock()
        store.list.return_value = pd.DataFrame({"key": ["k1"], "status": ["resolved"]})
        with (
            patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)),
            patch("socrata_toolkit.core.cli._default_pack_date", return_value="2024-01-01"),
        ):
            result = runner.invoke(main, ["review", "list", "--kind", "conflict"])
        assert result.exit_code == 0
        assert "k1" in result.output

    def test_list_json_out(self, runner, tmp_path):
        store = MagicMock()
        store.list.return_value = pd.DataFrame({"key": ["k1"]})
        out = tmp_path / "decisions.json"
        with (
            patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)),
            patch("socrata_toolkit.core.cli._default_pack_date", return_value="2024-01-01"),
        ):
            result = runner.invoke(main, ["review", "list", "--json-out", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "Wrote 1 decisions" in result.output


# ---------------------------------------------------------------------------
# review set
# ---------------------------------------------------------------------------


class TestReviewSet:
    def test_set_conflict(self, runner):
        store = MagicMock()
        with patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)):
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--pack-date",
                    "2024-01-01",
                    "--kind",
                    "conflict",
                    "--key-type",
                    "location_id",
                    "--key",
                    "L1",
                    "--status",
                    "resolved",
                ],
            )
        assert result.exit_code == 0
        assert "OK" in result.output
        store.set_conflict.assert_called_once()

    def test_set_approval(self, runner):
        store = MagicMock()
        with patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)):
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--pack-date",
                    "2024-01-01",
                    "--kind",
                    "approval",
                    "--key-type",
                    "contract_id",
                    "--key",
                    "C1",
                    "--status",
                    "approved",
                    "--reason",
                    "ok",
                ],
            )
        assert result.exit_code == 0
        store.set_approval.assert_called_once()

    def test_set_missing_pack_date_raises(self, runner):
        with patch("socrata_toolkit.core.cli._default_pack_date", return_value=""):
            result = runner.invoke(
                main,
                [
                    "review",
                    "set",
                    "--kind",
                    "conflict",
                    "--key-type",
                    "location_id",
                    "--key",
                    "L1",
                    "--status",
                    "resolved",
                ],
            )
        assert result.exit_code != 0
        assert "pack-date" in result.output


# ---------------------------------------------------------------------------
# review export
# ---------------------------------------------------------------------------


class TestReviewExport:
    def test_export_with_artifacts(self, runner, tmp_path):
        pack = tmp_path / "2024-01-01"
        pack.mkdir()
        store = MagicMock()
        store.export_for_pack.return_value = {"xlsx": str(pack / "decisions.xlsx")}
        with patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)):
            result = runner.invoke(main, ["review", "export", "--pack", str(pack)])
        assert result.exit_code == 0
        assert "xlsx" in result.output

    def test_export_no_artifacts(self, runner, tmp_path):
        pack = tmp_path / "2024-01-01"
        pack.mkdir()
        store = MagicMock()
        store.export_for_pack.return_value = {}
        with patch("socrata_toolkit.review.store.ReviewStore", return_value=_store_cm(store)):
            result = runner.invoke(main, ["review", "export", "--pack", str(pack)])
        assert result.exit_code == 0
        assert "No decisions found" in result.output


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------


class TestMigrate:
    def test_migrate_no_dsn(self, runner, monkeypatch):
        monkeypatch.delenv("PG_DSN", raising=False)
        result = runner.invoke(main, ["migrate"])
        assert result.exit_code != 0
        assert "DSN" in result.output

    def test_migrate_no_files(self, runner, tmp_path):
        result = runner.invoke(
            main, ["migrate", "--dsn", "postgresql://x", "--migrations-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "No migration files found" in result.output

    def test_migrate_applies_files(self, runner, tmp_path):
        (tmp_path / "001_init.sql").write_text("CREATE TABLE t (id INT);")
        (tmp_path / "002_more.sql").write_text("ALTER TABLE t ADD COLUMN v INT;")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        with patch("psycopg.connect", return_value=mock_conn):
            result = runner.invoke(
                main, ["migrate", "--dsn", "postgresql://x", "--migrations-dir", str(tmp_path)]
            )
        assert result.exit_code == 0
        assert "Migrations applied" in result.output
        assert mock_cursor.execute.call_count == 2


# ---------------------------------------------------------------------------
# alerts (preview path)
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_alerts_preview(self, runner):
        result = runner.invoke(main, ["alerts", "--preview"])
        assert result.exit_code == 0

    def test_alerts_send_requires_recipients(self, runner):
        result = runner.invoke(main, ["alerts", "--send"])
        assert result.exit_code != 0
        assert "recipients" in result.output

    def test_alerts_persist_requires_dsn(self, runner, monkeypatch):
        monkeypatch.delenv("PG_DSN", raising=False)
        result = runner.invoke(main, ["alerts", "--persist"])
        assert result.exit_code != 0
        assert "pg-dsn" in result.output
