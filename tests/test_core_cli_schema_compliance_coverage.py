"""Coverage tests for core.cli schema and compliance command bodies.

Covers execution paths (not just --help) for the schema group (list, current,
diff, validate, check-compatibility) and compliance group (ada-violations,
report). Schema happy-paths mock SchemaRegistry; compliance commands run against
the real bundled ADA rule set.
"""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main

@pytest.fixture
def runner():
    return CliRunner()

def _col(dtype, nullable=True, position=0, sample_value=None):
    return SimpleNamespace(dtype=dtype, nullable=nullable, position=position, sample_value=sample_value)

def _schema(dataset_id="inspection", version=1, columns=None, row_count=100):
    return SimpleNamespace(
        dataset_id=dataset_id,
        version=version,
        captured_at=datetime(2024, 1, 1),
        row_count=row_count,
        columns=columns or {"a": _col("int"), "b": _col("text")},
        metadata={},
    )

# ---------------------------------------------------------------------------
# compliance group (real bundled rules)
# ---------------------------------------------------------------------------

class TestComplianceCommands:
    def test_ada_violations_default(self, runner):
        result = runner.invoke(main, ["compliance", "ada-violations"])
        assert result.exit_code == 0
        assert "ADA-" in result.output

    def test_ada_violations_severity_filter(self, runner):
        result = runner.invoke(main, ["compliance", "ada-violations", "--severity", "high"])
        assert result.exit_code == 0

    def test_ada_violations_json_out(self, runner, tmp_path):
        out = tmp_path / "rules.json"
        result = runner.invoke(main, ["compliance", "ada-violations", "--json-out", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert isinstance(json.loads(out.read_text()), list)

    def test_report_default(self, runner):
        result = runner.invoke(main, ["compliance", "report"])
        assert result.exit_code == 0
        assert "ADA Compliance Rule Summary" in result.output

    def test_report_material_filter(self, runner):
        result = runner.invoke(main, ["compliance", "report", "--material", "asphalt"])
        assert result.exit_code == 0

    def test_report_json_out(self, runner, tmp_path):
        out = tmp_path / "report.json"
        result = runner.invoke(main, ["compliance", "report", "--json-out", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        payload = json.loads(out.read_text())
        assert "total_rules" in payload

# ---------------------------------------------------------------------------
# schema diff
# ---------------------------------------------------------------------------

class TestSchemaDiff:
    def test_diff_version1_missing(self, runner):
        result = runner.invoke(main, ["schema", "diff", "inspection", "1", "2"])
        assert result.exit_code == 0
        assert "Version 1 not found" in result.output

    def test_diff_version2_missing(self, runner):
        mock_reg = MagicMock()
        mock_reg.get_schema_version.side_effect = [_schema(version=1), None]
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "diff", "inspection", "1", "2"])
        assert result.exit_code == 0
        assert "Version 2 not found" in result.output

    def test_diff_no_changes(self, runner):
        cols = {"a": _col("int"), "b": _col("text")}
        mock_reg = MagicMock()
        mock_reg.get_schema_version.side_effect = [
            _schema(version=1, columns=cols),
            _schema(version=2, columns=dict(cols)),
        ]
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "diff", "inspection", "1", "2"])
        assert result.exit_code == 0
        assert "No changes" in result.output

    def test_diff_with_changes(self, runner):
        v1 = {"a": _col("int"), "b": _col("text")}
        v2 = {"a": _col("float"), "c": _col("text")}  # a type-change, b deleted, c added
        mock_reg = MagicMock()
        mock_reg.get_schema_version.side_effect = [
            _schema(version=1, columns=v1),
            _schema(version=2, columns=v2),
        ]
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "diff", "inspection", "1", "2"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["change_count"] == 3
        types = {c["type"] for c in payload["changes"]}
        assert types == {"COLUMN_DELETION", "COLUMN_ADDITION", "TYPE_CHANGE"}

# ---------------------------------------------------------------------------
# schema validate
# ---------------------------------------------------------------------------

class TestSchemaValidate:
    def test_validate_no_schema_raises(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = None
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "validate", "inspection", str(jsonl)])
        assert result.exit_code != 0
        assert "No schema found" in result.output

    def test_validate_happy(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\n{"a": 2}\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg), \
             patch("socrata_toolkit.core.cli.SchemaValidator") as mock_val:
            mock_val.return_value.validate_batch.return_value = (2, [])
            result = runner.invoke(main, ["schema", "validate", "inspection", str(jsonl)])
        assert result.exit_code == 0
        assert "Valid records: 2" in result.output

    def test_validate_with_errors(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\n{"a": "bad"}\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg), \
             patch("socrata_toolkit.core.cli.SchemaValidator") as mock_val:
            mock_val.return_value.validate_batch.return_value = (1, ["row 2: type error"])
            result = runner.invoke(main, ["schema", "validate", "inspection", str(jsonl)])
        assert result.exit_code == 0
        assert "Invalid records: 1" in result.output
        assert "row 2: type error" in result.output

    def test_validate_malformed_line(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\nNOT JSON\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg), \
             patch("socrata_toolkit.core.cli.SchemaValidator") as mock_val:
            mock_val.return_value.validate_batch.return_value = (1, [])
            result = runner.invoke(main, ["schema", "validate", "inspection", str(jsonl)])
        assert result.exit_code == 0
        assert "Error parsing line 2" in result.output

# ---------------------------------------------------------------------------
# schema check-compatibility
# ---------------------------------------------------------------------------

class TestSchemaCheckCompatibility:
    def test_check_compat_no_old_schema(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = None
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "check-compatibility", "inspection", str(jsonl)])
        assert result.exit_code == 0
        assert "No previous schema" in result.output

    def test_check_compat_empty_jsonl_raises(self, runner, tmp_path):
        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("")
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "check-compatibility", "inspection", str(jsonl)])
        assert result.exit_code != 0
        assert "No records found" in result.output

    def test_check_compat_compatible(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        mock_reg.extract_schema_from_dataframe = MagicMock(return_value=_schema(version=2))
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg), \
             patch("socrata_toolkit.core.cli.SchemaRegistry.extract_schema_from_dataframe",
                   return_value=_schema(version=2), create=True), \
             patch("socrata_toolkit.core.cli.BackwardCompatibilityChecker") as mock_chk:
            mock_chk.return_value.check_compatibility.return_value = (True, [])
            result = runner.invoke(main, ["schema", "check-compatibility", "inspection", str(jsonl)])
        assert result.exit_code == 0
        assert "Compatible: True" in result.output

    def test_check_compat_with_violations(self, runner, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"a": 1}\n')
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg), \
             patch("socrata_toolkit.core.cli.SchemaRegistry.extract_schema_from_dataframe",
                   return_value=_schema(version=2), create=True), \
             patch("socrata_toolkit.core.cli.BackwardCompatibilityChecker") as mock_chk:
            mock_chk.return_value.check_compatibility.return_value = (False, ["dropped column a"])
            result = runner.invoke(main, ["schema", "check-compatibility", "inspection", str(jsonl), "--strict"])
        assert result.exit_code == 0
        assert "Compatible: False" in result.output
        assert "dropped column a" in result.output

# ---------------------------------------------------------------------------
# schema list / current
# ---------------------------------------------------------------------------

class TestSchemaListCurrent:
    def test_list_empty(self, runner):
        result = runner.invoke(main, ["schema", "list", "inspection"])
        assert result.exit_code == 0
        assert "No schema versions found" in result.output

    def test_list_populated(self, runner):
        mock_reg = MagicMock()
        mock_reg._load_schema_history.return_value = [_schema(version=1), _schema(version=2)]
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "list", "inspection"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert len(payload) == 2

    def test_current_empty(self, runner):
        result = runner.invoke(main, ["schema", "current", "inspection"])
        assert result.exit_code == 0
        assert "No schema found" in result.output

    def test_current_populated(self, runner):
        mock_reg = MagicMock()
        mock_reg.get_schema_version.return_value = _schema()
        with patch("socrata_toolkit.core.cli.SchemaRegistry", return_value=mock_reg):
            result = runner.invoke(main, ["schema", "current", "inspection"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["dataset_id"] == "inspection"
        assert "columns" in payload
