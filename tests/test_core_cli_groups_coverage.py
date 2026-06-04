"""Coverage tests for core.cli subcommand groups.

Exercises the lineage, observability, material, compliance, and schema command
groups via Click's CliRunner. These run against fresh/default state, so most
commands need no mocking — they produce deterministic output.

Note: the ``socrata_toolkit.observability`` module is not packaged in this
build, so every observability command fails with a ClickException. The tests
assert that error path (exit_code != 0) to cover the try/except handlers.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# lineage group
# ---------------------------------------------------------------------------

class TestLineageGroup:
    def test_lineage_nodes_empty(self, runner):
        result = runner.invoke(main, ["lineage", "nodes"])
        assert result.exit_code == 0
        assert "Found 0 nodes" in result.output

    def test_lineage_nodes_json(self, runner):
        result = runner.invoke(main, ["lineage", "nodes", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["count"] == 0
        assert payload["nodes"] == []

    def test_lineage_nodes_with_filters(self, runner):
        result = runner.invoke(
            main, ["lineage", "nodes", "--type", "ingestion", "--owner", "a@b.c", "--tag", "x"]
        )
        assert result.exit_code == 0

    def test_lineage_node_missing_raises(self, runner):
        result = runner.invoke(main, ["lineage", "node", "does-not-exist"])
        assert result.exit_code != 0

    def test_lineage_sources_empty(self, runner):
        result = runner.invoke(main, ["lineage", "sources", "missing"])
        assert result.exit_code == 0
        assert "No upstream sources" in result.output

    def test_lineage_consumers_empty(self, runner):
        result = runner.invoke(main, ["lineage", "consumers", "missing"])
        assert result.exit_code == 0
        assert "No downstream consumers" in result.output

    def test_lineage_path_none(self, runner):
        result = runner.invoke(main, ["lineage", "path", "a", "b"])
        assert result.exit_code == 0
        assert "No path found" in result.output

    def test_lineage_impact(self, runner):
        result = runner.invoke(main, ["lineage", "impact", "x"])
        assert result.exit_code == 0
        assert "Impact Analysis" in result.output

    def test_lineage_dag_empty(self, runner):
        result = runner.invoke(main, ["lineage", "dag"])
        assert result.exit_code == 0
        assert "Empty DAG" in result.output

    def test_lineage_stats(self, runner):
        result = runner.invoke(main, ["lineage", "stats"])
        assert result.exit_code == 0
        assert "Total nodes: 0" in result.output

    def test_lineage_freshness_never_executed(self, runner):
        result = runner.invoke(main, ["lineage", "freshness", "missing"])
        assert result.exit_code == 0
        assert "NEVER EXECUTED" in result.output


# ---------------------------------------------------------------------------
# observability group (module missing → error path)
# ---------------------------------------------------------------------------

class TestObservabilityGroup:
    @pytest.mark.parametrize(
        "args",
        [
            ["observability", "status"],
            ["observability", "health"],
            ["observability", "sla-report"],
            ["observability", "logs"],
            ["observability", "metrics"],
            ["observability", "trace", "some-correlation-id"],
        ],
    )
    def test_observability_error_path(self, runner, args):
        """observability module is unavailable → commands raise ClickException."""
        result = runner.invoke(main, args)
        assert result.exit_code != 0
        assert "Error" in result.output

    def test_observability_export_requires_format(self, runner):
        result = runner.invoke(main, ["observability", "export"])
        # missing required FORMAT arg → click usage error (exit 2)
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# material group
# ---------------------------------------------------------------------------

class TestMaterialGroup:
    def test_material_list(self, runner):
        result = runner.invoke(main, ["material", "list"])
        assert result.exit_code == 0
        assert "ASPH-NYC-001" in result.output

    def test_material_show_valid(self, runner):
        result = runner.invoke(main, ["material", "show", "ASPH-NYC-001"])
        assert result.exit_code == 0
        assert "Material:" in result.output

    def test_material_maintenance_schedule(self, runner):
        result = runner.invoke(main, ["material", "maintenance-schedule", "ASPH-NYC-001"])
        assert result.exit_code == 0

    def test_material_ada_rules(self, runner):
        result = runner.invoke(main, ["material", "ada-rules", "ASPH-NYC-001"])
        assert result.exit_code == 0
        assert "ADA" in result.output

    def test_material_show_missing_arg(self, runner):
        result = runner.invoke(main, ["material", "show"])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# compliance group
# ---------------------------------------------------------------------------

class TestComplianceGroup:
    def test_compliance_check_valid(self, runner):
        result = runner.invoke(main, ["compliance", "check", "ASPH-NYC-001"])
        assert result.exit_code == 0
        assert "Compliance Check" in result.output

    def test_compliance_check_help(self, runner):
        result = runner.invoke(main, ["compliance", "check", "--help"])
        assert result.exit_code == 0

    def test_compliance_ada_violations_help(self, runner):
        result = runner.invoke(main, ["compliance", "ada-violations", "--help"])
        assert result.exit_code == 0

    def test_compliance_report_help(self, runner):
        result = runner.invoke(main, ["compliance", "report", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# schema group (help/usage paths)
# ---------------------------------------------------------------------------

class TestSchemaGroup:
    @pytest.mark.parametrize(
        "subcommand",
        ["list", "current", "diff", "validate", "check-compatibility"],
    )
    def test_schema_subcommand_help(self, runner, subcommand):
        result = runner.invoke(main, ["schema", subcommand, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


# ---------------------------------------------------------------------------
# top-level group help
# ---------------------------------------------------------------------------

class TestGroupHelp:
    @pytest.mark.parametrize(
        "group",
        ["lineage", "observability", "material", "compliance", "schema"],
    )
    def test_group_help(self, runner, group):
        result = runner.invoke(main, [group, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
