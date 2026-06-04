"""Coverage tests for core.cli operational commands.

Covers toolkit_search, sync, db-status, setup/wizard, the conflict-detect
GeoJSON-export path (geopandas), and the dataset-health manual-format fallback.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def _resp(json_value):
    r = MagicMock()
    r.json.return_value = json_value
    r.ok = True
    r.raise_for_status = MagicMock()
    return r


# ---------------------------------------------------------------------------
# toolkit_search
# ---------------------------------------------------------------------------

class TestToolkitSearch:
    def test_search_echoes_results(self, runner):
        client = MagicMock()
        result = MagicMock()
        result.name = "Sidewalk Inspections"
        result.fourfour = "dntt-gqwq"
        result.domain = "data.cityofnewyork.us"
        client.search.return_value = [result]
        with patch("socrata_toolkit.core.cli._client", return_value=client):
            res = runner.invoke(main, ["toolkit-search", "-q", "sidewalk"])
        assert res.exit_code == 0
        assert "Sidewalk Inspections" in res.output
        assert "dntt-gqwq" in res.output

    def test_search_requires_query(self, runner):
        res = runner.invoke(main, ["toolkit-search"])
        assert res.exit_code == 2


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

class TestSync:
    def test_sync_reports_count(self, runner):
        with patch("socrata_toolkit.pipeline.sync_dataset", return_value=123):
            res = runner.invoke(main, [
                "sync", "-i", "dntt-gqwq", "--table", "inspections",
            ])
        assert res.exit_code == 0
        assert "123 rows" in res.output

    def test_sync_requires_table(self, runner):
        res = runner.invoke(main, ["sync", "-i", "dntt-gqwq"])
        assert res.exit_code == 2


# ---------------------------------------------------------------------------
# db-status
# ---------------------------------------------------------------------------

class TestDbStatus:
    def test_db_status_lists_tables(self, runner):
        mgr = MagicMock()
        # query("SHOW TABLES").fetchall() -> tables; query(count).fetchone() -> (n,)
        show = MagicMock()
        show.fetchall.return_value = [("inspections",), ("violations",)]
        count_q = MagicMock()
        count_q.fetchone.return_value = (42,)
        mgr.query.side_effect = [show, count_q, count_q]
        with patch("socrata_toolkit.core.duckdb_store.DuckDBManager", return_value=mgr):
            res = runner.invoke(main, ["db-status"])
        assert res.exit_code == 0
        assert "inspections: 42 rows" in res.output
        mgr.close.assert_called_once()

    def test_db_status_empty(self, runner):
        mgr = MagicMock()
        show = MagicMock()
        show.fetchall.return_value = []
        mgr.query.return_value = show
        with patch("socrata_toolkit.core.duckdb_store.DuckDBManager", return_value=mgr):
            res = runner.invoke(main, ["db-status"])
        assert res.exit_code == 0


# ---------------------------------------------------------------------------
# setup / wizard
# ---------------------------------------------------------------------------

class TestSetupWizard:
    def test_setup(self, runner):
        with patch("socrata_toolkit.install_wizard.run_wizard", return_value={"ok": True}) as rw, \
             patch("socrata_toolkit.install_wizard._print_summary") as ps:
            res = runner.invoke(main, ["setup", "--non-interactive", "--skip-checks"])
        assert res.exit_code == 0
        rw.assert_called_once()
        ps.assert_called_once()

    def test_wizard_alias(self, runner):
        with patch("socrata_toolkit.install_wizard.run_wizard", return_value={"ok": True}) as rw, \
             patch("socrata_toolkit.install_wizard._print_summary"):
            res = runner.invoke(main, ["wizard", "--non-interactive"])
        assert res.exit_code == 0
        rw.assert_called_once()


# ---------------------------------------------------------------------------
# conflict-detect GeoJSON export (geopandas path)
# ---------------------------------------------------------------------------

class TestConflictDetectGeoJSON:
    def test_geojson_export_with_geopandas(self, runner, tmp_path):
        pytest.importorskip("geopandas")
        rows = [
            {"bbl": "1", "latitude": "40.70", "longitude": "-74.01", "borough": "MANHATTAN"},
            {"bbl": "1", "latitude": "40.71", "longitude": "-74.02", "borough": "MANHATTAN"},
        ]
        out = tmp_path / "conflicts.geojson"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with patch("socrata_toolkit.core.cli._make_session", return_value=session), \
             patch("socrata_toolkit.core.cli.HAS_GEOPANDAS", True):
            res = runner.invoke(main, ["conflict-detect", "--output", str(out)])
        assert res.exit_code == 0
        assert out.exists()
        assert "GeoJSON written" in res.output

    def test_geojson_no_latlon_writes_json(self, runner, tmp_path):
        pytest.importorskip("geopandas")
        rows = [{"bbl": "1", "borough": "MANHATTAN"}, {"bbl": "1", "borough": "MANHATTAN"}]
        out = tmp_path / "conflicts.geojson"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with patch("socrata_toolkit.core.cli._make_session", return_value=session), \
             patch("socrata_toolkit.core.cli.HAS_GEOPANDAS", True):
            res = runner.invoke(main, ["conflict-detect", "--output", str(out)])
        assert res.exit_code == 0
        assert out.exists()
        assert "no lat/lon" in res.output


# ---------------------------------------------------------------------------
# dataset health manual-format fallback (tabulate missing)
# ---------------------------------------------------------------------------

class TestDatasetHealthFallback:
    def test_manual_format_when_tabulate_missing(self, runner):
        from datetime import datetime

        reg = {"inspection": {"fourfour": "dntt-gqwq"}}
        session = MagicMock()
        session.get.side_effect = [
            _resp([{"c": "100"}]),
            _resp({"rowsUpdatedAt": int(datetime.utcnow().timestamp())}),
        ]
        # Force the `from tabulate import tabulate` inside the command to fail.
        with patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=reg), \
             patch("socrata_toolkit.core.cli._make_session", return_value=session), \
             patch.dict(sys.modules, {"tabulate": None}):
            res = runner.invoke(main, ["dataset", "health", "--key", "inspection"])
        assert res.exit_code == 0
        assert "inspection" in res.output


# ---------------------------------------------------------------------------
# _load_dataset_registry / _make_session helpers
# ---------------------------------------------------------------------------

class TestRegistryAndSession:
    def test_load_dataset_registry_real(self):
        from socrata_toolkit.core.cli import _load_dataset_registry

        reg = _load_dataset_registry()
        assert isinstance(reg, dict)
        assert len(reg) > 0
        # each entry has a fourfour
        first = next(iter(reg.values()))
        assert "fourfour" in first

    def test_make_session_has_adapters(self):
        from socrata_toolkit.core.cli import _make_session

        session = _make_session()
        assert session.get_adapter("https://x") is not None
        assert session.get_adapter("http://x") is not None
