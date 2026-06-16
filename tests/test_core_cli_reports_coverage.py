"""Coverage tests for core.cli report/analyst commands and nl-query happy path.

Covers report contract, dataset ramp-analysis, the analyst group (init-config,
run, publish), and the nl-query execution path with a stubbed anthropic module.
"""

from __future__ import annotations
import pytest


import json
import sys
import types
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
    r.text = json.dumps(json_value)
    r.raise_for_status = MagicMock()
    return r


# ---------------------------------------------------------------------------
# report contract
# ---------------------------------------------------------------------------


class TestReportContract:
    REG = {"street_construction_inspections": {"fourfour": "ydkf-mpxb"}}

    def test_contract_with_contractor_column(self, runner):
        rows = [
            {"contractor": "ACME", "id": 1},
            {"contractor": "ACME", "id": 2},
            {"contractor": "BETA", "id": 3},
        ]
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["report", "contract"])
        assert result.exit_code == 0
        assert "Contractor Performance Report" in result.output
        assert "ACME" in result.output

    def test_contract_without_contractor_column(self, runner):
        rows = [{"id": 1, "value": 10}]
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["report", "contract"])
        assert result.exit_code == 0
        assert "No contractor/applicant column" in result.output

    def test_contract_writes_text_output(self, runner, tmp_path):
        rows = [{"contractor": "ACME", "id": 1}]
        out = tmp_path / "report.txt"
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
            patch("socrata_toolkit.core.cli.HAS_WEASYPRINT", False),
        ):
            result = runner.invoke(main, ["report", "contract", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "Text report written" in result.output

    def test_contract_fallback_to_violations_key(self, runner):
        reg = {"violations": {"fourfour": "6kbp-uz6m"}}
        session = MagicMock()
        session.get.return_value = _resp([{"applicant": "X", "id": 1}])
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=reg),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["report", "contract"])
        assert result.exit_code == 0

    def test_contract_request_error(self, runner):
        import requests

        session = MagicMock()
        session.get.side_effect = requests.RequestException("fail")
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["report", "contract"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# dataset ramp-analysis
# ---------------------------------------------------------------------------


class TestDatasetRampAnalysis:
    REG = {"ramp_progress": {"fourfour": "e7gc-ub6z"}}

    def test_ramp_key_missing(self, runner):
        with patch("socrata_toolkit.core.cli._load_dataset_registry", return_value={}):
            result = runner.invoke(main, ["dataset", "ramp-analysis"])
        assert result.exit_code != 0
        assert "ramp_progress" in result.output

    def test_ramp_no_rows(self, runner):
        session = MagicMock()
        session.get.return_value = _resp([])
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "ramp-analysis", "--sample", "10"])
        assert result.exit_code == 0
        assert "No ramp data found" in result.output

    def test_ramp_request_error(self, runner):
        import requests

        session = MagicMock()
        session.get.side_effect = requests.RequestException("boom")
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
        ):
            result = runner.invoke(main, ["dataset", "ramp-analysis"])
        assert result.exit_code != 0

    def test_ramp_happy_path(self, runner):
        rows = [{"borough": "MN", "status": "complete"}]
        session = MagicMock()
        session.get.return_value = _resp(rows)
        mock_report = MagicMock()
        mock_report.to_table.return_value = "BOROUGH TABLE"
        mock_report.to_dict.return_value = {"overall_completion_rate": 0.8}
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
            patch(
                "socrata_toolkit.engineering.ramp_analysis.RampCompletionReportGenerator"
            ) as mock_gen,
        ):
            mock_gen.return_value.generate.return_value = mock_report
            result = runner.invoke(
                main, ["dataset", "ramp-analysis", "--sample", "100", "--include-ci"]
            )
        assert result.exit_code == 0
        assert "BOROUGH TABLE" in result.output

    def test_ramp_generation_value_error(self, runner):
        rows = [{"borough": "MN"}]
        session = MagicMock()
        session.get.return_value = _resp(rows)
        with (
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
            patch(
                "socrata_toolkit.engineering.ramp_analysis.RampCompletionReportGenerator"
            ) as mock_gen,
        ):
            mock_gen.return_value.generate.side_effect = ValueError("bad columns")
            result = runner.invoke(main, ["dataset", "ramp-analysis"])
        assert result.exit_code != 0
        assert "Report generation failed" in result.output


# ---------------------------------------------------------------------------
# analyst group
# ---------------------------------------------------------------------------


class TestAnalystGroup:
    def test_init_config_writes_template(self, runner, tmp_path):
        out = tmp_path / "profile.yaml"
        result = runner.invoke(main, ["analyst", "init-config", "--out", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "Wrote analyst profile template" in result.output

    def test_analyst_run(self, runner, tmp_path):
        profile = tmp_path / "profile.yaml"
        profile.write_text("profile_name: test\n")
        mock_result = MagicMock()
        mock_result.pack_dir = tmp_path / "pack"
        mock_result.artifacts = ["a.xlsx"]
        mock_result.warnings = []
        with patch("socrata_toolkit.analyst.run_analyst_pack", return_value=mock_result):
            result = runner.invoke(main, ["analyst", "run", "--profile", str(profile), "--dry-run"])
        assert result.exit_code == 0
        assert "artifacts" in result.output

    def test_analyst_publish(self, runner, tmp_path):
        profile = tmp_path / "pub.yaml"
        profile.write_text("dest: x\n")
        pack = tmp_path / "pack"
        pack.mkdir()
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"published": True}
        with patch("socrata_toolkit.analyst.publish.publish_pack", return_value=mock_report):
            result = runner.invoke(
                main,
                ["analyst", "publish", "--profile", str(profile), "--pack", str(pack), "--dry-run"],
            )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# nl-query happy path (stubbed anthropic)
# ---------------------------------------------------------------------------


class TestNlQueryHappyPath:
    REG = {"inspection": {"fourfour": "dntt-gqwq"}}

    def _stub_anthropic(self, soql_text):
        """Build a stub anthropic module returning a fixed SoQL string."""
        mod = types.ModuleType("anthropic")

        class _APIError(Exception):
            pass

        mod.APIError = _APIError

        message = MagicMock()
        message.content = [MagicMock(text=soql_text)]
        client = MagicMock()
        client.messages.create.return_value = message
        mod.Anthropic = MagicMock(return_value=client)
        return mod

    def test_nl_query_executes_generated_soql(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        session = MagicMock()
        # first call: sample for columns; second: query execution
        session.get.side_effect = [
            _resp([{"borough": "MN", "violations": 3}]),
            _resp([{"borough": "MN", "count": 5}]),
        ]
        stub = self._stub_anthropic("SELECT borough, count(*) GROUP BY borough")
        with (
            patch("socrata_toolkit.core.cli.HAS_ANTHROPIC", True),
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
            patch.dict(sys.modules, {"anthropic": stub}),
        ):
            result = runner.invoke(main, ["nl-query", "violations per borough"])
        assert result.exit_code == 0
        assert "Generated SoQL" in result.output

    def test_nl_query_forbidden_keyword_blocked(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        session = MagicMock()
        session.get.return_value = _resp([{"borough": "MN"}])
        stub = self._stub_anthropic("DROP TABLE inspections")
        with (
            patch("socrata_toolkit.core.cli.HAS_ANTHROPIC", True),
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch("socrata_toolkit.core.cli._make_session", return_value=session),
            patch.dict(sys.modules, {"anthropic": stub}),
        ):
            result = runner.invoke(main, ["nl-query", "drop everything"])
        assert result.exit_code != 0
        assert "forbidden keyword" in result.output

    def test_nl_query_unknown_dataset(self, runner, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        stub = self._stub_anthropic("SELECT *")
        with (
            patch("socrata_toolkit.core.cli.HAS_ANTHROPIC", True),
            patch("socrata_toolkit.core.cli._load_dataset_registry", return_value=self.REG),
            patch.dict(sys.modules, {"anthropic": stub}),
        ):
            result = runner.invoke(main, ["nl-query", "q", "--dataset", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output
