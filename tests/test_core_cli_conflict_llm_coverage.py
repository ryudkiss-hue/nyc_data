"""Coverage tests for core.cli conflict, llm-augment, and export-geojson commands."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
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
    r.text = json.dumps(json_value)
    r.raise_for_status = MagicMock()
    return r


# ---------------------------------------------------------------------------
# conflict
# ---------------------------------------------------------------------------

class TestConflictCommand:
    def test_no_proposed_source(self, runner):
        with patch("socrata_toolkit.core.cli._client", return_value=MagicMock()):
            res = runner.invoke(main, ["conflict", "--ref-file", "x.json"])
        assert res.exit_code != 0
        assert "proposed" in res.output

    def test_no_ref_source(self, runner, tmp_path):
        pf = tmp_path / "proposed.json"
        pd.DataFrame({"geometry": ["POINT(0 0)"]}).to_json(pf)
        with patch("socrata_toolkit.core.cli._client", return_value=MagicMock()):
            res = runner.invoke(main, ["conflict", "--proposed-file", str(pf)])
        assert res.exit_code != 0
        assert "ref" in res.output.lower()

    def test_conflict_summary_dry_run(self, runner, tmp_path):
        pf = tmp_path / "proposed.csv"
        rf = tmp_path / "ref.csv"
        pd.DataFrame({"geometry": ["POINT(0 0)"]}).to_csv(pf, index=False)
        pd.DataFrame({"geometry": ["POINT(0 0)"]}).to_csv(rf, index=False)
        resolver = MagicMock()
        summary = SimpleNamespace(conflict_count=1, total=1)
        resolver.resolve_conflicts.return_value = (pd.DataFrame({"a": [1]}), summary)
        with patch("socrata_toolkit.core.cli._client", return_value=MagicMock()), \
             patch("socrata_toolkit.core.cli.ConflictResolver", return_value=resolver):
            res = runner.invoke(main, [
                "conflict", "--proposed-file", str(pf), "--ref-file", str(rf), "--dry-run",
            ])
        assert res.exit_code == 0
        assert "Dry-run" in res.output

    def test_conflict_writes_outputs(self, runner, tmp_path):
        pf = tmp_path / "proposed.json"
        rf = tmp_path / "ref.json"
        pd.DataFrame({"geometry": ["POINT(0 0)"]}).to_json(pf)
        pd.DataFrame({"geometry": ["POINT(0 0)"]}).to_json(rf)
        out_gj = tmp_path / "out.geojson"
        out_xlsx = tmp_path / "out.xlsx"
        resolver = MagicMock()
        resolver.resolve_conflicts.return_value = (pd.DataFrame({"a": [1]}), SimpleNamespace(conflict_count=0))
        resolver.export_geojson.return_value = {"type": "FeatureCollection", "features": []}
        resolver.generate_construction_list.return_value = pd.DataFrame({"loc": ["L1"]})
        with patch("socrata_toolkit.core.cli._client", return_value=MagicMock()), \
             patch("socrata_toolkit.core.cli.ConflictResolver", return_value=resolver), \
             patch("socrata_toolkit.core.cli.XLSXExporter") as mock_xlsx:
            res = runner.invoke(main, [
                "conflict", "--proposed-file", str(pf), "--ref-file", str(rf),
                "--out-geojson", str(out_gj), "--out-xlsx", str(out_xlsx),
            ])
        assert res.exit_code == 0
        assert out_gj.exists()
        assert "Wrote GeoJSON" in res.output
        mock_xlsx.return_value.write.assert_called_once()

    def test_conflict_fetches_from_socrata(self, runner):
        client = MagicMock()
        client.fetch_json.side_effect = [
            iter([[{"geometry": "POINT(0 0)"}]]),
            iter([[{"geometry": "POINT(0 0)"}]]),
        ]
        resolver = MagicMock()
        resolver.resolve_conflicts.return_value = (pd.DataFrame(), SimpleNamespace(conflict_count=0))
        with patch("socrata_toolkit.core.cli._client", return_value=client), \
             patch("socrata_toolkit.core.cli.ConflictResolver", return_value=resolver):
            res = runner.invoke(main, [
                "conflict",
                "--proposed-domain", "d", "--proposed-fourfour", "aaaa-1111",
                "--ref-domain", "d", "--ref-fourfour", "bbbb-2222", "--dry-run",
            ])
        assert res.exit_code == 0
        assert client.fetch_json.call_count == 2


# ---------------------------------------------------------------------------
# llm-augment
# ---------------------------------------------------------------------------

class TestLlmAugment:
    def test_llm_augment_writes_output(self, runner, tmp_path):
        client = MagicMock()
        client.fetch_json.return_value = iter([[{"id": 1, "description": "crack"}]])
        out = tmp_path / "augmented.json"
        tagged = pd.DataFrame({"id": [1], "description": ["crack"], "_llm_tag": ["surface"]})
        with patch("socrata_toolkit.core.cli._client", return_value=client), \
             patch("socrata_toolkit.core.cli.augment_dataframe_with_llm", return_value=tagged):
            res = runner.invoke(main, [
                "llm-augment", "data.cityofnewyork.us", "abc1-2345",
                "--text-column", "description", "--out", str(out),
            ])
        assert res.exit_code == 0
        assert out.exists()
        assert "LLM-augmented" in res.output


# ---------------------------------------------------------------------------
# export geojson (geopandas)
# ---------------------------------------------------------------------------

class TestExportGeojson:
    REG = {"inspection": {"fourfour": "dntt-gqwq"}}

    def test_export_geojson_with_geopandas(self, runner, tmp_path):
        pytest.importorskip("geopandas")
        rows = [{"id": 1, "the_geom": {"type": "Point", "coordinates": [0, 0]}}]
        out = tmp_path / "out.geojson"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        # The export command writes the raw GeoJSON text from Socrata's .geojson endpoint
        geojson_resp = MagicMock()
        geojson_resp.text = json.dumps({"type": "FeatureCollection", "features": []})
        geojson_resp.raise_for_status = MagicMock()
        session.get.return_value = geojson_resp
        with patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG), \
             patch("socrata_toolkit.core.cli._make_session", return_value=session), \
             patch("socrata_toolkit.core.cli.HAS_GEOPANDAS", True):
            res = runner.invoke(main, [
                "export", "inspection", "--format", "geojson", "--output", str(out),
            ])
        assert res.exit_code == 0
        assert out.exists()
        assert "GeoJSON written" in res.output

    def test_export_geojson_request_error(self, runner, tmp_path):
        import requests

        session = MagicMock()
        session.get.side_effect = requests.RequestException("fail")
        with patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG), \
             patch("socrata_toolkit.core.cli._make_session", return_value=session), \
             patch("socrata_toolkit.core.cli.HAS_GEOPANDAS", True):
            res = runner.invoke(main, [
                "export", "inspection", "--format", "geojson", "--output", str(tmp_path / "x.geojson"),
            ])
        assert res.exit_code != 0
