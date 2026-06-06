"""Comprehensive tests for analyst.config module."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from socrata_toolkit.analyst.config import (
    AnalystProfile,
    SourceConfig,
    _parse_source,
    load_profile,
)


class TestSourceConfig:
    """Tests for SourceConfig dataclass."""

    def test_minimal_source_config(self):
        config = SourceConfig(type="excel")
        assert config.type == "excel"
        assert config.path is None
        assert config.sheet == 0
        assert config.domain is None
        assert config.fourfour is None
        assert config.table is None
        assert config.dsn_env == "PG_DSN"
        assert config.max_rows is None
        assert config.column_map == {}

    def test_source_config_with_path(self):
        config = SourceConfig(
            type="excel",
            path="/path/to/file.xlsx",
            sheet=1,
        )
        assert config.path == "/path/to/file.xlsx"
        assert config.sheet == 1

    def test_source_config_socrata(self):
        config = SourceConfig(
            type="socrata",
            domain="data.cityofnewyork.us",
            fourfour="dntt-gqwq",
        )
        assert config.type == "socrata"
        assert config.domain == "data.cityofnewyork.us"
        assert config.fourfour == "dntt-gqwq"

    def test_source_config_postgres(self):
        config = SourceConfig(
            type="postgres",
            table="violations",
            dsn_env="PG_DSN",
            max_rows=50000,
        )
        assert config.type == "postgres"
        assert config.table == "violations"
        assert config.max_rows == 50000

    def test_source_config_with_column_map(self):
        column_map = {"old_name": "new_name", "id": "violation_id"}
        config = SourceConfig(type="excel", column_map=column_map)
        assert config.column_map == column_map
        assert config.column_map["id"] == "violation_id"


class TestAnalystProfile:
    """Tests for AnalystProfile dataclass."""

    def test_minimal_profile(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
        )
        assert profile.profile_name == "test"
        assert profile.sources == {}
        assert profile.outputs_dir == "outputs/analyst_pack"
        assert profile.output_formats == ["xlsx", "md", "html", "json"]
        assert profile.steps == {}
        assert profile.contract_ids == []
        assert profile.offline is False

    def test_profile_with_sources(self):
        sources = {
            "violations": SourceConfig(type="socrata", fourfour="dntt-gqwq"),
            "complaints": SourceConfig(type="excel", path="/data/complaints.xlsx"),
        }
        profile = AnalystProfile(profile_name="test", sources=sources)
        assert len(profile.sources) == 2
        assert "violations" in profile.sources
        assert profile.sources["violations"].fourfour == "dntt-gqwq"

    def test_profile_with_custom_outputs(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            outputs_dir="custom/output",
            output_formats=["json", "csv"],
        )
        assert profile.outputs_dir == "custom/output"
        assert profile.output_formats == ["json", "csv"]

    def test_profile_with_steps(self):
        steps = {
            "prioritize": True,
            "contract_report": False,
            "publish": True,
        }
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps=steps,
        )
        assert profile.steps["prioritize"] is True
        assert profile.steps["contract_report"] is False
        assert profile.steps["publish"] is True

    def test_profile_with_contract_ids(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            contract_ids=["CONTRACT001", "CONTRACT002"],
        )
        assert len(profile.contract_ids) == 2
        assert "CONTRACT001" in profile.contract_ids


class TestAnalystProfileProperties:
    """Tests for AnalystProfile property methods."""

    def test_prioritize_true_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.prioritize is True

    def test_prioritize_false_when_disabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"prioritize": False},
        )
        assert profile.prioritize is False

    def test_contract_report_true_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.contract_report is True

    def test_contract_report_false_when_disabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"contract_report": False},
        )
        assert profile.contract_report is False

    def test_program_kpi_true_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.program_kpi is True

    def test_program_kpi_false_when_disabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"program_kpi": False},
        )
        assert profile.program_kpi is False

    def test_inquiry_templates_true_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.inquiry_templates is True

    def test_inquiry_templates_false_when_disabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"inquiry_templates": False},
        )
        assert profile.inquiry_templates is False

    def test_construction_diff_true_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.construction_diff is True

    def test_construction_diff_false_when_disabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"construction_diff": False},
        )
        assert profile.construction_diff is False

    def test_executive_summary_true_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.executive_summary is True

    def test_executive_summary_false_when_disabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"executive_summary": False},
        )
        assert profile.executive_summary is False

    def test_publish_false_by_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.publish is False

    def test_publish_true_when_enabled(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"publish": True},
        )
        assert profile.publish is True

    def test_publish_profile_path_from_publish_profile(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"publish_profile": "/path/to/profile.yaml"},
        )
        assert profile.publish_profile_path == "/path/to/profile.yaml"

    def test_publish_profile_path_from_publish_profile_path(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"publish_profile_path": "/path/to/profile.yaml"},
        )
        assert profile.publish_profile_path == "/path/to/profile.yaml"

    def test_publish_profile_path_none_when_not_set(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.publish_profile_path is None

    def test_conflict_buffer_m_default(self):
        profile = AnalystProfile(profile_name="test", sources={})
        assert profile.conflict_buffer_m == 20.0

    def test_conflict_buffer_m_custom(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"conflicts": {"buffer_m": 50}},
        )
        assert profile.conflict_buffer_m == 50.0

    def test_conflict_buffer_m_non_dict_conflicts(self):
        profile = AnalystProfile(
            profile_name="test",
            sources={},
            steps={"conflicts": "some_string"},
        )
        assert profile.conflict_buffer_m == 20.0


class TestParseSource:
    """Tests for _parse_source function."""

    def test_parse_minimal_source(self):
        raw = {"type": "excel"}
        config = _parse_source("test_source", raw)
        assert config.type == "excel"
        assert config.path is None

    def test_parse_excel_source(self):
        raw = {
            "type": "excel",
            "path": "/data/file.xlsx",
            "sheet": 2,
        }
        config = _parse_source("test_source", raw)
        assert config.type == "excel"
        assert config.path == "/data/file.xlsx"
        assert config.sheet == 2

    def test_parse_socrata_source(self):
        raw = {
            "type": "socrata",
            "domain": "data.cityofnewyork.us",
            "fourfour": "dntt-gqwq",
            "max_rows": 10000,
        }
        config = _parse_source("violations", raw)
        assert config.type == "socrata"
        assert config.domain == "data.cityofnewyork.us"
        assert config.fourfour == "dntt-gqwq"
        assert config.max_rows == 10000

    def test_parse_postgres_source(self):
        raw = {
            "type": "postgres",
            "table": "violations",
            "dsn_env": "PROD_DSN",
            "max_rows": 50000,
        }
        config = _parse_source("db_source", raw)
        assert config.type == "postgres"
        assert config.table == "violations"
        assert config.dsn_env == "PROD_DSN"
        assert config.max_rows == 50000

    def test_parse_source_with_column_map(self):
        raw = {
            "type": "excel",
            "path": "/data/file.xlsx",
            "column_map": {
                "ViolationID": "violation_id",
                "DateCreated": "created_at",
            },
        }
        config = _parse_source("test_source", raw)
        assert config.column_map["ViolationID"] == "violation_id"
        assert config.column_map["DateCreated"] == "created_at"

    def test_parse_source_default_sheet(self):
        raw = {"type": "excel", "path": "/data/file.xlsx"}
        config = _parse_source("test_source", raw)
        assert config.sheet == 0

    def test_parse_source_default_type_to_excel(self):
        raw = {"path": "/data/file.xlsx"}
        config = _parse_source("test_source", raw)
        assert config.type == "excel"


class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_profile("/nonexistent/path/profile.yaml")

    def test_load_minimal_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_path.write_text(
                "profile_name: test_profile\nsources: {}\n",
                encoding="utf-8",
            )
            profile = load_profile(config_path)
            assert profile.profile_name == "test_profile"
            assert profile.sources == {}

    def test_load_profile_with_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources:
  violations:
    type: socrata
    domain: data.cityofnewyork.us
    fourfour: dntt-gqwq
  complaints:
    type: excel
    path: /data/complaints.xlsx
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert len(profile.sources) == 2
            assert "violations" in profile.sources
            assert profile.sources["violations"].type == "socrata"
            assert "complaints" in profile.sources

    def test_load_profile_with_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
outputs:
  dir: custom/outputs
  formats: [json, csv, xlsx]
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.outputs_dir == "custom/outputs"
            assert profile.output_formats == ["json", "csv", "xlsx"]

    def test_load_profile_with_steps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
steps:
  prioritize: false
  contract_report: true
  publish: true
  publish_profile: /path/to/publish.yaml
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.steps["prioritize"] is False
            assert profile.steps["contract_report"] is True
            assert profile.steps["publish"] is True

    def test_load_profile_with_contract_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
contract_ids:
  - CONTRACT001
  - CONTRACT002
  - CONTRACT003
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert len(profile.contract_ids) == 3
            assert "CONTRACT001" in profile.contract_ids

    def test_load_profile_with_duckdb_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
duckdb_path: /custom/path/db.duckdb
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.duckdb_path == "/custom/path/db.duckdb"

    def test_load_profile_with_offline_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
offline: true
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.offline is True

    def test_load_profile_with_budget_codes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
budget_codes: /path/to/budget_codes.xlsx
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.budget_codes_path == "/path/to/budget_codes.xlsx"

    def test_load_profile_profile_name_from_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "my_profile.yaml"
            config_path.write_text("sources: {}\n", encoding="utf-8")
            profile = load_profile(config_path)
            # Should use filename stem if profile_name not specified
            assert profile.profile_name == "my_profile"

    def test_load_profile_with_role_and_role_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
role: analyst
role_profile: /path/to/role_profile.yaml
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.role == "analyst"
            assert profile.role_profile_path == "/path/to/role_profile.yaml"

    def test_load_profile_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "empty.yaml"
            config_path.write_text("", encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.profile_name == "empty"
            assert profile.sources == {}

    def test_load_profile_conflict_buffer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "profile.yaml"
            config_text = """
profile_name: test
sources: {}
steps:
  conflicts:
    buffer_m: 100
"""
            config_path.write_text(config_text, encoding="utf-8")
            profile = load_profile(config_path)
            assert profile.conflict_buffer_m == 100.0
