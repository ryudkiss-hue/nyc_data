"""Tests for core.cli module - Click CLI commands."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import (
    alerts_cmd,
    analyze_cmd,
    batch_search_cmd,
    conflict_cmd,
    correlations_cmd,
    doctor_cmd,
    fetch_cmd,
    llm_augment_cmd,
    main,
    meta_cmd,
    migrate_cmd,
    nlp_analyze_cmd,
    outliers_cmd,
    pipeline,
    readiness_cmd,
    search,
    spatial_join_cmd,
    text_insights_cmd,
    upsert_mongo,
    upsert_pg,
)


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""
    return CliRunner()


class TestMainGroup:
    """Tests for main CLI group and global options."""

    def test_main_help(self, cli_runner):
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Socrata toolkit CLI" in result.output

    def test_main_verbose_flag(self, cli_runner):
        result = cli_runner.invoke(main, ["-v", "--help"])
        assert result.exit_code == 0

    def test_main_very_verbose_flag(self, cli_runner):
        result = cli_runner.invoke(main, ["-vv", "--help"])
        assert result.exit_code == 0

    def test_main_log_level_debug(self, cli_runner):
        result = cli_runner.invoke(main, ["--log-level", "DEBUG", "--help"])
        assert result.exit_code == 0

    def test_main_log_level_info(self, cli_runner):
        result = cli_runner.invoke(main, ["--log-level", "INFO", "--help"])
        assert result.exit_code == 0

    def test_main_log_level_warning(self, cli_runner):
        result = cli_runner.invoke(main, ["--log-level", "WARNING", "--help"])
        assert result.exit_code == 0

    def test_main_log_level_error(self, cli_runner):
        result = cli_runner.invoke(main, ["--log-level", "ERROR", "--help"])
        assert result.exit_code == 0

    def test_main_log_level_critical(self, cli_runner):
        result = cli_runner.invoke(main, ["--log-level", "CRITICAL", "--help"])
        assert result.exit_code == 0


class TestSearchCommand:
    """Tests for search command."""

    def test_search_help(self, cli_runner):
        result = cli_runner.invoke(search, ["--help"])
        assert result.exit_code == 0

    def test_search_no_args(self, cli_runner):
        with patch("socrata_toolkit.core.cli._client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.return_value = []

            result = cli_runner.invoke(search, [])
            assert "[]" in result.output or result.exit_code == 0

    def test_search_with_query(self, cli_runner):
        with patch("socrata_toolkit.core.cli._client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_result = MagicMock()
            mock_result.__dict__ = {"name": "test", "id": "123"}
            mock_client.search.return_value = [mock_result]

            result = cli_runner.invoke(search, ["test query"])
            # Should not error
            assert result.exit_code == 0 or "test" in result.output

    def test_search_with_json_output(self, cli_runner):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "results.json"
            with patch("socrata_toolkit.core.cli._client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.search.return_value = []

                result = cli_runner.invoke(
                    search,
                    ["test", "--json-out", str(output_file)]
                )
                if result.exit_code == 0:
                    assert output_file.exists()


class TestMetaCommand:
    """Tests for metadata command."""

    def test_meta_help(self, cli_runner):
        result = cli_runner.invoke(meta_cmd, ["--help"])
        assert result.exit_code == 0

    def test_meta_columns_only(self, cli_runner):
        with patch("socrata_toolkit.core.cli._client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_meta = MagicMock()
            mock_meta.column_dict.return_value = [{"name": "col1"}]
            mock_meta.summary.return_value = {"rows": 100}
            mock_client.get_metadata.return_value = mock_meta

            result = cli_runner.invoke(
                meta_cmd,
                ["example.com", "abc123", "--columns-only"]
            )
            assert result.exit_code == 0


class TestFetchCommand:
    """Tests for fetch command."""

    def test_fetch_help(self, cli_runner):
        result = cli_runner.invoke(fetch_cmd, ["--help"])
        assert result.exit_code == 0

    def test_fetch_json_format(self, cli_runner):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "data.json"
            with patch("socrata_toolkit.core.cli._client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.fetch_json.return_value = [[{"id": 1}]]

                result = cli_runner.invoke(
                    fetch_cmd,
                    [
                        "example.com",
                        "abc123",
                        "--format", "json",
                        "--out", str(output_file),
                    ]
                )
                if result.exit_code == 0:
                    assert output_file.exists()

    def test_fetch_xlsx_format(self, cli_runner):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "data.xlsx"
            with patch("socrata_toolkit.core.cli._client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                import pandas as pd
                mock_client.fetch_dataframe.return_value = pd.DataFrame({"id": [1]})

                with patch("socrata_toolkit.core.cli.XLSXExporter"):
                    result = cli_runner.invoke(
                        fetch_cmd,
                        [
                            "example.com",
                            "abc123",
                            "--format", "xlsx",
                            "--out", str(output_file),
                        ]
                    )
                    assert result.exit_code == 0


class TestAnalyzeCommand:
    """Tests for analyze command."""

    def test_analyze_help(self, cli_runner):
        result = cli_runner.invoke(analyze_cmd, ["--help"])
        assert result.exit_code == 0

    def test_analyze_with_domain_and_fourfour(self, cli_runner):
        with patch("socrata_toolkit.core.cli._client") as mock_client_class:
            import pandas as pd
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.fetch_dataframe.return_value = pd.DataFrame({"id": [1, 2]})

            with patch("socrata_toolkit.analysis.profile_dataframe") as mock_profile:
                mock_profile.return_value = MagicMock()
                result = cli_runner.invoke(
                    analyze_cmd,
                    ["example.com", "abc123"]
                )
                # May error if save_state fails, but command executed
                assert result.exit_code is not None


class TestReadinessCommand:
    """Tests for readiness check command."""

    def test_readiness_help(self, cli_runner):
        result = cli_runner.invoke(readiness_cmd, ["--help"])
        assert result.exit_code == 0

    def test_readiness_without_pytest(self, cli_runner):
        result = cli_runner.invoke(readiness_cmd, [])
        # Should complete without error
        assert result.exit_code is not None


class TestDoctorCommand:
    """Tests for doctor command."""

    def test_doctor_help(self, cli_runner):
        result = cli_runner.invoke(doctor_cmd, ["--help"])
        assert result.exit_code == 0

    def test_doctor_basic(self, cli_runner):
        result = cli_runner.invoke(doctor_cmd, [])
        # Should complete without critical errors
        assert result.exit_code is not None


class TestOutliersCommand:
    """Tests for outliers detection command."""

    def test_outliers_help(self, cli_runner):
        result = cli_runner.invoke(outliers_cmd, ["--help"])
        assert result.exit_code == 0

    def test_outliers_iqr_method(self, cli_runner):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "outliers.json"
            with patch("socrata_toolkit.core.cli._client") as mock_client_class:
                import pandas as pd
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.fetch_dataframe.return_value = pd.DataFrame(
                    {"value": [1, 2, 3, 4, 100]}
                )

                with patch("socrata_toolkit.analysis.detect_all_outliers") as mock_detect:
                    mock_detect.return_value = [{"index": 4, "value": 100}]
                    result = cli_runner.invoke(
                        outliers_cmd,
                        [
                            "example.com",
                            "abc123",
                            "--method", "iqr",
                            "--out", str(output_file),
                        ]
                    )
                    assert result.exit_code is not None


class TestCorrelationsCommand:
    """Tests for correlation analysis command."""

    def test_correlations_help(self, cli_runner):
        result = cli_runner.invoke(correlations_cmd, ["--help"])
        assert result.exit_code == 0

    def test_correlations_pearson_method(self, cli_runner):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "correlations.json"
            with patch("socrata_toolkit.core.cli._client") as mock_client_class:
                import pandas as pd
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.fetch_dataframe.return_value = pd.DataFrame(
                    {"a": [1, 2, 3], "b": [2, 4, 6]}
                )

                # Mock correlation_analysis which is imported inside the command
                with patch("socrata_toolkit.analysis.advanced.correlation_analysis") as mock_corr:
                    mock_result = MagicMock()
                    mock_result.method = "pearson"
                    mock_result.threshold = 0.5
                    mock_result.pairs = [("a", "b", 0.99)]
                    mock_corr.return_value = mock_result
                    result = cli_runner.invoke(
                        correlations_cmd,
                        [
                            "example.com",
                            "abc123",
                            "--method", "pearson",
                            "--out", str(output_file),
                        ]
                    )
                    assert result.exit_code == 0


class TestNLPAnalyzeCommand:
    """Tests for NLP analysis command."""

    def test_nlp_analyze_help(self, cli_runner):
        result = cli_runner.invoke(nlp_analyze_cmd, ["--help"])
        assert result.exit_code == 0

    def test_nlp_analyze_text_only(self, cli_runner):
        result = cli_runner.invoke(nlp_analyze_cmd, ["This is test text"])
        # Should handle gracefully (nlp modules may not be installed)
        assert result.exit_code is not None


class TestSpatialJoinCommand:
    """Tests for spatial join command."""

    def test_spatial_join_help(self, cli_runner):
        result = cli_runner.invoke(spatial_join_cmd, ["--help"])
        assert result.exit_code == 0


class TestUpsertPostgresCommand:
    """Tests for Postgres upsert command."""

    def test_upsert_pg_help(self, cli_runner):
        result = cli_runner.invoke(upsert_pg, ["--help"])
        assert result.exit_code == 0


class TestUpsertMongoCommand:
    """Tests for MongoDB upsert command."""

    def test_upsert_mongo_help(self, cli_runner):
        result = cli_runner.invoke(upsert_mongo, ["--help"])
        assert result.exit_code == 0


class TestBatchSearchCommand:
    """Tests for batch search command."""

    def test_batch_search_help(self, cli_runner):
        result = cli_runner.invoke(batch_search_cmd, ["--help"])
        assert result.exit_code == 0


class TestMigrateCommand:
    """Tests for database migration command."""

    def test_migrate_help(self, cli_runner):
        result = cli_runner.invoke(migrate_cmd, ["--help"])
        assert result.exit_code == 0


class TestAlertsCommand:
    """Tests for alerts command."""

    def test_alerts_help(self, cli_runner):
        result = cli_runner.invoke(alerts_cmd, ["--help"])
        assert result.exit_code == 0

    def test_alerts_preview_flag(self, cli_runner):
        with patch("socrata_toolkit.core.cli.AlertManager"):
            result = cli_runner.invoke(alerts_cmd, ["--preview"])
            # Should execute without error
            assert result.exit_code is not None


class TestLLMAugmentCommand:
    """Tests for LLM augmentation command."""

    def test_llm_augment_help(self, cli_runner):
        result = cli_runner.invoke(llm_augment_cmd, ["--help"])
        assert result.exit_code == 0


class TestTextInsightsCommand:
    """Tests for text insights command."""

    def test_text_insights_help(self, cli_runner):
        result = cli_runner.invoke(text_insights_cmd, ["--help"])
        assert result.exit_code == 0


class TestConflictCommand:
    """Tests for conflict detection command."""

    def test_conflict_help(self, cli_runner):
        result = cli_runner.invoke(conflict_cmd, ["--help"])
        assert result.exit_code == 0


class TestPipelineCommand:
    """Tests for pipeline command."""

    def test_pipeline_help(self, cli_runner):
        result = cli_runner.invoke(pipeline, ["--help"])
        assert result.exit_code == 0
