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
    """The observability subsystem is now shipped, so commands succeed."""

    @pytest.fixture(autouse=True)
    def _fresh_manager(self):
        from socrata_toolkit.observability import reset_observability_manager

        reset_observability_manager()
        yield
        reset_observability_manager()

    @pytest.mark.parametrize(
        "args,marker",
        [
            (["observability", "status"], "Observability Status"),
            (["observability", "health"], "Health Check"),
            (["observability", "health", "--detailed"], "Component Details"),
            (["observability", "sla-report"], "SLA Compliance Report"),
            (["observability", "logs"], "Recent Logs"),
            (["observability", "metrics"], "Metrics Summary"),
            (["observability", "metrics", "--format", "json"], "counters"),
            (["observability", "metrics", "--format", "prometheus"], ""),
        ],
    )
    def test_observability_success(self, runner, args, marker):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output
        if marker:
            assert marker in result.output

    def test_observability_sla_report_json(self, runner):
        result = runner.invoke(main, ["observability", "sla-report", "--json"])
        assert result.exit_code == 0

    def test_observability_health_json(self, runner):
        result = runner.invoke(main, ["observability", "health", "--json"])
        assert result.exit_code == 0

    def test_observability_logs_json(self, runner):
        result = runner.invoke(main, ["observability", "logs", "--json"])
        assert result.exit_code == 0

    def test_observability_trace_missing(self, runner):
        result = runner.invoke(main, ["observability", "trace", "nonexistent"])
        assert result.exit_code == 0
        assert "No trace found" in result.output

    def test_observability_trace_with_spans(self, runner):
        from socrata_toolkit.observability import get_observability_manager

        obs = get_observability_manager()
        tracer = obs.get_tracer()
        root = tracer.start_span("root")
        root.set_attribute("dataset", "violations")
        root.finish()
        child = tracer.start_span("child", trace_id=root.trace_id, parent_span_id=root.span_id)
        child.finish(error_message="boom")

        result = runner.invoke(main, ["observability", "trace", root.trace_id])
        assert result.exit_code == 0
        assert "Spans: 2" in result.output
        assert "@dataset=violations" in result.output
        assert "ERROR: boom" in result.output

    def test_observability_trace_json(self, runner):
        from socrata_toolkit.observability import get_observability_manager

        tracer = get_observability_manager().get_tracer()
        span = tracer.start_span("op")
        span.finish()
        result = runner.invoke(main, ["observability", "trace", span.trace_id, "--json"])
        assert result.exit_code == 0

    def test_observability_status_and_metrics_with_data(self, runner):
        from socrata_toolkit.observability import get_observability_manager

        obs = get_observability_manager()
        obs.get_metrics().increment("requests", 5)
        obs.get_metrics().observe_histogram("latency", 12.0)
        obs.get_logs().log("hello", level="INFO")
        result = runner.invoke(main, ["observability", "metrics", "--format", "json"])
        assert result.exit_code == 0
        assert "requests" in result.output

    def test_observability_sla_report_with_violations(self, runner):
        from socrata_toolkit.observability import SLA, get_observability_manager

        obs = get_observability_manager()
        obs.get_sla().register(SLA(name="latency", target=10, actual=99, severity="high"))
        result = runner.invoke(main, ["observability", "sla-report"])
        assert result.exit_code == 0
        assert "Violations" in result.output
        assert "latency" in result.output

    def test_observability_logs_with_entries(self, runner):
        from socrata_toolkit.observability import get_observability_manager

        obs = get_observability_manager()
        obs.get_logs().log("an error happened", level="ERROR", context={"k": "v"})
        result = runner.invoke(main, ["observability", "logs", "--level", "ERROR"])
        assert result.exit_code == 0
        assert "an error happened" in result.output

    def test_observability_metrics_output_file(self, runner, tmp_path):
        out = tmp_path / "metrics.txt"
        result = runner.invoke(main, ["observability", "metrics", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_observability_export_metrics_json(self, runner, tmp_path):
        out = tmp_path / "m.json"
        result = runner.invoke(
            main, ["observability", "export", "json", "--output", str(out), "--type", "metrics"]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_observability_export_metrics_prometheus(self, runner, tmp_path):
        out = tmp_path / "m.prom"
        result = runner.invoke(
            main,
            ["observability", "export", "prometheus", "--output", str(out), "--type", "metrics"],
        )
        assert result.exit_code == 0

    def test_observability_export_logs_csv(self, runner, tmp_path):
        out = tmp_path / "logs.csv"
        result = runner.invoke(
            main, ["observability", "export", "csv", "--output", str(out), "--type", "logs"]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_observability_export_traces_json(self, runner, tmp_path):
        out = tmp_path / "traces.json"
        result = runner.invoke(
            main, ["observability", "export", "json", "--output", str(out), "--type", "traces"]
        )
        assert result.exit_code == 0

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
