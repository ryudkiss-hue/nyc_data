"""Coverage tests for core.cli operational commands.

Covers toolkit_search, sync, db-status, setup/wizard, the conflict-detect
GeoJSON-export path (geopandas), and the dataset-health manual-format fallback.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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
        # SODA3 count via session.post; metadata via session.get.
        session.post.return_value = _resp([{"c": "100"}])
        session.get.side_effect = [
            _resp({"rowsUpdatedAt": int(datetime.now(timezone.utc).timestamp())}),
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

class TestAnalyzeAndTextInsights:
    """analyze and text-insights run real profiling over fetch_json batches."""

    def test_analyze_cmd(self, runner):
        client = MagicMock()
        client.fetch_json.return_value = iter([[
            {"id": 1, "borough": "MN", "value": 10},
            {"id": 2, "borough": "BX", "value": 20},
            {"id": 3, "borough": "MN", "value": 30},
        ]])
        with patch("socrata_toolkit.core.cli._client", return_value=client), \
             patch("socrata_toolkit.core.cli.load_state", return_value=None):
            res = runner.invoke(main, [
                "analyze", "data.cityofnewyork.us", "abc1-2345", "--key-column", "id",
            ])
        assert res.exit_code == 0
        payload = json.loads(res.output)
        assert payload["profile"]["row_count"] == 3
        assert "quality" in payload

    def test_text_insights_cmd(self, runner, tmp_path):
        client = MagicMock()
        client.fetch_json.return_value = iter([[
            {"id": 1, "description": "cracked sidewalk trip hazard near curb"},
            {"id": 2, "description": "pothole pooling water after rain"},
        ]])
        out = tmp_path / "tagged.json"
        with patch("socrata_toolkit.core.cli._client", return_value=client), \
             patch("socrata_toolkit.core.cli.load_state", return_value=None):
            res = runner.invoke(main, [
                "text-insights", "data.cityofnewyork.us", "abc1-2345",
                "--text-column", "description", "--out", str(out),
            ])
        assert res.exit_code == 0
        payload = json.loads(res.output)
        assert payload["row_count"] == 2
        assert out.exists()

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

class TestSpatialJoinAndDefaultPackDate:
    def test_spatial_join_cmd(self, runner, tmp_path):
        from types import SimpleNamespace
        from unittest.mock import patch

        import pandas as pd

        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        out = tmp_path / "joined.json"
        pd.DataFrame({"the_geom": ["POINT(0 0)"]}).to_json(left)
        pd.DataFrame({"the_geom": ["POINT(0 0)"]}).to_json(right)

        result = SimpleNamespace(
            joined=pd.DataFrame({"a": [1]}), conflict_rate=0.5, overlap_count=1
        )
        with patch("socrata_toolkit.core.cli.spatial_intersects_join", return_value=result):
            res = runner.invoke(main, [
                "spatial-join", "--left-json", str(left), "--right-json", str(right),
                "--left-geom-col", "the_geom", "--right-geom-col", "the_geom", "--out", str(out),
            ])
        assert res.exit_code == 0
        assert out.exists()
        assert "overlap_count" in res.output

    def test_default_pack_date_happy(self):
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch

        from socrata_toolkit.core.cli import _default_pack_date

        prof = SimpleNamespace(state_dir=Path("/tmp"))
        with patch("socrata_toolkit.core.profiles.ensure_profile_exists", return_value=prof), \
             patch("socrata_toolkit.core.state.load_state", return_value={"last_run_date": "2024-05-01"}):
            assert _default_pack_date() == "2024-05-01"

    def test_default_pack_date_exception_returns_empty(self):
        from unittest.mock import patch

        from socrata_toolkit.core.cli import _default_pack_date

        with patch("socrata_toolkit.core.profiles.ensure_profile_exists", side_effect=RuntimeError("no profile")):
            assert _default_pack_date() == ""
