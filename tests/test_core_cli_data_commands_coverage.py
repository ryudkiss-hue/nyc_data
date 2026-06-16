"""Coverage tests for core.cli v0.4.0 data commands.

Covers dataset health, conflict-detect, cache refresh, export, and nl-query.
These use module-level ``_load_dataset_registry()`` and ``_make_session()``,
so we patch those in ``socrata_toolkit.core.cli`` and feed mock HTTP responses.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def _resp(json_value, ok=True):
    r = MagicMock()
    r.json.return_value = json_value
    r.ok = ok
    r.text = json.dumps(json_value)
    r.raise_for_status = MagicMock()
    return r


REGISTRY = {"inspection": {"fourfour": "dntt-gqwq"}}

# ---------------------------------------------------------------------------
# dataset health
# ---------------------------------------------------------------------------


class TestDatasetHealth:
    def test_health_ok(self, runner):
        now_ts = int(datetime.now(timezone.utc).timestamp())
        session = MagicMock()
        # SODA3 count is fetched via session.post; metadata via session.get.
        session.post.return_value = _resp([{"c": "100"}])
        session.get.side_effect = [
            _resp({"rowsUpdatedAt": now_ts}),  # metadata (fresh)
        ]
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "health", "--key", "inspection"])
        assert result.exit_code == 0
        assert "inspection" in result.output
        assert "dntt-gqwq" in result.output

    def test_health_empty_dataset_exits_nonzero(self, runner):
        session = MagicMock()
        session.post.return_value = _resp([{"c": "0"}])  # count = 0 -> empty
        session.get.side_effect = [
            _resp({"rowsUpdatedAt": int(datetime.now(timezone.utc).timestamp())}),
        ]
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "health", "--key", "inspection"])
        assert result.exit_code == 1
        assert "empty" in result.output

    def test_health_stale_dataset_exits_nonzero(self, runner):
        old_ts = int(datetime(2017, 1, 1).timestamp())
        session = MagicMock()
        session.post.return_value = _resp([{"c": "50"}])
        session.get.side_effect = [
            _resp({"rowsUpdatedAt": old_ts}),  # very old -> stale
        ]
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(
                main, ["dataset", "health", "--key", "inspection", "--stale", "7"]
            )
        assert result.exit_code == 1
        assert "stale" in result.output

    def test_health_unknown_key(self, runner):
        session = MagicMock()
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "health", "--key", "nonexistent"])
        assert "unknown_key" in result.output
        session.get.assert_not_called()

    def test_health_request_error(self, runner):
        import requests

        session = MagicMock()
        session.get.side_effect = requests.RequestException("boom")
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "health", "--key", "inspection"])
        assert result.exit_code == 1
        assert "error" in result.output

    def test_health_empty_filter(self, runner):
        session = MagicMock()
        session.get.side_effect = [
            _resp([{"c": "0"}]),
            _resp({"rowsUpdatedAt": int(datetime.now(timezone.utc).timestamp())}),
        ]
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "health", "--key", "inspection", "--empty"])
        # empty dataset shown, exit 1 due to empty status
        assert result.exit_code == 1

    def test_health_sort_by_size(self, runner):
        session = MagicMock()
        session.post.return_value = _resp([{"c": "100"}])
        session.get.side_effect = [
            _resp({"rowsUpdatedAt": int(datetime.now(timezone.utc).timestamp())}),
        ]
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(
                main, ["dataset", "health", "--key", "inspection", "--sort-by", "size"]
            )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# conflict-detect
# ---------------------------------------------------------------------------


class TestConflictDetect:
    def test_conflict_detect_with_duplicates(self, runner):
        rows = [
            {"bbl": "100", "borough": "MANHATTAN"},
            {"bbl": "100", "borough": "MANHATTAN"},
            {"bbl": "200", "borough": "MANHATTAN"},
        ]
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with patch("socrata_toolkit.core.cli._make_session", return_value=session):
            result = runner.invoke(main, ["conflict-detect", "--borough", "MN"])
        assert result.exit_code == 0
        assert '"conflict_count": 1' in result.output

    def test_conflict_detect_no_rows(self, runner):
        session = MagicMock()
        session.get.return_value = _resp([])
        with patch("socrata_toolkit.core.cli._make_session", return_value=session):
            result = runner.invoke(main, ["conflict-detect", "--borough", "BX"])
        assert result.exit_code == 0
        assert '"rows_fetched": 0' in result.output

    def test_conflict_detect_request_error(self, runner):
        import requests

        session = MagicMock()
        session.get.side_effect = requests.RequestException("fail")
        with patch("socrata_toolkit.core.cli._make_session", return_value=session):
            result = runner.invoke(main, ["conflict-detect"])
        assert result.exit_code != 0

    def test_conflict_detect_output_json_fallback(self, runner, tmp_path):
        """Without geopandas, --output writes JSON instead of GeoJSON."""
        rows = [{"bbl": "1", "borough": "MANHATTAN"}, {"bbl": "1", "borough": "MANHATTAN"}]
        out = tmp_path / "conflicts.geojson"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
            patch("socrata_toolkit.core.cli.HAS_GEOPANDAS", False),
        ):
            result = runner.invoke(main, ["conflict-detect", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()


# ---------------------------------------------------------------------------
# cache refresh
# ---------------------------------------------------------------------------


class TestCacheRefresh:
    def test_cache_refresh_no_dir(self, runner, tmp_path, monkeypatch):
        monkeypatch.setenv("SOCRATA_CACHE_DIR", str(tmp_path / "missing"))
        result = runner.invoke(main, ["cache", "refresh", "inspection"])
        assert result.exit_code == 0
        assert "does not exist" in result.output

    def test_cache_refresh_no_matching_files(self, runner, tmp_path, monkeypatch):
        monkeypatch.setenv("SOCRATA_CACHE_DIR", str(tmp_path))
        result = runner.invoke(main, ["cache", "refresh", "inspection"])
        assert result.exit_code == 0
        assert "No cache files found" in result.output

    def test_cache_refresh_deletes_matching(self, runner, tmp_path, monkeypatch):
        monkeypatch.setenv("SOCRATA_CACHE_DIR", str(tmp_path))
        (tmp_path / "inspection_2024.parquet").write_text("x")
        (tmp_path / "inspection_meta.json").write_text("{}")
        (tmp_path / "violations.parquet").write_text("y")  # should not be deleted
        result = runner.invoke(main, ["cache", "refresh", "inspection"])
        assert result.exit_code == 0
        assert "Deleted 2 cache file(s)" in result.output
        assert not (tmp_path / "inspection_2024.parquet").exists()
        assert (tmp_path / "violations.parquet").exists()


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_csv(self, runner, tmp_path):
        rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
        out = tmp_path / "out.csv"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(
                main, ["export", "inspection", "--format", "csv", "--output", str(out)]
            )
        assert result.exit_code == 0
        assert out.exists()
        assert "CSV written" in result.output

    def test_export_parquet(self, runner, tmp_path):
        rows = [{"id": 1}]
        out = tmp_path / "out.parquet"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(
                main, ["export", "inspection", "--format", "parquet", "--output", str(out)]
            )
        assert result.exit_code == 0
        assert out.exists()

    def test_export_unknown_key(self, runner, tmp_path):
        with patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY):
            result = runner.invoke(
                main,
                ["export", "nope", "--format", "csv", "--output", str(tmp_path / "x.csv")],
            )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_export_geojson_without_geopandas(self, runner, tmp_path):
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli.HAS_GEOPANDAS", False),
        ):
            result = runner.invoke(
                main,
                [
                    "export",
                    "inspection",
                    "--format",
                    "geojson",
                    "--output",
                    str(tmp_path / "x.geojson"),
                ],
            )
        assert result.exit_code != 0
        assert "geopandas is required" in result.output

    def test_export_request_error(self, runner, tmp_path):
        import requests

        session = MagicMock()
        session.get.side_effect = requests.RequestException("fail")
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=REGISTRY),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(
                main,
                ["export", "inspection", "--format", "csv", "--output", str(tmp_path / "x.csv")],
            )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# nl-query (anthropic gating)
# ---------------------------------------------------------------------------


class TestNlQuery:
    def test_nl_query_without_anthropic(self, runner):
        with patch("socrata_toolkit.core.cli.HAS_ANTHROPIC", False):
            result = runner.invoke(main, ["nl-query", "how many violations?"])
        assert result.exit_code != 0
        assert "anthropic SDK is not installed" in result.output

    def test_nl_query_missing_api_key(self, runner, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("socrata_toolkit.core.cli.HAS_ANTHROPIC", True):
            result = runner.invoke(main, ["nl-query", "how many violations?"])
        assert result.exit_code != 0
        assert "ANTHROPIC_API_KEY" in result.output
